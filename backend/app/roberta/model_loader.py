from pathlib import Path

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)

BASE_DIR = Path(__file__).resolve().parents[3]

MODEL_PATH = str(
    BASE_DIR / "models" / "roberta_phishing"
)

tokenizer = (
    AutoTokenizer.from_pretrained(
        MODEL_PATH
    )
)

model = (
    AutoModelForSequenceClassification
    .from_pretrained(
        MODEL_PATH
    )
)