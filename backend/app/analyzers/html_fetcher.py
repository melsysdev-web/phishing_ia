import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

from backend.app.core import ssrf_guard

# Protección principal contra SSRF: parchea el punto donde urllib3 abre la
# conexión TCP real para que la IP se resuelva y valide en la misma llamada
# que conecta (sin ventana para DNS rebinding entre el chequeo de abajo y la
# petición real). Ver backend/app/core/ssrf_guard.py.
ssrf_guard.install()

_TIMEOUT = 10
_MAX_REDIRECTS = 5
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB — evita agotar memoria con respuestas gigantes
_ALLOWED_SCHEMES = {"http", "https"}


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


def _is_safe_host(hostname: str) -> bool:
    """Chequeo temprano de defensa en profundidad (no es la protección principal).

    Resuelve el hostname y rechaza si cualquier IP asociada es interna o
    privada, para devolver un error claro antes de intentar la conexión. La
    protección que realmente cierra la ventana de DNS rebinding es
    `ssrf_guard.install()` (arriba), que valida la IP en el mismo momento en
    que se abre la conexión TCP real — este chequeo por sí solo, al resolver
    el hostname por separado de la petición real, se puede saltar con una
    respuesta DNS distinta entre esta resolución y la de `requests.get`.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    return bool(infos) and all(not _is_blocked_ip(info[4][0]) for info in infos)


class HtmlFetcher:

    @staticmethod
    def get_html(url: str):
        try:
            current_url = url

            for _ in range(_MAX_REDIRECTS + 1):
                parsed = urlparse(current_url)

                if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.hostname:
                    return {
                        "success": False,
                        "error": "Esquema de URL no permitido",
                        "html": "",
                    }

                if not _is_safe_host(parsed.hostname):
                    return {
                        "success": False,
                        "error": "URL apunta a una red interna/privada, bloqueada por seguridad",
                        "html": "",
                    }

                response = requests.get(
                    current_url,
                    timeout=_TIMEOUT,
                    headers={"User-Agent": "Mozilla/5.0"},
                    allow_redirects=False,
                    stream=True,
                )

                if response.is_redirect or response.is_permanent_redirect:
                    location = response.headers.get("Location")
                    response.close()
                    if not location:
                        return {
                            "success": False,
                            "error": "Redirección sin cabecera Location",
                            "html": "",
                        }
                    current_url = urljoin(current_url, location)
                    continue

                total = 0
                chunks = []
                for chunk in response.iter_content(chunk_size=8192):
                    total += len(chunk)
                    if total > _MAX_BYTES:
                        response.close()
                        return {
                            "success": False,
                            "error": "Respuesta demasiado grande (> 2MB)",
                            "html": "",
                        }
                    chunks.append(chunk)

                html = b"".join(chunks).decode(
                    response.encoding or "utf-8", errors="replace"
                )

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "html": html,
                }

            return {
                "success": False,
                "error": "Demasiadas redirecciones",
                "html": "",
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
                "html": ""
            }
