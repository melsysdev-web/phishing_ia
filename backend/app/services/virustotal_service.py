import base64

import requests

from backend.app.core.config import settings
from backend.app.core.quota_circuit import vt_quota

_API_KEY = settings.virustotal_api_key
_BASE_URL = "https://www.virustotal.com/api/v3"

# Sesión compartida — reutiliza conexiones TCP/TLS entre requests en vez de
# renegociar una por cada llamada (requests.get/post crean una Session
# efímera cada vez internamente).
_SESSION = requests.Session()
_SESSION.mount(
    "https://", requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
)
_SESSION.mount(
    "http://", requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
)


def _url_id(url: str) -> str:
    return (
        base64.urlsafe_b64encode(url.encode())
        .rstrip(b"=")
        .decode()
    )


def _parse_stats(stats: dict) -> dict:
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    harmless = stats.get("harmless", 0)
    undetected = stats.get("undetected", 0)
    total = malicious + suspicious + harmless + undetected

    if malicious >= 3:
        verdict = "malicious"
    elif malicious > 0 or suspicious >= 2:
        verdict = "suspicious"
    else:
        verdict = "clean"

    return {
        "verdict": verdict,
        "is_malicious": malicious > 0,
        "is_suspicious": suspicious > 0,
        "stats": {
            "malicious": malicious,
            "suspicious": suspicious,
            "harmless": harmless,
            "undetected": undetected,
            "total_engines": total,
        },
    }


class VirusTotalService:

    @staticmethod
    def analyze(url: str) -> dict:
        if not _API_KEY:
            return {"error": "VIRUSTOTAL_API_KEY not configured"}

        if vt_quota.is_open():
            return {
                "error": "quota_exceeded",
                "detail": "VirusTotal daily quota exhausted",
            }

        headers = {
            "x-apikey": _API_KEY,
            "accept": "application/json",
        }

        try:
            response = _SESSION.get(
                f"{_BASE_URL}/urls/{_url_id(url)}",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                vt_quota.record_call()
                try:
                    stats = response.json()["data"]["attributes"][
                        "last_analysis_stats"
                    ]
                except (KeyError, ValueError, TypeError):
                    return {
                        "error": "VirusTotal: respuesta con formato inesperado"
                    }
                return _parse_stats(stats)

            if response.status_code == 404:
                return {
                    "error": "url_not_in_virustotal",
                    "detail": "URL not yet analyzed by VirusTotal",
                }

            if response.status_code == 429:
                vt_quota.record_error_429()
                return {
                    "error": "quota_exceeded",
                    "detail": "VirusTotal rate limited (429)",
                }

            return {"error": f"VirusTotal error: {response.status_code}"}

        except requests.Timeout:
            return {"error": "VirusTotal request timed out"}

        except requests.RequestException as exc:
            return {"error": str(exc)}

