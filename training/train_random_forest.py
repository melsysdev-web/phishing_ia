import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report
)

# ==========================
# DATASET
# ==========================

DATASET_PATH = "datasets/raw/phishing_urls.csv"

print("Cargando dataset...")

df = pd.read_csv(DATASET_PATH)

print(
    f"Registros encontrados: {len(df)}"
)

# ==========================
# FEATURES DISPONIBLES
# EN PRODUCCIÓN
# ==========================

selected_features = [

    "URLLength",
    "DomainLength",
    
    "IsDomainIP",
    "TLDLength",
    "NoOfSubDomain",
    "IsHTTPS",

    "HasTitle",
    "HasFavicon",
    "HasDescription",
    "HasPasswordField",
    "HasHiddenFields",

    "NoOfImage",
    "NoOfCSS",
    "NoOfJS"
]

# ==========================
# VALIDAR COLUMNAS
# ==========================

missing_columns = [

    col
    for col in selected_features
    if col not in df.columns
]

if missing_columns:

    raise ValueError(
        f"Columnas faltantes: {missing_columns}"
    )

# ==========================
# X / Y
# ==========================

X = df[selected_features]

y = df["label"]

# ==========================
# TRAIN TEST SPLIT
# ==========================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ==========================
# MODEL
# ==========================

print(
    "\nEntrenando Random Forest V2..."
)

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)

# ==========================
# EVALUACIÓN
# ==========================

predictions = model.predict(
    X_test
)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n====================")
print("RESULTADOS V2")
print("====================")

print(
    f"\nAccuracy: {accuracy:.4f}"
)

print(
    classification_report(
        y_test,
        predictions
    )
)

# ==========================
# FEATURE IMPORTANCE
# ==========================

feature_importance = pd.DataFrame({

    "feature": X.columns,

    "importance":
        model.feature_importances_
})

feature_importance = (
    feature_importance
    .sort_values(
        by="importance",
        ascending=False
    )
)

print(
    "\nTOP FEATURES"
)

print(
    feature_importance
)

# ==========================
# GUARDAR
# ==========================

joblib.dump(
    model,
    "models/random_forest_v2.pkl"
)

joblib.dump(
    selected_features,
    "models/feature_columns_v2.pkl"
)

print(
    "\nModelo guardado:"
)

print(
    "models/random_forest_v2.pkl"
)