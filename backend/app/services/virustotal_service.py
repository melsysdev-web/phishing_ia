import base64
import os

import requests
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
_BASE_URL = "https://www.virustotal.com/api/v3"


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

    if total == 0:
        verdict = "no_data"
    elif malicious >= 3:
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

        headers = {
            "x-apikey": _API_KEY,
            "accept": "application/json",
        }

        try:
            response = requests.get(
                f"{_BASE_URL}/urls/{_url_id(url)}",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                stats = (
                    response.json()["data"]["attributes"][
                        "last_analysis_stats"
                    ]
                )
                return _parse_stats(stats)

            if response.status_code == 404:
                return VirusTotalService._submit_and_fetch(
                    url, headers
                )

            return {
                "error": (
                    f"VirusTotal error: {response.status_code}"
                )
            }

        except requests.Timeout:
            return {"error": "VirusTotal request timed out"}

        except requests.RequestException as exc:
            return {"error": str(exc)}

    @staticmethod
    def _submit_and_fetch(url: str, headers: dict) -> dict:
        try:
            submit = requests.post(
                f"{_BASE_URL}/urls",
                headers={
                    **headers,
                    "content-type": (
                        "application/x-www-form-urlencoded"
                    ),
                },
                data={"url": url},
                timeout=10,
            )

            if submit.status_code != 200:
                return {
                    "error": (
                        f"VirusTotal submission failed: "
                        f"{submit.status_code}"
                    )
                }

            analysis_id = submit.json()["data"]["id"]

            analysis = requests.get(
                f"{_BASE_URL}/analyses/{analysis_id}",
                headers=headers,
                timeout=10,
            )

            if analysis.status_code != 200:
                return {
                    "error": (
                        f"VirusTotal analysis fetch failed: "
                        f"{analysis.status_code}"
                    )
                }

            stats = (
                analysis.json()["data"]["attributes"]["stats"]
            )
            return _parse_stats(stats)

        except requests.Timeout:
            return {"error": "VirusTotal request timed out"}

        except requests.RequestException as exc:
            return {"error": str(exc)}
