import numpy as np

from datasets import load_dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix
)

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

BASE_MODEL  = "hamzab/roberta-fake-news-classification"
DATASET_ID  = "GonzaloA/fake_news"
OUTPUT_DIR  = "models/roberta_content"
MAX_LENGTH  = 512
EPOCHS      = 3
BATCH_SIZE  = 8
LR          = 2e-5

ID2LABEL = {0: "FAKE", 1: "REAL"}
LABEL2ID = {"FAKE": 0, "REAL": 1}


# ──────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────

print("Cargando dataset...")

ds = load_dataset(DATASET_ID)

print(ds)


def clean(batch):
    titles = batch.get("title") or [""] * len(batch["label"])
    texts  = batch.get("text")  or [""] * len(batch["label"])

    combined = []
    for title, text in zip(titles, texts):
        title = (title or "").strip()
        text  = (text  or "").strip()[:1000]
        combined.append(f"{title}. {text}" if title else text)

    return {"combined": combined}


ds = ds.map(clean, batched=True)

# Drop rows with empty text or invalid labels
ds = ds.filter(
    lambda x: len(x["combined"].strip()) >= 20
              and x["label"] in (0, 1)
)

train_ds = ds["train"]
test_ds  = ds["test"]

print(f"Train: {len(train_ds)} | Test: {len(test_ds)}")


# ──────────────────────────────────────────────
# Tokenizer
# ──────────────────────────────────────────────

print("Cargando tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)


def tokenize(batch):
    return tokenizer(
        batch["combined"],
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH
    )


train_ds = train_ds.map(tokenize, batched=True)
test_ds  = test_ds.map(tokenize,  batched=True)

keep = ["input_ids", "attention_mask", "label"]
train_ds = train_ds.remove_columns(
    [c for c in train_ds.column_names if c not in keep]
)
test_ds = test_ds.remove_columns(
    [c for c in test_ds.column_names if c not in keep]
)

train_ds.set_format("torch")
test_ds.set_format("torch")


# ──────────────────────────────────────────────
# Modelo
# ──────────────────────────────────────────────

print("Cargando modelo base...")

model = AutoModelForSequenceClassification.from_pretrained(
    BASE_MODEL,
    num_labels=2,
    id2label=ID2LABEL,
    label2id=LABEL2ID,
    ignore_mismatched_sizes=True,
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

    logging_steps=50,

    load_best_model_at_end=True,
    metric_for_best_model="f1",

    fp16=True,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=1)],
)

print("Iniciando entrenamiento...")

trainer.train()

print("\nEvaluación final:")

results = trainer.evaluate()
print(results)


# ──────────────────────────────────────────────
# Guardar
# ──────────────────────────────────────────────

trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"\nModelo guardado en {OUTPUT_DIR}/")
print(f"  Accuracy:  {results.get('eval_accuracy', 0):.4f}")
print(f"  F1:        {results.get('eval_f1', 0):.4f}")
print(f"  Precision: {results.get('eval_precision', 0):.4f}")
print(f"  Recall:    {results.get('eval_recall', 0):.4f}")
