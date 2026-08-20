"""
Almacén de correcciones enviadas por usuarios.

Cada entrada registra un veredicto que el usuario considera equivocado. Es la
fuente de datos etiquetados que hoy no existe y que bloquea el reentrenamiento
de los modelos (ensemble apilado, features cruzadas, fine-tuning).

Diseño deliberado:
- La URL se guarda hasheada, no en claro: el backend no necesita saber qué
  sitios visita cada usuario para aprender de sus correcciones.
- Los fallos de escritura no propagan: una corrección perdida no debe romper
  el análisis que el usuario pidió.
"""

import hashlib
import sqlite3
import threading
import time
from pathlib import Path

from backend.app.core.paths import get_models_dir

# Veredictos que un usuario puede reportar como el correcto.
VALID_LABELS = frozenset({"LOW", "MEDIUM", "HIGH"})

_lock = threading.Lock()
_db_path = None
_initialized = False


def _get_db_path():
    global _db_path
    if _db_path is None:
        _db_path = Path(get_models_dir()).parent / "feedback.db"
    return _db_path


def _init_db():
    global _initialized
    if _initialized:
        return
    try:
        conn = sqlite3.connect(str(_get_db_path()))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT NOT NULL,
                predicted_risk TEXT NOT NULL,
                predicted_score INTEGER NOT NULL,
                reported_risk TEXT NOT NULL,
                confidence REAL,
                variant TEXT,
                timestamp REAL NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_feedback_ts ON feedback(timestamp)"
        )
        conn.commit()
        conn.close()
        _initialized = True
    except sqlite3.Error:
        # Sin persistencia el análisis sigue funcionando; sólo se pierde el dato.
        pass


def hash_url(url: str) -> str:
    """Identificador estable de una URL, sin exponer la URL en sí."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def record(
    url: str,
    predicted_risk: str,
    predicted_score: int,
    reported_risk: str,
    confidence: float = None,
    variant: str = None,
) -> bool:
    """
    Guarda una corrección. Devuelve True si se persistió.

    Un `reported_risk` fuera de VALID_LABELS se rechaza: datos de entrenamiento
    con etiquetas arbitrarias son peores que no tener datos.
    """
    if reported_risk not in VALID_LABELS:
        return False

    _init_db()
    try:
        with _lock:
            conn = sqlite3.connect(str(_get_db_path()))
            conn.execute(
                """INSERT INTO feedback
                   (url_hash, predicted_risk, predicted_score, reported_risk,
                    confidence, variant, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    hash_url(url),
                    predicted_risk,
                    int(predicted_score),
                    reported_risk,
                    confidence,
                    variant,
                    time.time(),
                ),
            )
            conn.commit()
            conn.close()
        return True
    except (sqlite3.Error, ValueError, TypeError):
        return False


def stats() -> dict:
    """
    Resumen de las correcciones acumuladas.

    `disagreements_by_direction` distingue los dos errores, que tienen costes
    muy distintos: marcar como peligroso un sitio legítimo molesta al usuario;
    dejar pasar phishing lo expone.
    """
    _init_db()
    empty = {
        "total": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "by_predicted_risk": {},
    }
    try:
        conn = sqlite3.connect(str(_get_db_path()))
        cursor = conn.cursor()

        total = cursor.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]

        # Predijimos peligro y el usuario dice que era seguro.
        false_positives = cursor.execute(
            """SELECT COUNT(*) FROM feedback
               WHERE predicted_risk = 'HIGH' AND reported_risk = 'LOW'"""
        ).fetchone()[0]

        # Dijimos que era seguro y el usuario reporta phishing.
        false_negatives = cursor.execute(
            """SELECT COUNT(*) FROM feedback
               WHERE predicted_risk = 'LOW' AND reported_risk = 'HIGH'"""
        ).fetchone()[0]

        by_risk = dict(
            cursor.execute(
                "SELECT predicted_risk, COUNT(*) FROM feedback GROUP BY predicted_risk"
            ).fetchall()
        )

        conn.close()
        return {
            "total": total,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "by_predicted_risk": by_risk,
        }
    except sqlite3.Error:
        return empty


def export_training_rows(limit: int = 10000) -> list:
    """
    Correcciones en forma consumible por un reentrenamiento.

    Sin uso todavía: los modelos no pueden reentrenarse hasta acumular
    suficientes filas. Existe para que el dato recogido hoy sea utilizable
    sin migraciones más adelante.
    """
    _init_db()
    try:
        conn = sqlite3.connect(str(_get_db_path()))
        rows = conn.execute(
            """SELECT url_hash, predicted_risk, predicted_score,
                      reported_risk, confidence, variant, timestamp
               FROM feedback ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        return [
            {
                "url_hash": r[0],
                "predicted_risk": r[1],
                "predicted_score": r[2],
                "reported_risk": r[3],
                "confidence": r[4],
                "variant": r[5],
                "timestamp": r[6],
            }
            for r in rows
        ]
    except sqlite3.Error:
        return []


def clear() -> int:
    """Borra todas las correcciones. Devuelve cuántas se eliminaron."""
    _init_db()
    try:
        with _lock:
            conn = sqlite3.connect(str(_get_db_path()))
            count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            conn.execute("DELETE FROM feedback")
            conn.commit()
            conn.close()
        return count
    except sqlite3.Error:
        return 0
