import pandas as pd

# Ruta del dataset
DATASET_PATH = "datasets/raw/phishing_urls.csv"

# Cargar dataset
df = pd.read_csv(DATASET_PATH)

# Información general
print("\n=== INFORMACIÓN GENERAL ===")
print(df.info())

# Primeras filas
print("\n=== PRIMERAS 5 FILAS ===")
print(df.head())

# Columnas
print("\n=== COLUMNAS ===")
print(df.columns)

# Valores nulos
print("\n=== VALORES NULOS ===")
print(df.isnull().sum())

# Distribución de clases
print("\n=== DISTRIBUCIÓN ===")
print(df.iloc[:, -1].value_counts())