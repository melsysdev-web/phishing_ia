import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def get_models_dir() -> Path:
    """Directorio donde viven los .pkl / carpetas de modelos HuggingFace.

    Por defecto asume el layout del repo (models/ junto a backend/). En
    despliegue se puede montar un volumen en otra ruta y apuntarlo con
    MODELS_DIR (ver backend/Dockerfile y docker-compose.yml).
    """
    override = os.getenv("MODELS_DIR")
    if override:
        return Path(override)
    return _REPO_ROOT / "models"
