import os
from typing import Optional, Tuple

import torch
from sklearn.metrics import f1_score
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from transformers import get_linear_schedule_with_warmup

from .config import (
    BATCH_SIZE,
    CHECKPOINT_DIR,
    EARLY_STOPPING_PATIENCE,
    EPOCHS,
    LEARNING_RATE,
    WARMUP_RATIO,
    WEIGHT_DECAY,
)
from .model import PhishingClassifier


def _run_epoch(
    model: PhishingClassifier,
    loader: DataLoader,
    device: torch.device,
    optimizer: Optional[torch.optim.Optimizer] = None,
    scheduler: Optional[torch.optim.lr_scheduler.LambdaLR] = None,
) -> Tuple[float, float]:
    """
    Ejecuta una época completa.
    Si `optimizer` es None, corre en modo evaluación (sin backprop).

    Returns:
        (loss_promedio_por_muestra, f1_score)
    """
    is_train = optimizer is not None
    model.train(is_train)

    total_loss = 0.0
    all_preds: list[int] = []
    all_labels: list[int] = []

    with torch.set_grad_enabled(is_train):
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            if is_train:
                optimizer.zero_grad()

            output = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = output["loss"]

            if is_train:
                loss.backward()
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()

            total_loss += loss.item() * input_ids.size(0)

            preds = torch.argmax(output["probabilities"], dim=-1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    avg_loss = total_loss / len(loader.dataset)
    f1 = f1_score(all_labels, all_preds, average="binary", zero_division=0)

    return avg_loss, f1


def train(
    model: PhishingClassifier,
    train_dataset: Dataset,
    val_dataset: Dataset,
    device: Optional[torch.device] = None,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    weight_decay: float = WEIGHT_DECAY,
    warmup_ratio: float = WARMUP_RATIO,
    patience: int = EARLY_STOPPING_PATIENCE,
    checkpoint_dir: str = CHECKPOINT_DIR,
) -> PhishingClassifier:
    """
    Entrena PhishingClassifier con AdamW + warmup lineal + early stopping
    sobre val_loss. Guarda automáticamente el mejor checkpoint encontrado.

    Al finalizar (por agotar épocas o por early stopping), el modelo
    retornado tiene cargados los pesos del mejor checkpoint, no los de
    la última época.

    Returns:
        El propio `model`, con los pesos del mejor checkpoint restaurados.
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    optimizer = AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )

    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    os.makedirs(checkpoint_dir, exist_ok=True)
    best_checkpoint_path = os.path.join(checkpoint_dir, "best_model.pt")

    best_val_loss = float("inf")
    epochs_without_improvement = 0

    for epoch in range(1, epochs + 1):
        train_loss, train_f1 = _run_epoch(
            model, train_loader, device, optimizer, scheduler
        )
        val_loss, val_f1 = _run_epoch(model, val_loader, device)

        print(
            f"Época {epoch}/{epochs} | "
            f"train_loss={train_loss:.4f} train_f1={train_f1:.4f} | "
            f"val_loss={val_loss:.4f} val_f1={val_f1:.4f}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            torch.save(model.state_dict(), best_checkpoint_path)
            print(f"  ↳ Mejor checkpoint guardado en {best_checkpoint_path}")
        else:
            epochs_without_improvement += 1
            print(f"  ↳ Sin mejora ({epochs_without_improvement}/{patience})")

            if epochs_without_improvement >= patience:
                print(f"Early stopping activado en la época {epoch}.")
                break

    # Restaurar el mejor checkpoint antes de devolver el modelo
    model.load_state_dict(torch.load(best_checkpoint_path, map_location=device))
    return model
