import requests

from backend.app.core.config import settings

_API_KEY = settings.safe_browsing_api_key
_ENDPOINT = (
    "https://safebrowsing.googleapis.com"
    "/v4/threatMatches:find"
)
_THREAT_TYPES = [
    "MALWARE",
    "SOCIAL_ENGINEERING",
    "UNWANTED_SOFTWARE",
    "POTENTIALLY_HARMFUL_APPLICATION",
]


class SafeBrowsingService:

    @staticmethod
    def analyze(url: str) -> dict:
        if not _API_KEY:
            return {
                "error": "SAFE_BROWSING_API_KEY not configured"
            }

        payload = {
            "client": {
                "clientId": "phishing-ia",
                "clientVersion": "1.0.0",
            },
            "threatInfo": {
                "threatTypes": _THREAT_TYPES,
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}],
            },
        }

        try:
            response = requests.post(
                _ENDPOINT,
                params={"key": _API_KEY},
                json=payload,
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": (
                        f"Safe Browsing API error: "
                        f"{response.status_code}"
                    )
                }

            data = response.json()
            matches = data.get("matches", [])

            if not matches:
                return {
                    "is_threat": False,
                    "threats": [],
                    "verdict": "clean",
                }

            threats = [
                {
                    "type": m.get("threatType"),
                    "platform": m.get("platformType"),
                    "cache_duration": m.get(
                        "cacheDuration"
                    ),
                }
                for m in matches
            ]

            threat_types = {t["type"] for t in threats}

            if (
                "MALWARE" in threat_types
                or "SOCIAL_ENGINEERING" in threat_types
            ):
                verdict = "dangerous"
            else:
                verdict = "suspicious"

            return {
                "is_threat": True,
                "threats": threats,
                "verdict": verdict,
            }

        except requests.Timeout:
            return {
                "error": "Safe Browsing request timed out"
            }

        except requests.RequestException as exc:
            return {"error": str(exc)}
