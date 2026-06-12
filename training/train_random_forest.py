import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.metrics import accuracy_score, classification_report

# ==========================
# DATASET
# ==========================

DATASET_PATH = "datasets/raw/phishing_urls.csv"

print("Cargando dataset...")

df = pd.read_csv(DATASET_PATH)

print(f"Registros encontrados: {len(df)}")

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
    "NoOfJS",
]

# ==========================
# VALIDAR COLUMNAS
# ==========================

missing_columns = [col for col in selected_features if col not in df.columns]

if missing_columns:
    raise ValueError(f"Columnas faltantes: {missing_columns}")

# ==========================
# X / Y
# ==========================

X = df[selected_features]
y = df["label"]

print(f"\nDistribución de clases:\n{y.value_counts().to_string()}")

# ==========================
# CROSS-VALIDATION (5 folds)
# ==========================

print("\nEjecutando cross-validation (5 folds)...")

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

cv_model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    n_jobs=-1,
)

scoring = [
    "accuracy",
    "precision_weighted",
    "recall_weighted",
    "f1_weighted",
    "roc_auc",
]

cv_results = cross_validate(
    cv_model,
    X,
    y,
    cv=cv,
    scoring=scoring,
    n_jobs=-1,
)

print("\n====================")
print("CROSS-VALIDATION (5 folds)")
print("====================")

metrics = {
    "Accuracy":  "test_accuracy",
    "Precision": "test_precision_weighted",
    "Recall":    "test_recall_weighted",
    "F1":        "test_f1_weighted",
    "ROC-AUC":   "test_roc_auc",
}

for label, key in metrics.items():
    scores = cv_results[key]
    print(f"  {label:12s}: {scores.mean():.4f} ± {scores.std():.4f}")

# ==========================
# TRAIN TEST SPLIT
# ==========================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)

# ==========================
# MODELO FINAL
# ==========================

print("\nEntrenando modelo final (80% datos)...")

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    n_jobs=-1,
)

model.fit(X_train, y_train)

# ==========================
# EVALUACIÓN EN TEST SET
# ==========================

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\n====================")
print("EVALUACIÓN EN TEST SET (20%)")
print("====================")

print(f"\n  Accuracy: {accuracy:.4f}")
print(classification_report(y_test, predictions))

# ==========================
# FEATURE IMPORTANCE
# ==========================

feature_importance = (
    pd.DataFrame({
        "feature":    X.columns,
        "importance": model.feature_importances_,
    })
    .sort_values(by="importance", ascending=False)
    .reset_index(drop=True)
)

print("TOP FEATURES")
print(feature_importance.to_string(index=False))

# ==========================
# GUARDAR
# ==========================

joblib.dump(model, "models/random_forest_v2.pkl")
joblib.dump(selected_features, "models/feature_columns_v2.pkl")

print("\nModelo guardado:")
print("  models/random_forest_v2.pkl")
print("  models/feature_columns_v2.pkl")
