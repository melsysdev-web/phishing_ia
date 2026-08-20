"""
Asignación de variantes para probar cambios de scoring en producción.

Permite exponer una variante nueva a una fracción del tráfico y comparar su
comportamiento contra la actual antes de adoptarla.

La asignación es determinista por URL: la misma URL cae siempre en la misma
variante. Sin eso, dos análisis de la misma URL podrían devolver veredictos
distintos, y el cache — que no distingue variantes — serviría el de quien
llegó primero.
"""

import hashlib
import os

CONTROL = "control"

# Fracción de tráfico enviada a la variante nueva, vía EXPERIMENT_ROLLOUT
# (0.0 = desactivado, 1.0 = todo el tráfico). Fuera de rango se ignora.
_DEFAULT_ROLLOUT = 0.0


def _read_rollout() -> float:
    raw = os.getenv("EXPERIMENT_ROLLOUT", "")
    if not raw:
        return _DEFAULT_ROLLOUT
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_ROLLOUT
    if not 0.0 <= value <= 1.0:
        return _DEFAULT_ROLLOUT
    return value


def _read_variant_name() -> str:
    return os.getenv("EXPERIMENT_VARIANT", "candidate")


def _bucket(url: str) -> float:
    """Posición estable de una URL en [0, 1)."""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    # 8 hex = 32 bits, suficiente resolución para repartir tráfico.
    return int(digest[:8], 16) / 0xFFFFFFFF


def assign(url: str) -> str:
    """
    Devuelve la variante que le corresponde a esta URL.

    Con rollout 0.0 (por defecto) siempre devuelve CONTROL, así que el
    experimento está inactivo mientras nadie lo configure explícitamente.
    """
    rollout = _read_rollout()
    if rollout <= 0.0:
        return CONTROL
    if rollout >= 1.0:
        return _read_variant_name()
    return _read_variant_name() if _bucket(url) < rollout else CONTROL


def status() -> dict:
    """Configuración activa del experimento, para inspección y monitoreo."""
    rollout = _read_rollout()
    return {
        "enabled": rollout > 0.0,
        "rollout": rollout,
        "variant": _read_variant_name(),
        "control": CONTROL,
    }
