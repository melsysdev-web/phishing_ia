"""
Integration tests for the endpoints and middleware not covered by
test_api.py / test_content_api.py: cache introspection, API key rejection
and rate limiting.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.core import security
from backend.app.main import app

client = TestClient(app)

_MINIMAL_PREDICT_RESPONSE = {
    "url": "https://www.google.com",
    "cached": False,
    "risk_assessment": {},
    "machine_learning": {},
    "html_analysis": {},
    "url_features": {},
    "domain_info": {},
    "virustotal": {},
    "safe_browsing": {},
    "fact_check": {},
}


# ─── GET /metadata ───────────────────────────────────────────────────────────

def test_metadata_returns_200():
    response = client.get("/metadata")
    assert response.status_code == 200


def test_metadata_has_required_keys():
    response = client.get("/metadata")
    data = response.json()
    for key in [
        "api_version", "models", "rate_limit_per_minute",
        "cache_ttl_seconds", "cache_max_size",
    ]:
        assert key in data
    for key in ["random_forest", "roberta_url", "roberta_content"]:
        assert key in data["models"]


# ─── GET /cache/stats ──────────────────────────────────────────────────────

def test_cache_stats_returns_200():
    response = client.get("/cache/stats")
    assert response.status_code == 200


def test_cache_stats_has_required_keys():
    response = client.get("/cache/stats")
    data = response.json()
    for key in ["entries", "valid", "ttl_seconds", "max_size"]:
        assert key in data


# ─── DELETE /cache ──────────────────────────────────────────────────────────

def test_cache_clear_returns_200():
    response = client.delete("/cache")
    assert response.status_code == 200


def test_cache_clear_has_cleared_key():
    response = client.delete("/cache")
    assert isinstance(response.json()["cleared"], int)


# ─── require_api_key: 403 cuando API_KEY está configurada ──────────────────

def test_predict_rejects_missing_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key", "expected-secret")
    response = client.post("/predict", json={"url": "https://www.google.com"})
    assert response.status_code == 403


def test_predict_rejects_invalid_api_key(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key", "expected-secret")
    response = client.post(
        "/predict",
        json={"url": "https://www.google.com"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_predict_accepts_correct_api_key(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key", "expected-secret")
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_MINIMAL_PREDICT_RESPONSE,
    ):
        response = client.post(
            "/predict",
            json={"url": "https://www.google.com"},
            headers={"X-API-Key": "expected-secret"},
        )
    assert response.status_code == 200


# ─── RateLimitMiddleware: 429 al superar el máximo ──────────────────────────
# conftest.py resetea _rate_store (autouse) antes de cada test: es un dict
# global compartido por IP, no por endpoint, en main.py.

def test_rate_limit_returns_429_after_max_requests():
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_MINIMAL_PREDICT_RESPONSE,
    ):
        for _ in range(main_module._RATE_MAX):
            ok = client.post("/predict", json={"url": "https://www.google.com"})
            assert ok.status_code == 200

        blocked = client.post("/predict", json={"url": "https://www.google.com"})

    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"


# ─── Exception handler global: 500 controlado ───────────────────────────────
# raise_server_exceptions=False: Starlette por diseño re-lanza las excepciones
# de servidor en TestClient para visibilidad en debugging, aun cuando el
# exception_handler ya envio la respuesta 500 correcta al "cliente" real.

def test_unhandled_exception_returns_controlled_500():
    lenient_client = TestClient(app, raise_server_exceptions=False)
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        side_effect=RuntimeError("boom"),
    ):
        response = lenient_client.post("/predict", json={"url": "https://example.com"})
    assert response.status_code == 500
    assert response.json()["error"] == "Error interno del servidor"
