from typing import Optional

import torch
import torch.nn as nn
from transformers import RobertaModel

from .config import DROPOUT, HIDDEN_DIM, MODEL_NAME


class PhishingClassifier(nn.Module):
    """
    Clasificador de phishing basado en RoBERTa-base.

    Pipeline interno:
        input_ids + attention_mask
        → RoBERTa encoder (12 bloques, dim 768)
        → pooler_output [CLS]  (dim 768)
        → Dropout(0.1) → Linear(768→256) → ReLU
        → Dropout(0.1) → Linear(256→2)
        → Softmax  →  {"phishing": p, "legitimo": 1-p}
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        dropout: float = DROPOUT,
        hidden_dim: int = HIDDEN_DIM,
        freeze_encoder: bool = False,
    ) -> None:
        super().__init__()

        # Encoder RoBERTa pre-entrenado
        self.roberta: RobertaModel = RobertaModel.from_pretrained(model_name)

        # Cabeza clasificadora personalizada
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(self.roberta.config.hidden_size, hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_dim, 2),
        )

        self._loss_fn = nn.CrossEntropyLoss()

        if freeze_encoder:
            self.freeze_encoder()

    # ── Forward ───────────────────────────────────────────────────────────────

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
    ) -> dict:
        """
        Args:
            input_ids:      (batch, seq_len)
            attention_mask: (batch, seq_len)
            labels:         (batch,) con valores 0 (legítimo) o 1 (phishing)

        Returns:
            dict con claves:
                logits        – (batch, 2), sin softmax
                probabilities – (batch, 2), columna 0 = legítimo, 1 = phishing
                loss          – scalar CrossEntropy (solo si se pasan labels)
        """
        encoder_out = self.roberta(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

        # pooler_output: vector [CLS] procesado con Dense+Tanh — shape (batch, 768)
        pooled: torch.Tensor = encoder_out.pooler_output

        logits: torch.Tensor = self.classifier(pooled)          # (batch, 2)
        probs: torch.Tensor = torch.softmax(logits, dim=-1)     # (batch, 2)

        result: dict = {
            "logits": logits,
            "probabilities": probs,
        }

        if labels is not None:
            result["loss"] = self._loss_fn(logits, labels)

        return result

    # ── Transfer learning ─────────────────────────────────────────────────────

    def freeze_encoder(self) -> None:
        """Congela todos los parámetros del encoder (embeddings + 12 capas)."""
        for param in self.roberta.parameters():
            param.requires_grad = False

    def unfreeze_encoder(self) -> None:
        """Descongela todos los parámetros del encoder."""
        for param in self.roberta.parameters():
            param.requires_grad = True

    def unfreeze_last_n_layers(self, n: int) -> None:
        """
        Estrategia de fine-tuning gradual: congela el encoder excepto las
        últimas n capas transformer y el pooler.

        Ejemplo de uso:
            modelo.freeze_encoder()
            modelo.unfreeze_last_n_layers(4)   # solo entrena las últimas 4 de 12
        """
        self.freeze_encoder()
        encoder_layers = self.roberta.encoder.layer
        for layer in encoder_layers[-n:]:
            for param in layer.parameters():
                param.requires_grad = True
        # El pooler siempre se entrena (alimenta directamente la cabeza)
        for param in self.roberta.pooler.parameters():
            param.requires_grad = True

    # ── Utilidades ────────────────────────────────────────────────────────────

    def trainable_params(self) -> int:
        """Número de parámetros con gradiente activo."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def total_params(self) -> int:
        """Número total de parámetros del modelo."""
        return sum(p.numel() for p in self.parameters())
