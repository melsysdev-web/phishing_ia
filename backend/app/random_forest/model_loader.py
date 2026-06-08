import joblib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

MODEL_PATH = BASE_DIR / "models" / "random_forest_v2.pkl"

FEATURES_PATH = (
    BASE_DIR
    / "models"
    / "feature_columns_v2.pkl"
)

model = joblib.load(MODEL_PATH)

feature_columns = joblib.load(
    FEATURES_PATH
)