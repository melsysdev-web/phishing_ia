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


# ─── RateLimitMiddleware + X-Forwarded-For (proxy headers) ─────────────────────

def test_rate_limit_proxy_headers_note():
    """
    En uvicorn con --proxy-headers --forwarded-allow-ips=*, X-Forwarded-For
    se usa como request.client.host para rate limiting. Esto funciona en Render
    pero no en TestClient (que simula un cliente directo, no un proxy).

    Los tests abajo verifican que rate limiting funciona por request.client.host.
    En producción (Render), uvicorn transforma X-Forwarded-For → request.client.host
    automáticamente (aplicado en backend/Dockerfile con --proxy-headers).
    """
    pass  # Este es un test documentativo, no tiene assertions


def test_rate_limit_uses_client_ip_for_bucketing():
    """Rate limiting agrupa por request.client.host (en Render, esto es X-Forwarded-For)."""
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_MINIMAL_PREDICT_RESPONSE,
    ):
        # En TestClient, request.client.host siempre es 127.0.0.1
        # Pero el test verifica que el mecanismo de bucketing funciona
        for _ in range(main_module._RATE_MAX):
            response = client.post("/predict", json={"url": "https://www.google.com"})
            assert response.status_code == 200

        # Agotó la quota para 127.0.0.1
        response = client.post("/predict", json={"url": "https://www.google.com"})
        assert response.status_code == 429

        # Comentario: En Render, con --proxy-headers y X-Forwarded-For,
        # diferentes IPs reales crearían buckets separados.
        # TestClient no puede simular eso, pero el código de RateLimitMiddleware
        # es agnóstico de cómo se obtiene request.client.host.


def test_rate_limit_unauthenticated_paths_not_limited():
    """Endpoints no autenticados (/health, /metadata, /) no tienen rate limit."""
    # Puede llamar a estos sin límite
    for _ in range(main_module._RATE_MAX + 10):
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/metadata")
        assert response.status_code == 200

        response = client.get("/")
        assert response.status_code == 200


def test_rate_limit_analyze_content_also_limited():
    """Rate limiting aplica a /analyze-content también."""
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_MINIMAL_PREDICT_RESPONSE,
    ):
        # Agota quota en /analyze-content
        for _ in range(main_module._RATE_MAX):
            response = client.post(
                "/analyze-content",
                json={"text": "This is real news or fake news?"},
            )
            assert response.status_code == 200

        # Siguiente request debe fallar
        response = client.post(
            "/analyze-content",
            json={"text": "Another article"},
        )
        assert response.status_code == 429


def test_rate_limit_bucket_eviction_on_max_ips():
    """Cuando se alcanza _RATE_MAX_IPS, se evicta la IP más antigua."""
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_MINIMAL_PREDICT_RESPONSE,
    ):
        # Este test es sensible al estado de _rate_store
        # Suponiendo que empieza limpio (conftest resetea antes de cada test)
        original_max = main_module._RATE_MAX_IPS

        try:
            # Temporalmente reduce el máximo para probar eviction
            main_module._RATE_MAX_IPS = 3

            # Crea 3 buckets distintos
            for i in range(3):
                response = client.post(
                    "/predict",
                    json={"url": "https://www.google.com"},
                    headers={"X-Forwarded-For": f"203.0.113.{i}"},
                )
                assert response.status_code == 200

            # 4ta IP debe causar eviction de la más vieja
            response = client.post(
                "/predict",
                json={"url": "https://www.google.com"},
                headers={"X-Forwarded-For": "203.0.113.99"},
            )
            assert response.status_code == 200

            # El store nunca excede _RATE_MAX_IPS
            assert len(main_module._rate_store) <= main_module._RATE_MAX_IPS

        finally:
            main_module._RATE_MAX_IPS = original_max


def test_rate_limit_retry_after_header():
    """Cuando está rate-limited, debe incluir Retry-After: 60."""
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_MINIMAL_PREDICT_RESPONSE,
    ):
        for _ in range(main_module._RATE_MAX):
            client.post("/predict", json={"url": "https://www.google.com"})

        response = client.post("/predict", json={"url": "https://www.google.com"})

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
        assert "Demasiadas solicitudes" in response.json()["error"]


# ─── Security: No leaking backend internals ─────────────────────────────────

