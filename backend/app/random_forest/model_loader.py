import joblib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

MODEL_PATH = BASE_DIR / "models" / "random_forest.pkl"

FEATURES_PATH = (
    BASE_DIR
    / "models"
    / "feature_columns.pkl"
)

model = joblib.load(MODEL_PATH)

feature_columns = joblib.load(
    FEATURES_PATH
)