import os
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import torch
from transformers import PreTrainedTokenizerBase, RobertaTokenizer

from .config import (
    CHECKPOINT_DIR,
    DEFAULT_THRESHOLD,
    MAX_LENGTH,
    MODEL_NAME,
    PREDICT_BATCH_SIZE,
)
from .model import PhishingClassifier


@lru_cache(maxsize=1)
def _load_predictor(
    checkpoint_path: Optional[str] = None,
) -> Tuple[PhishingClassifier, PreTrainedTokenizerBase, torch.device]:
    """
    Carga (una sola vez, cacheada vía lru_cache) el modelo entrenado y el
    tokenizador. Usa `{CHECKPOINT_DIR}/best_model.pt` si no se especifica
    `checkpoint_path`.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    path = checkpoint_path or os.path.join(CHECKPOINT_DIR, "best_model.pt")

    model = PhishingClassifier()
    model.load_state_dict(torch.load(path, map_location=device))
    model.to(device)
    model.eval()

    tokenizer = RobertaTokenizer.from_pretrained(MODEL_NAME)

    return model, tokenizer, device


def _build_result(
    phishing_prob: float,
    legitimate_prob: float,
    threshold: float,
) -> Dict[str, object]:
    """Construye el dict de salida estándar a partir de las probabilidades crudas."""
    label = "phishing" if phishing_prob > threshold else "legitimo"
    confidence = phishing_prob if label == "phishing" else legitimate_prob

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "phishing_probability": round(phishing_prob, 4),
        "legitimate_probability": round(legitimate_prob, 4),
        "alert": phishing_prob > threshold,
    }


def predict_batch(
    texts: List[str],
    threshold: float = DEFAULT_THRESHOLD,
    batch_size: int = PREDICT_BATCH_SIZE,
    checkpoint_path: Optional[str] = None,
) -> List[Dict[str, object]]:
    """
    Clasifica una lista de textos en lotes de `batch_size`.

    Args:
        texts:           Textos ya preparados (ver preprocess.prepare_input)
        threshold:        Umbral de phishing_probability para activar "alert"
        batch_size:        Tamaño de lote usado durante la inferencia
        checkpoint_path:   Ruta a un checkpoint distinto al best_model.pt por defecto

    Returns:
        Lista de dicts (uno por texto, en el mismo orden) con label,
        confidence, probabilidades y alert.
    """
    model, tokenizer, device = _load_predictor(checkpoint_path)
    results: List[Dict[str, object]] = []

    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]

        inputs = tokenizer(
            chunk,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=MAX_LENGTH,
        ).to(device)

        with torch.no_grad():
            output = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
            )

        for row in output["probabilities"]:
            results.append(
                _build_result(
                    phishing_prob=float(row[1]),
                    legitimate_prob=float(row[0]),
                    threshold=threshold,
                )
            )

    return results


def predict_single(
    text: str,
    threshold: float = DEFAULT_THRESHOLD,
    checkpoint_path: Optional[str] = None,
) -> Dict[str, object]:
    """
    Clasifica un único texto. Atajo sobre predict_batch para no duplicar
    la lógica de tokenización/inferencia.
    """
    return predict_batch(
        [text],
        threshold=threshold,
        batch_size=1,
        checkpoint_path=checkpoint_path,
    )[0]
