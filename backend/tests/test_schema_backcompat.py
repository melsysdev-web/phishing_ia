"""
Compatibilidad del schema con respuestas cacheadas por versiones anteriores.

El cache warm (extended_cache) persiste 30 días en SQLite, así que tras un
deploy se siguen sirviendo entradas escritas por la versión previa. El
response_model debe aceptar ese shape antiguo en lugar de devolver un 500.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

# Shape que escribía la versión anterior a la calibración: confidence era un
# entero igual al score y no existían los campos de incertidumbre.
_LEGACY_CACHED_RESPONSE = {
    "url": "https://www.google.com",
    "cached": True,
    "risk_assessment": {
        "risk": "LOW",
        "confidence": 90,
        "score": 90,
        "reasons": ["HTTPS válido"],
    },
    "machine_learning": {},
    "html_analysis": {},
    "url_features": {},
    "domain_info": {},
    "virustotal": {},
    "safe_browsing": {},
    "fact_check": {},
}


def _post_legacy():
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=_LEGACY_CACHED_RESPONSE,
    ):
        return client.post("/predict", json={"url": "https://www.google.com"})


def test_legacy_cached_response_does_not_500():
    assert _post_legacy().status_code == 200


def test_legacy_cached_response_preserves_core_fields():
    risk = _post_legacy().json()["risk_assessment"]
    assert risk["risk"] == "LOW"
    assert risk["score"] == 90
    assert risk["reasons"] == ["HTTPS válido"]


def test_legacy_cached_response_reports_missing_calibration_as_null():
    risk = _post_legacy().json()["risk_assessment"]
    for key in ("probability", "probability_interval", "score_interval", "ml_agreement"):
        assert risk[key] is None


def test_empty_risk_assessment_does_not_500():
    payload = dict(_LEGACY_CACHED_RESPONSE, risk_assessment={})
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=payload,
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    assert response.status_code == 200
