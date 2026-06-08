import pandas as pd

df = pd.read_csv(
    "datasets/roberta_dataset.csv"
)

print("\n=== SHAPE ===")
print(df.shape)

print("\n=== COLUMNAS ===")
print(df.columns)

print("\n=== PRIMERAS 5 FILAS ===")
print(df.head())

print("\n=== DISTRIBUCIÓN ===")
print(df["label"].value_counts())

print("\n=== PORCENTAJES ===")
print(
    df["label"]
    .value_counts(normalize=True) * 100
)