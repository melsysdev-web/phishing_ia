from functools import lru_cache

from bs4 import BeautifulSoup

_MAX_TEXT_CHARS = 2000
_MIN_TEXT_CHARS = 50

_MODEL_ID = "hamzab/roberta-fake-news-classification"


@lru_cache(maxsize=1)
def _load_pipeline():
    from transformers import pipeline
    return pipeline(
        "text-classification",
        model=_MODEL_ID,
        truncation=True,
        max_length=512,
    )


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)

    return " ".join(text.split())[:_MAX_TEXT_CHARS]


class ContentClassifierService:

    @staticmethod
    def analyze(page_text: str) -> dict:
        if not page_text or len(page_text.strip()) < _MIN_TEXT_CHARS:
            return {
                "verdict": "no_content",
                "label": "UNKNOWN",
                "confidence": 0.0
            }

        try:
            pipe = _load_pipeline()
            result = pipe(page_text[:_MAX_TEXT_CHARS])[0]

            label = result["label"].upper()
            confidence = round(result["score"], 4)

            # Model outputs TRUE/FALSE — normalize to REAL/FAKE for clarity
            normalized = (
                "REAL" if label in ("TRUE", "REAL")
                else "FAKE" if label in ("FALSE", "FAKE")
                else label
            )

            return {
                "verdict": normalized.lower(),
                "label": normalized,
                "confidence": confidence,
                "raw_label": label,
            }

        except Exception as exc:
            return {"error": str(exc)}
