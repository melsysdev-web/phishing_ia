# Hiperparámetros y configuración central del detector de phishing

MODEL_NAME: str = "roberta-base"

# Tokenizador
MAX_LENGTH: int = 512

# Entrenamiento
BATCH_SIZE: int = 16
LEARNING_RATE: float = 2e-5
EPOCHS: int = 10
WARMUP_RATIO: float = 0.1
WEIGHT_DECAY: float = 0.01
EARLY_STOPPING_PATIENCE: int = 3

# Arquitectura del clasificador
DROPOUT: float = 0.1
HIDDEN_DIM: int = 256   # tamaño de la capa intermedia (768 → 256 → 2)

# Inferencia
DEFAULT_THRESHOLD: float = 0.5
PREDICT_BATCH_SIZE: int = 32

# Rutas de artefactos
CHECKPOINT_DIR: str = "checkpoints/phishing_detector"
