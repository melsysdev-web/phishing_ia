from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

# ─────────────────────────────────────────────
# Shared mock response fixture
# ─────────────────────────────────────────────

@pytest.fixture
def mock_safe_response():
    return {
        "url": "https://www.google.com",
        "risk_assessment": {
            "risk": "LOW",
            "confidence": 90,
            "score": 90,
            "reasons": ["HTTPS válido", "TLD confiable: .com", "Dominio con más de 10 años"]
        },
        "machine_learning": {
            "fusion": {
                "prediction": 0,
                "phishing_probability": 0.12,
                "legitimate_probability": 0.88,
                "rf_weight": 0.4,
                "roberta_weight": 0.6
            },
            "random_forest": {
                "prediction": 0,
                "phishing_probability": 0.13,
                "legitimate_probability": 0.87
            },
            "roberta": {
                "prediction": 1,
                "phishing_probability": 0.11,
                "legitimate_probability": 0.89
            }
        },
        "html_analysis": {
            "success": True,
            "html_features": {
                "HasTitle": 1, "HasFavicon": 1, "HasDescription": 1,
                "HasPasswordField": 0, "HasHiddenFields": 0,
                "NoOfImage": 5, "NoOfCSS": 2, "NoOfJS": 3
            }
        },
        "url_features": {
            "has_https": True, "url_length": 22,
            "num_dots": 2, "has_ip": False
        },
        "domain_info": {
            "domain": "google.com", "tld": "com", "domain_age_days": 10000
        }
    }


@pytest.fixture
def mock_phishing_response():
    return {
        "url": "http://192.168.1.1/login@paypal.com",
        "risk_assessment": {
            "risk": "HIGH",
            "confidence": 5,
            "score": 5,
            "reasons": [
                "No utiliza HTTPS",
                "Uso de dirección IP en lugar de dominio",
                "Contiene símbolo @"
            ]
        },
        "machine_learning": {
            "fusion": {
                "prediction": 1,
                "phishing_probability": 0.92,
                "legitimate_probability": 0.08,
                "rf_weight": 0.4,
                "roberta_weight": 0.6
            },
            "random_forest": {
                "prediction": 1,
                "phishing_probability": 0.90,
                "legitimate_probability": 0.10
            },
            "roberta": {
                "prediction": 0,
                "phishing_probability": 0.93,
                "legitimate_probability": 0.07
            }
        },
        "html_analysis": {"success": False, "error": "Connection refused"},
        "url_features": {
            "has_https": False, "url_length": 38,
            "has_ip": True, "contains_at_symbol": True
        },
        "domain_info": {"domain": None, "tld": None, "domain_age_days": None}
    }


# ─────────────────────────────────────────────
# Basic endpoints
# ─────────────────────────────────────────────

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_healthy_status():
    response = client.get("/health")
    assert response.json() == {"status": "healthy"}


def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_root_returns_message():
    response = client.get("/")
    assert "message" in response.json()


# ─────────────────────────────────────────────
# POST /predict — input validation
# ─────────────────────────────────────────────

def test_predict_missing_url_field_returns_422():
    response = client.post("/predict", json={})
    assert response.status_code == 422


def test_predict_invalid_body_returns_422():
    response = client.post("/predict", json={"not_url": "something"})
    assert response.status_code == 422


def test_predict_no_body_returns_422():
    response = client.post("/predict")
    assert response.status_code == 422


# ─────────────────────────────────────────────
# POST /predict — response structure
# ─────────────────────────────────────────────

def test_predict_returns_200(mock_safe_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    assert response.status_code == 200


def test_predict_response_has_all_top_level_keys(mock_safe_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    data = response.json()
    for key in [
        "url", "risk_assessment", "machine_learning",
        "html_analysis", "url_features", "domain_info"
    ]:
        assert key in data, f"Missing top-level key: {key}"


def test_predict_machine_learning_has_three_models(mock_safe_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    ml = response.json()["machine_learning"]
    assert "fusion" in ml
    assert "random_forest" in ml
    assert "roberta" in ml


def test_predict_fusion_has_required_fields(mock_safe_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    fusion = response.json()["machine_learning"]["fusion"]
    for key in [
        "prediction", "phishing_probability",
        "legitimate_probability", "rf_weight", "roberta_weight"
    ]:
        assert key in fusion, f"Missing fusion key: {key}"


def test_predict_fusion_prediction_is_binary(mock_safe_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    prediction = response.json()["machine_learning"]["fusion"]["prediction"]
    assert prediction in (0, 1)


def test_predict_risk_assessment_has_required_fields(mock_safe_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    risk = response.json()["risk_assessment"]
    for key in ["risk", "confidence", "score", "reasons"]:
        assert key in risk


# ─────────────────────────────────────────────
# POST /predict — safe vs phishing scenarios
# ─────────────────────────────────────────────

def test_predict_safe_url_low_risk(mock_safe_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": "https://www.google.com"})
    data = response.json()
    assert data["risk_assessment"]["risk"] == "LOW"
    assert data["machine_learning"]["fusion"]["prediction"] == 0


def test_predict_phishing_url_high_risk(mock_phishing_response):
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_phishing_response
    ):
        response = client.post(
            "/predict",
            json={"url": "http://192.168.1.1/login@paypal.com"}
        )
    data = response.json()
    assert data["risk_assessment"]["risk"] == "HIGH"
    assert data["machine_learning"]["fusion"]["prediction"] == 1
    assert data["machine_learning"]["fusion"]["phishing_probability"] > 0.5


def test_predict_url_echoed_in_response(mock_safe_response):
    url = "https://www.google.com"
    with patch(
        "backend.app.services.phishing_service.PhishingService.analyze",
        return_value=mock_safe_response
    ):
        response = client.post("/predict", json={"url": url})
    assert response.json()["url"] == url


# ─────────────────────────────────────────────
# Predictor unit tests (use mocked loaders from conftest)
# ─────────────────────────────────────────────

def test_rf_predictor_returns_prediction():
    from backend.app.random_forest.predictor import RandomForestPredictor
    from conftest import FEATURE_COLUMNS

    features = {col: 0 for col in FEATURE_COLUMNS}
    result = RandomForestPredictor.predict(features)
    assert "prediction" in result
    assert "phishing_probability" in result
    assert "legitimate_probability" in result


def test_rf_predictor_prediction_is_binary():
    from backend.app.random_forest.predictor import RandomForestPredictor
    from conftest import FEATURE_COLUMNS

    features = {col: 0 for col in FEATURE_COLUMNS}
    result = RandomForestPredictor.predict(features)
    assert result["prediction"] in (0, 1)


def test_rf_predictor_probabilities_in_range():
    from backend.app.random_forest.predictor import RandomForestPredictor
    from conftest import FEATURE_COLUMNS

    features = {col: 1 for col in FEATURE_COLUMNS}
    result = RandomForestPredictor.predict(features)
    assert 0.0 <= result["phishing_probability"] <= 1.0
    assert 0.0 <= result["legitimate_probability"] <= 1.0


def test_roberta_predictor_returns_prediction():
    from backend.app.roberta.predictor import RobertaPredictor

    result = RobertaPredictor.predict("https://example.com")
    assert "prediction" in result
    assert "phishing_probability" in result
    assert "legitimate_probability" in result


def test_roberta_predictor_probabilities_in_range():
    from backend.app.roberta.predictor import RobertaPredictor

    result = RobertaPredictor.predict("http://192.168.1.1/login")
    assert 0.0 <= result["phishing_probability"] <= 1.0
    assert 0.0 <= result["legitimate_probability"] <= 1.0
