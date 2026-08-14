"""Guard SSRF global para cualquier petición saliente hecha con `requests`.

`HtmlFetcher` valida el hostname antes de pedir la URL (ver html_fetcher.py),
pero esa validación resuelve el hostname por separado de la conexión real que
hace `requests`/urllib3 — dos resoluciones DNS independientes. Un atacante
dueño de su propio dominio puede responder una IP pública en la primera
consulta (pasa el chequeo) y una IP interna en la segunda, milisegundos
después (DNS rebinding), saltándose el chequeo por completo.

Este módulo parchea el punto donde urllib3 abre el socket TCP real
(`urllib3.util.connection.create_connection`) para que la IP se resuelva y
valide ahí mismo, en la misma llamada que abre la conexión — sin ventana
entre "verificar" y "conectar". El hostname original se sigue usando para
SNI/Host/verificación de certificado (no se toca `HTTPConnection.host`), solo
cambia a qué IP concreta se conecta el socket.

Se instala una sola vez, a nivel de proceso, para todas las llamadas
`requests` del backend — no solo las de HtmlFetcher. Es inofensivo para los
demás servicios (VirusTotal, Safe Browsing, Fact Check) porque sus hosts
siempre resuelven a IPs públicas.
"""

import ipaddress
import socket

import urllib3.util.connection as _urllib3_connection

_orig_create_connection = _urllib3_connection.create_connection
_installed = False


def _is_blocked_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _guarded_create_connection(address, *args, **kwargs):
    host, port = address

    try:
        candidates = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise OSError(f"No se pudo resolver el host '{host}': {e}") from e

    safe_ips = [c[4][0] for c in candidates if not _is_blocked_ip(c[4][0])]
    if not safe_ips:
        raise OSError(
            f"Host '{host}' resuelve a una IP interna/privada, bloqueado por seguridad (SSRF)"
        )

    # Conecta directo a la IP ya validada en vez de dejar que
    # create_connection vuelva a resolver 'host' por su cuenta — así no hay
    # una segunda resolución DNS que un atacante pueda hacer responder
    # distinto (rebinding).
    return _orig_create_connection((safe_ips[0], port), *args, **kwargs)


def install() -> None:
    """Instala el guard. Idempotente — llamar varias veces no lo duplica."""
    global _installed
    if _installed:
        return
    _urllib3_connection.create_connection = _guarded_create_connection
    _installed = True