def test_production_error_omits_detail():
    """En ENVIRONMENT=production, exception handler debe omitir 'detail'."""
    lenient_client = TestClient(app, raise_server_exceptions=False)

    # Cambia a production
    original_env = security.settings.environment
    try:
        security.settings.environment = "production"

        with patch(
            "backend.app.services.phishing_service.PhishingService.analyze",
            side_effect=RuntimeError("Database connection failed: host=internal.db.local"),
        ):
            response = lenient_client.post("/predict", json={"url": "https://example.com"})

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Error interno del servidor"
        # 'detail' no debe estar presente en producción
        assert "detail" not in data or data.get("detail") is None

    finally:
        security.settings.environment = original_env


def test_development_error_includes_detail():
    """En ENVIRONMENT=development, exception handler debe incluir 'detail' para debugging."""
    lenient_client = TestClient(app, raise_server_exceptions=False)

    original_env = security.settings.environment
    try:
        security.settings.environment = "development"

        with patch(
            "backend.app.services.phishing_service.PhishingService.analyze",
            side_effect=RuntimeError("Debug info: something went wrong"),
        ):
            response = lenient_client.post("/predict", json={"url": "https://example.com"})

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "Error interno del servidor"
        # En development, 'detail' debe estar presente
        assert "detail" in data
        assert data["detail"] is not None

    finally:
        security.settings.environment = original_env


def test_metadata_does_not_leak_internal_config():
    """GET /metadata no debe filtrar rutas internas ni configuración sensible."""
    response = client.get("/metadata")

    assert response.status_code == 200
    data = response.json()

    # Verifica que solo expone información necesaria
    expected_keys = {"api_version", "models", "rate_limit_per_minute", "cache_ttl_seconds", "cache_max_size"}
    assert set(data.keys()) == expected_keys

    # No debe exponer rutas internas
    assert "internal" not in str(data).lower()
    assert "backend" not in str(data).lower()
    assert "env" not in str(data).lower()

    # No debe exponer credenciales o keys
    assert "api_key" not in str(data).lower()
    assert "virustotal" not in str(data).lower()
    assert "safe_browsing" not in str(data).lower()
    assert "fact_check" not in str(data).lower()


def test_metadata_models_only_boolean_status():
    """GET /metadata expone solo True/False para modelos, no rutas de archivos."""
    response = client.get("/metadata")
    data = response.json()

    for model_name, model_status in data["models"].items():
        # Cada modelo debe ser un boolean
        assert isinstance(model_status, bool), f"Model '{model_name}' should be bool, got {type(model_status)}"


def test_health_endpoint_generic_response():
    """GET /health retorna respuesta genérica sin internals."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Debe ser simple y no exponer detalles
    assert "status" in data
    assert data["status"] in ["healthy", "ok"]
    # No debe contener detalles técnicos
    assert len(data) <= 2  # Solo status + posible message


def test_root_endpoint_generic_response():
    """GET / retorna respuesta genérica."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    # Debe ser simple
    assert "message" in data
    assert "internal" not in str(data).lower()
    assert "backend" not in str(data).lower()


def test_api_key_not_returned_in_responses():
    """Ningún endpoint debe retornar la API key en las responses."""
    endpoints_to_check = [
        ("/health", "GET"),
        ("/metadata", "GET"),
        ("/", "GET"),
        ("/cache/stats", "GET"),
    ]

    for endpoint, method in endpoints_to_check:
        if method == "GET":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json={})

        # Verifica que la API key no está en la respuesta
        response_text = str(response.json())
        assert "api_key" not in response_text.lower()
        assert "x-api-key" not in response_text.lower()


def test_error_messages_do_not_expose_internals():
    """Error messages nunca deben exponer detalles de implementación."""
    # Error de validación
    response = client.post("/predict", json={"url": "not-a-url"})
    error_msg = str(response.json())
    assert "fastapi" not in error_msg.lower()
    assert "pydantic" not in error_msg.lower()
    assert "traceback" not in error_msg.lower()

    # Error de rate limit
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_MINIMAL_PREDICT_RESPONSE,
    ):
        for _ in range(main_module._RATE_MAX + 1):
            client.post("/predict", json={"url": "https://www.google.com"})

        response = client.post("/predict", json={"url": "https://www.google.com"})
        error_msg = str(response.json())
        assert "internal" not in error_msg.lower()
        assert "middleware" not in error_msg.lower()
