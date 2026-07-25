from functools import lru_cache

from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.app.core.paths import get_models_dir

MODEL_PATH = str(get_models_dir() / "roberta_phishing_new")


@lru_cache(maxsize=1)
def get_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    model.eval()
    return tokenizer, model
