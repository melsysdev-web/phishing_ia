from functools import lru_cache

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.app.core.paths import get_models_dir

MODEL_PATH = str(get_models_dir() / "roberta_phishing_new")


@lru_cache(maxsize=1)
def get_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    model.eval()
    # Cuantización dinámica a int8 de las capas lineales — más rápido en CPU
    # y reduce la huella de memoria del modelo, sin reentrenar ni exportar.
    # torch.ao.quantization (no torch.quantization, deprecated en 2.11+).
    model = torch.ao.quantization.quantize_dynamic(
        model, {torch.nn.Linear}, dtype=torch.qint8
    )
    return tokenizer, model
