import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report
)

# ==========================
# CARGAR DATASET
# ==========================

DATASET_PATH = "datasets/raw/phishing_urls.csv"

print("Cargando dataset...")

df = pd.read_csv(DATASET_PATH)

print(f"Registros encontrados: {len(df)}")

# ==========================
# ELIMINAR COLUMNAS TEXTO
# ==========================

columns_to_drop = [
    "FILENAME",
    "URL",
    "Domain",
    "Title",
    "TLD"
]

X = df.drop(
    columns=columns_to_drop + ["label"]
)

y = df["label"]

# ==========================
# VALIDACIONES
# ==========================

print("\n=== TIPOS DE DATOS ===")
print(X.dtypes.value_counts())

non_numeric_columns = X.select_dtypes(
    include=["object"]
).columns.tolist()

print("\n=== COLUMNAS NO NUMÉRICAS ===")
print(non_numeric_columns)

if len(non_numeric_columns) > 0:
    raise ValueError(
        f"Existen columnas no numéricas: {non_numeric_columns}"
    )

# ==========================
# DIVISIÓN DEL DATASET
# ==========================

print("\nDividiendo dataset...")

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print(f"Entrenamiento: {len(X_train)} registros")
print(f"Prueba: {len(X_test)} registros")

# ==========================
# ENTRENAMIENTO
# ==========================

print("\nEntrenando Random Forest...")

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)

print("Entrenamiento finalizado.")

# ==========================
# EVALUACIÓN
# ==========================

print("\nEvaluando modelo...")

predictions = model.predict(
    X_test
)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n==============================")
print("RESULTADOS DEL MODELO")
print("==============================")

print(
    f"\nAccuracy: {accuracy:.4f}"
)

print(
    "\nReporte de clasificación:\n"
)

print(
    classification_report(
        y_test,
        predictions
    )
)

# ==========================
# GUARDAR MODELO
# ==========================

joblib.dump(
    model,
    "models/random_forest.pkl"
)

# Guardar nombres de columnas
joblib.dump(
    X.columns.tolist(),
    "models/feature_columns.pkl"
)

print(
    "\nModelo guardado en:"
)

print(
    "models/random_forest.pkl"
)

print(
    "\nColumnas guardadas en:"
)

print(
    "models/feature_columns.pkl"
)

print(
    "\nProceso completado correctamente."
)

feature_importance = pd.DataFrame({
    "feature": X.columns,
    "importance": model.feature_importances_
})

feature_importance = feature_importance.sort_values(
    by="importance",
    ascending=False
)

print("\nTOP 20 FEATURES")
print(feature_importance.head(20))