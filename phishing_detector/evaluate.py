from typing import Dict, List, Optional

import torch
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from torch.utils.data import DataLoader, Dataset

from .config import BATCH_SIZE
from .model import PhishingClassifier


def evaluate_model(
    model: PhishingClassifier,
    dataset: Dataset,
    device: Optional[torch.device] = None,
    batch_size: int = BATCH_SIZE,
) -> Dict[str, float]:
    """
    Evalúa PhishingClassifier sobre `dataset` (debe exponer "input_ids",
    "attention_mask" y "labels", como PhishingDataset).

    Returns:
        dict con precision, recall, f1 y auc_roc.
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_labels: List[int] = []
    all_preds: List[int] = []
    all_phishing_probs: List[float] = []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"]

            output = model(input_ids=input_ids, attention_mask=attention_mask)
            probs = output["probabilities"]  # (batch, 2) — col 1 = phishing

            preds = torch.argmax(probs, dim=-1)

            all_labels.extend(labels.tolist())
            all_preds.extend(preds.cpu().tolist())
            all_phishing_probs.extend(probs[:, 1].cpu().tolist())

    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="binary", zero_division=0
    )

    try:
        auc_roc = roc_auc_score(all_labels, all_phishing_probs)
    except ValueError:
        # roc_auc_score exige ambas clases presentes en el dataset evaluado
        auc_roc = float("nan")

    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "auc_roc": round(float(auc_roc), 4),
    }
