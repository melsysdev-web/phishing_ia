"""
Reentrenamiento del clasificador de contenido para español.

Base model : xlm-roberta-base  (multilingüe — pre-entrenado en 100 idiomas,
             incluyendo español; transfiere a ES sin necesidad de datos en ES)
Dataset    : GonzaloA/fake_news (EN, 24k muestras)
Output     : models/roberta_content   (sobreescribe el modelo inglés)
"""

import numpy as np
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

BASE_MODEL = "xlm-roberta-base"
DATASET_ID = "GonzaloA/fake_news"
OUTPUT_DIR = "models/roberta_content"
MAX_LENGTH = 512
EPOCHS     = 3
BATCH_SIZE = 8
LR         = 2e-5

ID2LABEL = {0: "REAL", 1: "FAKE"}
LABEL2ID = {"REAL": 0, "FAKE": 1}

# ──────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────

print(f"Cargando dataset: {DATASET_ID}...")
ds = load_dataset(DATASET_ID)
print(f"  Splits  : {list(ds.keys())}")
print(f"  Columnas: {ds['train'].column_names}")


def clean(batch):
    combined = []
    for title, text in zip(batch.get("title") or [""] * len(batch["label"]),
                           batch.get("text")  or [""] * len(batch["label"])):
        title = (title or "").strip()
        text  = (text  or "").strip()[:1000]
        combined.append(f"{title}. {text}" if title and text else title or text)
    return {"combined": combined}


ds = ds.map(clean, batched=True)
ds = ds.filter(
    lambda x: len(x["combined"].strip()) >= 20 and x["label"] in (0, 1)
)

train_ds = ds["train"]
eval_ds  = ds["validation"]
test_ds  = ds["test"]

print(f"\nTrain: {len(train_ds)} | Val: {len(eval_ds)} | Test: {len(test_ds)}")
n_fake = sum(1 for l in train_ds["label"] if l == 0)
n_real = sum(1 for l in train_ds["label"] if l == 1)
print(f"Train — FAKE: {n_fake} | REAL: {n_real}")

# ──────────────────────────────────────────────
# Tokenizer
# ──────────────────────────────────────────────

print(f"\nCargando tokenizer: {BASE_MODEL}")

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)


def tokenize(batch):
    return tokenizer(
        batch["combined"],
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
    )


train_ds = train_ds.map(tokenize, batched=True)
eval_ds  = eval_ds.map(tokenize,  batched=True)
test_ds  = test_ds.map(tokenize,  batched=True)

keep_cols = ["input_ids", "attention_mask", "label"]
train_ds = train_ds.remove_columns([c for c in train_ds.column_names if c not in keep_cols])
eval_ds  = eval_ds.remove_columns( [c for c in eval_ds.column_names  if c not in keep_cols])
test_ds  = test_ds.remove_columns( [c for c in test_ds.column_names  if c not in keep_cols])

train_ds.set_format("torch")
eval_ds.set_format("torch")
test_ds.set_format("torch")

# ──────────────────────────────────────────────
# Modelo
# ──────────────────────────────────────────────

print(f"\nCargando modelo base: {BASE_MODEL}")

model = AutoModelForSequenceClassification.from_pretrained(
    BASE_MODEL,
    num_labels=2,
    id2label=ID2LABEL,
    label2id=LABEL2ID,
)

# ──────────────────────────────────────────────
# Métricas
# ──────────────────────────────────────────────

def compute_metrics(pred):
    labels = pred.label_ids
    preds  = np.argmax(pred.predictions, axis=1)

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary"
    )
    acc = accuracy_score(labels, preds)
    cm  = confusion_matrix(labels, preds)

    print(f"\nConfusion matrix:\n{cm}")
    print(f"  TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}  TP={cm[1,1]}")

    return {
        "accuracy":  acc,
        "precision": precision,
        "recall":    recall,
        "f1":        f1,
    }

# ──────────────────────────────────────────────
# Entrenamiento
# ──────────────────────────────────────────────

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,

    eval_strategy="epoch",
    save_strategy="epoch",

    learning_rate=LR,

    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,

    num_train_epochs=EPOCHS,

    weight_decay=0.01,
    warmup_ratio=0.1,

    logging_steps=100,

    load_best_model_at_end=True,
    metric_for_best_model="f1",

    fp16=True,    # RTX 3060 - mixed precision para mayor velocidad
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=1)],
)

print("\nIniciando entrenamiento...")

trainer.train()

print("\nEvaluación final (test set):")
results = trainer.evaluate(test_ds)
print(results)

# ──────────────────────────────────────────────
# Guardar
# ──────────────────────────────────────────────

trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"\nModelo guardado en {OUTPUT_DIR}/")
print(f"  Accuracy  : {results.get('eval_accuracy',  0):.4f}")
print(f"  F1        : {results.get('eval_f1',        0):.4f}")
print(f"  Precision : {results.get('eval_precision', 0):.4f}")
print(f"  Recall    : {results.get('eval_recall',    0):.4f}")
