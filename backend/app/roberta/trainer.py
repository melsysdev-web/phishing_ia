import pandas as pd
import numpy as np

from datasets import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer
)

from sklearn.model_selection import (
    train_test_split
)

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support
)

MODEL_NAME = "distilroberta-base"

print("Cargando dataset...")

df = pd.read_csv(
    "datasets/roberta_dataset.csv"
)

print(df.shape)

train_df, test_df = train_test_split(
    df,
    test_size=0.2,
    random_state=42,
    stratify=df["label"]
)

train_dataset = Dataset.from_pandas(
    train_df
)

test_dataset = Dataset.from_pandas(
    test_df
)

print("Cargando tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

def tokenize(batch):

    return tokenizer(
        batch["URL"],
        padding="max_length",
        truncation=True,
        max_length=128
    )

train_dataset = train_dataset.map(
    tokenize,
    batched=True
)

test_dataset = test_dataset.map(
    tokenize,
    batched=True
)

train_dataset = train_dataset.remove_columns(
    ["URL"]
)

test_dataset = test_dataset.remove_columns(
    ["URL"]
)

train_dataset.set_format(
    "torch"
)

test_dataset.set_format(
    "torch"
)

print("Cargando modelo...")

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2
)

def compute_metrics(pred):

    labels = pred.label_ids

    preds = np.argmax(
        pred.predictions,
        axis=1
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            labels,
            preds,
            average="binary"
        )
    )

    acc = accuracy_score(
        labels,
        preds
    )

    return {
        "accuracy": acc,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

training_args = TrainingArguments(
    output_dir="models/roberta_phishing",

    eval_strategy="epoch",

    save_strategy="epoch",

    learning_rate=2e-5,

    per_device_train_batch_size=16,

    per_device_eval_batch_size=16,

    num_train_epochs=2,

    weight_decay=0.01,

    logging_steps=100,

    load_best_model_at_end=True
)

trainer = Trainer(
    model=model,

    args=training_args,

    train_dataset=train_dataset,

    eval_dataset=test_dataset,

    compute_metrics=compute_metrics
)

print("Iniciando entrenamiento...")

trainer.train()

print("Evaluando...")

results = trainer.evaluate()

print(results)

trainer.save_model(
    "models/roberta_phishing"
)

tokenizer.save_pretrained(
    "models/roberta_phishing"
)

print(
    "\nModelo guardado correctamente."
)