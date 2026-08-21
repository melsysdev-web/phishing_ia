"""Límite de peticiones de análisis simultáneas.

Medido en la imagen de producción (`backend/Dockerfile`, torch CPU) contra un
contenedor capado a los 512 MB del free tier de Render:

| Peticiones a /predict en paralelo | Pico RSS | Resultado          |
|-----------------------------------|----------|--------------------|
| 1                                 |  395 MiB | 200 OK             |
| 2                                 |  441 MiB | OOM, worker muerto |
| 3                                 |  482 MiB | OOM, worker muerto |
| 6                                 |  500 MiB | OOM, worker muerto |
| 6, con 2 GB                       |  874 MiB | 200 OK             |

El endpoint `/predict` es `def` (no `async def`), así que FastAPI lo despacha en
su threadpool: sin este semáforo caben hasta 40 pipelines a la vez, cada uno
abriendo además su propio pool de 6 workers. Dos peticiones concurrentes bastan
para pasarse de 512 MB.

Y pasarse no degrada, colapsa: el kernel mata al worker único
(`WEB_CONCURRENCY=1`) y con él se cae el servicio entero, así que /health
también empieza a fallar hasta que Render reinicia. Serializar convierte esa
caída total en una espera de unos segundos.

El semáforo es compartido por /predict y /analyze-content a propósito: son
procesos distintos del pipeline pero cargan sus modelos en la misma memoria, y
lo que hay que acotar es el total residente, no cada endpoint por su cuenta.

`MAX_CONCURRENT_ANALYSES` sube el límite sin tocar código para cuando el
servicio corra en una instancia con más RAM (con 2 GB medidos, 6 caben de
sobra).
"""

import logging
import os
import threading
from contextlib import contextmanager

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _positive_int(name: str, default: int) -> int:
    """Lee un entero > 0 del entorno; un valor inválido cae al default.

    Una env var mal escrita no debe dejar el semáforo en 0 (cuelga cada
    petición) ni en negativo (ValueError al arrancar).
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r no es un entero; se usa %d", name, raw, default)
        return default
    if value < 1:
        logger.warning("%s=%d debe ser >= 1; se usa %d", name, value, default)
        return default
    return value


MAX_CONCURRENT_ANALYSES: int = _positive_int("MAX_CONCURRENT_ANALYSES", 1)

# Cuánto espera en cola una petición antes de rendirse. Por encima de esto el
# cliente ya ha visto un timeout de todas formas (la extensión aborta a los
# 60 s), así que devolver 503 es más honesto que seguir ocupando un hilo.
ANALYSIS_QUEUE_TIMEOUT: int = _positive_int("ANALYSIS_QUEUE_TIMEOUT", 30)

_slots = threading.BoundedSemaphore(MAX_CONCURRENT_ANALYSES)


@contextmanager
def analysis_slot():
    """Reserva uno de los turnos de análisis o aborta con 503.

    Uso:
        with analysis_slot():
            return PhishingService.analyze(url)
    """
    if not _slots.acquire(timeout=ANALYSIS_QUEUE_TIMEOUT):
        logger.warning(
            "Cola de análisis saturada: %d turnos ocupados durante %ds",
            MAX_CONCURRENT_ANALYSES,
            ANALYSIS_QUEUE_TIMEOUT,
        )
        raise HTTPException(
            status_code=503,
            detail="Servidor ocupado analizando otras peticiones. Reintenta en unos segundos.",
            headers={"Retry-After": str(ANALYSIS_QUEUE_TIMEOUT)},
        )
    try:
        yield
    finally:
        _slots.release()


def status() -> dict:
    """Config activa, para el log de arranque.

    A propósito no se publica en /metadata, que no lleva autenticación: el
    proyecto ya dejó fuera de ahí la config del experimento por lo mismo, y
    aquí además el dato es munición directa para saturar el servicio.
    """
    return {
        "max_concurrent_analyses": MAX_CONCURRENT_ANALYSES,
        "analysis_queue_timeout_seconds": ANALYSIS_QUEUE_TIMEOUT,
    }
