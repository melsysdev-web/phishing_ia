import argparse
import sys
from pathlib import Path
from typing import List

# Permite ejecutar este script directamente (python scripts/run_training.py ...)
# sin depender de que el repo root ya esté en PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sklearn.model_selection import train_test_split

from phishing_detector.dataset import PhishingDataset
from phishing_detector.evaluate import evaluate_model
from phishing_detector.model import PhishingClassifier
from phishing_detector.preprocess import prepare_input
from phishing_detector.train import train

REQUIRED_COLUMNS = {"url", "body", "label"}


def _build_texts(df: pd.DataFrame) -> List[str]:
    """Combina url + body de cada fila en el formato que consume el modelo."""
    df = df.fillna("")
    return [
        prepare_input(url=row.url, body=row.body)
        for row in df.itertuples(index=False)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Entrena y evalúa PhishingClassifier a partir de un CSV "
            "con columnas url,body,label"
        )
    )
    parser.add_argument("csv_path", type=str, help="Ruta al CSV de entrada")
    parser.add_argument(
        "--test-size", type=float, default=0.2,
        help="Proporción de filas reservadas para validación (default: 0.2)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Semilla aleatoria para el split train/val (default: 42)",
    )
    args = parser.parse_args()

    print(f"Cargando dataset desde {args.csv_path}...")
    df = pd.read_csv(args.csv_path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {sorted(missing)}")

    print(f"{len(df)} filas cargadas.")
    print(f"Distribución de labels:\n{df['label'].value_counts()}")

    train_df, val_df = train_test_split(
        df,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=df["label"],
    )

    print("Preparando textos (combinando url + body)...")
    train_texts = _build_texts(train_df)
    val_texts = _build_texts(val_df)

    print("Tokenizando...")
    train_ds = PhishingDataset(train_texts, train_df["label"].tolist())
    val_ds = PhishingDataset(
        val_texts, val_df["label"].tolist(), tokenizer=train_ds.tokenizer
    )

    print("Inicializando PhishingClassifier...")
    model = PhishingClassifier()

    print("Entrenando...")
    model = train(model, train_ds, val_ds)

    print("Evaluando sobre el set de validación...")
    metrics = evaluate_model(model, val_ds)
    print(f"Métricas finales: {metrics}")


if __name__ == "__main__":
    main()
