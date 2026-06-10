import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.getenv("FACT_CHECK_API_KEY", "")
_BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

_NEGATIVE_RATINGS = {
    "false", "mostly false", "fake", "incorrect",
    "misleading", "misinformation", "disinformation",
    "falso", "incorrecto", "engañoso", "manipulado",
    "pants on fire", "four pinocchios", "fabricated"
}

_POSITIVE_RATINGS = {
    "true", "mostly true", "correct", "accurate",
    "verdadero", "correcto", "preciso", "confirmed"
}


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def _base_name(domain: str) -> str:
    # "bbc.com" -> "bbc", "infowars.com" -> "infowars"
    return domain.split(".")[0].lower()


def _domain_in(text: str, domain: str) -> bool:
    text_lower = (text or "").lower()
    return (
        domain.lower() in text_lower
        or _base_name(domain) in text_lower
    )


class FactCheckService:

    @staticmethod
    def analyze(url: str) -> dict:
        if not _API_KEY:
            return {"error": "FACT_CHECK_API_KEY not configured"}

        domain = _extract_domain(url)

        try:
            response = requests.get(
                _BASE_URL,
                params={"query": domain, "key": _API_KEY},
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": (
                        f"Fact Check API error: {response.status_code}"
                    )
                }

            claims = response.json().get("claims", [])

            if not claims:
                return {
                    "claims_found": 0,
                    "verdict": "no_data",
                    "fake_count": 0,
                    "true_count": 0,
                    "publisher_count": 0,
                    "claims": []
                }

            parsed_claims = []
            fake_count = 0
            true_count = 0
            publisher_count = 0  # times domain acted as fact-checker

            for claim in claims[:5]:
                claimant = claim.get("claimant", "")
                claimant_url = claim.get("claimantUrl", "")

                # Domain is the one making the claim (the source)
                is_claimant = (
                    _domain_in(claimant, domain)
                    or _domain_in(claimant_url, domain)
                )

                for review in claim.get("claimReview", []):
                    publisher_site = (
                        review.get("publisher", {})
                        .get("site", "")
                    )
                    review_url = review.get("url", "")

                    # Domain is the one publishing the fact-check
                    is_publisher = (
                        _domain_in(publisher_site, domain)
                        or _domain_in(review_url, domain)
                    )

                    rating = (
                        review.get("textualRating", "")
                        .lower()
                        .strip()
                    )

                    # Skip if domain is the fact-checker, not the source
                    if is_publisher and not is_claimant:
                        publisher_count += 1
                        continue

                    # Skip claims with no identified source
                    if not claimant and not is_claimant:
                        continue

                    parsed_claims.append({
                        "claim": claim.get("text", ""),
                        "claimant": claimant,
                        "rating": rating,
                        "publisher": (
                            review
                            .get("publisher", {})
                            .get("name", "Unknown")
                        ),
                        "url": review_url,
                    })

                    if any(neg in rating for neg in _NEGATIVE_RATINGS):
                        fake_count += 1
                    elif any(pos in rating for pos in _POSITIVE_RATINGS):
                        true_count += 1

            if fake_count >= 2 and fake_count > true_count:
                verdict = "unreliable"
            elif fake_count > 0:
                verdict = "suspicious"
            elif publisher_count > 0:
                # Domain is a known fact-checker — treat as reliable
                verdict = "reliable"
            elif true_count > 0:
                verdict = "reliable"
            else:
                verdict = "no_data"

            return {
                "claims_found": len(claims),
                "verdict": verdict,
                "fake_count": fake_count,
                "true_count": true_count,
                "publisher_count": publisher_count,
                "claims": parsed_claims[:3],
            }

        except requests.Timeout:
            return {"error": "Fact Check API request timed out"}

        except requests.RequestException as exc:
            return {"error": str(exc)}
