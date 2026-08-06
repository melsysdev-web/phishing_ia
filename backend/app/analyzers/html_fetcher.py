import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

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
    """Resuelve el hostname y rechaza si cualquier IP asociada es interna/privada.

    Esto es defensa contra SSRF: la URL a analizar la controla quien llama a
    /predict, y sin este chequeo el backend seguiría enlaces hacia
    localhost, redes internas (RFC1918) o metadata endpoints de cloud
    (169.254.169.254).
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
