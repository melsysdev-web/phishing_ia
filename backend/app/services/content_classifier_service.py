from functools import lru_cache
from pathlib import Path

_MAX_TEXT_CHARS = 2000
_MIN_TEXT_CHARS = 50

_REMOTE_MODEL  = "hamzab/roberta-fake-news-classification"
_LOCAL_MODEL   = str(Path(__file__).resolve().parents[3] / "models" / "roberta_content")


def _resolve_model() -> tuple[str, bool]:
    """Returns (model_path_or_id, is_local)."""
    local = Path(_LOCAL_MODEL)
    if (local / "config.json").exists():
        return _LOCAL_MODEL, True
    return _REMOTE_MODEL, False


@lru_cache(maxsize=1)
def _load_pipeline():
    from transformers import pipeline

    model_id, is_local = _resolve_model()

    if is_local:
        print(f"[ContentClassifier] Usando modelo local: {model_id}")
    else:
        print(f"[ContentClassifier] Usando modelo remoto: {model_id}")

    return pipeline(
        "text-classification",
        model=model_id,
        truncation=True,
        max_length=512,
    )


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

            # Normalize: local model uses FAKE/REAL, remote uses TRUE/FALSE
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
