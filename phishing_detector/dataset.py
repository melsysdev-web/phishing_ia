from typing import Dict, List, Optional

import torch
from torch.utils.data import Dataset
from transformers import PreTrainedTokenizerBase, RobertaTokenizer

from .config import MAX_LENGTH, MODEL_NAME


class PhishingDataset(Dataset):
    """
    Dataset de PyTorch para el clasificador de phishing.

    Tokeniza todos los textos por adelantado (en batch) durante __init__,
    evitando invocar el tokenizador en cada __getitem__.

    Nota: RobertaTokenizer usa <s>...</s> como tokens de inicio/fin
    (equivalentes funcionales a [CLS]/[SEP] de BERT), agregados
    automáticamente al tokenizar.
    """

    def __init__(
        self,
        texts: List[str],
        labels: List[int],
        tokenizer: Optional[PreTrainedTokenizerBase] = None,
        max_length: int = MAX_LENGTH,
    ) -> None:
        if len(texts) != len(labels):
            raise ValueError(
                f"texts y labels deben tener la misma longitud "
                f"({len(texts)} != {len(labels)})"
            )

        self.tokenizer: PreTrainedTokenizerBase = (
            tokenizer or RobertaTokenizer.from_pretrained(MODEL_NAME)
        )
        self.max_length = max_length
        self.labels: torch.Tensor = torch.tensor(labels, dtype=torch.long)

        # Tokenización en batch (más eficiente que una llamada por muestra)
        encoded = self.tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        self.input_ids: torch.Tensor = encoded["input_ids"]
        self.attention_mask: torch.Tensor = encoded["attention_mask"]

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "input_ids": self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "labels": self.labels[idx],
        }
