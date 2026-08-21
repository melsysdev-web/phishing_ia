"""Tests del semáforo que serializa /predict y /analyze-content.

Sin este límite dos peticiones concurrentes se pasan de los 512 MB del free
tier de Render y el kernel mata al worker, tumbando el servicio entero (medido:
1 petición = 395 MiB, 2 = OOM). Ver backend/app/core/concurrency.py.
"""

import threading
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core import concurrency
from backend.app.main import app

client = TestClient(app)

_FAKE_RESULT = {
    "url": "https://example.com",
    "cached": False,
    "analysis_time_ms": 1,
    "risk_assessment": {"risk": "LOW", "score": 90, "reasons": []},
    "machine_learning": {},
    "html_analysis": {},
    "url_features": {},
    "domain_info": {},
    "virustotal": {},
    "safe_browsing": {},
    "fact_check": {},
}


@pytest.fixture(autouse=True)
def _fresh_semaphore():
    """Cada test arranca con el semáforo libre.

    Es estado global del módulo: un test que dejara un turno cogido haría
    fallar a los siguientes con un 503 desconcertante.
    """
    original = concurrency._slots
    concurrency._slots = threading.BoundedSemaphore(concurrency.MAX_CONCURRENT_ANALYSES)
    yield
    concurrency._slots = original


def test_solo_un_analisis_a_la_vez():
    """Dos hilos dentro de analysis_slot() nunca se solapan."""
    dentro = 0
    pico = 0
    lock = threading.Lock()
    listos = threading.Barrier(2)

    def worker():
        nonlocal dentro, pico
        listos.wait()
        with concurrency.analysis_slot():
            with lock:
                dentro += 1
                pico = max(pico, dentro)
            # Ventana suficiente para que el otro hilo se solaparía si pudiera
            threading.Event().wait(0.05)
            with lock:
                dentro -= 1

    hilos = [threading.Thread(target=worker) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=10)

    assert pico == 1, f"se solaparon {pico} análisis; el semáforo no serializa"


def test_el_turno_se_libera_tras_una_excepcion():
    """Un fallo dentro del pipeline no puede dejar el turno cogido.

    Si se filtrara, la siguiente petición esperaría el timeout completo y
    devolvería 503 para siempre: el servicio quedaría muerto en caliente.
    """
    with pytest.raises(ValueError):
        with concurrency.analysis_slot():
            raise ValueError("el pipeline explotó")

    # El turno debe estar disponible otra vez
    assert concurrency._slots.acquire(timeout=1)
    concurrency._slots.release()


def test_predict_devuelve_503_cuando_la_cola_esta_saturada():
    """Con el turno ocupado, /predict se rinde con 503 en vez de encolarse."""
    concurrency._slots.acquire()
    try:
        with patch.object(concurrency, "ANALYSIS_QUEUE_TIMEOUT", 0.1):
            res = client.post("/predict", json={"url": "https://example.com"})
    finally:
        concurrency._slots.release()

    assert res.status_code == 503
    assert res.headers.get("Retry-After") is not None
    assert "ocupado" in res.json()["detail"].lower()


def test_analyze_content_comparte_el_mismo_limite():
    """Los dos endpoints pesados comparten turno.

    Cargan modelos distintos pero en la misma memoria del proceso: acotar cada
    endpoint por separado no acotaría el total residente, que es lo que cuenta.
    """
    concurrency._slots.acquire()
    try:
        with patch.object(concurrency, "ANALYSIS_QUEUE_TIMEOUT", 0.1):
            res = client.post("/analyze-content", json={"text": "x" * 400})
    finally:
        concurrency._slots.release()

    assert res.status_code == 503


def test_predict_funciona_con_el_turno_libre():
    """El semáforo no debe estorbar en el caso normal."""
    with patch(
        "backend.app.api.routes.PhishingService.analyze", return_value=_FAKE_RESULT
    ):
        res = client.post("/predict", json={"url": "https://example.com"})

    assert res.status_code == 200
    # Y el turno quedó libre para la siguiente
    assert concurrency._slots.acquire(timeout=1)
    concurrency._slots.release()


@pytest.mark.parametrize(
    "raw,esperado",
    [
        (None, 1),      # sin configurar
        ("4", 4),       # válido
        ("0", 1),       # 0 colgaría cada petición
        ("-2", 1),      # negativo reventaría BoundedSemaphore
        ("muchos", 1),  # no numérico
        ("", 1),        # vacío
    ],
)
def test_config_invalida_cae_al_default(raw, esperado):
    """Una env var mal puesta no puede dejar el servicio inservible."""
    env = {} if raw is None else {"MAX_CONCURRENT_ANALYSES": raw}
    with patch.dict("os.environ", env, clear=False):
        if raw is None:
            import os

            os.environ.pop("MAX_CONCURRENT_ANALYSES", None)
        assert concurrency._positive_int("MAX_CONCURRENT_ANALYSES", 1) == esperado


def test_la_config_no_se_publica_en_metadata():
    """/metadata no lleva autenticación.

    Saber que solo cabe un análisis simultáneo le dice a cualquiera cuántas
    peticiones hacen falta para dejar el servicio inaccesible. Va al log de
    arranque, no al endpoint público (mismo criterio que /experiment/status).
    """
    body = client.get("/metadata").json()

    assert "max_concurrent_analyses" not in body
    assert "analysis_queue_timeout_seconds" not in body


def test_status_expone_la_config_para_el_log():
    got = concurrency.status()

    assert got["max_concurrent_analyses"] == concurrency.MAX_CONCURRENT_ANALYSES
    assert got["analysis_queue_timeout_seconds"] == concurrency.ANALYSIS_QUEUE_TIMEOUT
