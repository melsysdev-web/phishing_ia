import joblib

from backend.app.core.paths import get_models_dir

MODELS_DIR = get_models_dir()

MODEL_PATH = MODELS_DIR / "random_forest_v2.pkl"

FEATURES_PATH = MODELS_DIR / "feature_columns_v2.pkl"

model = joblib.load(MODEL_PATH)

feature_columns = joblib.load(
    FEATURES_PATH
)