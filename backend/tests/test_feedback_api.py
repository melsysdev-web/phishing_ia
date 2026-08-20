"""Tests del endpoint POST /feedback y GET /feedback/stats."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import feedback_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(feedback_store, "_db_path", Path(tmp) / "feedback.db")
        monkeypatch.setattr(feedback_store, "_initialized", False)
        yield


_VALID = {
    "url": "https://example.com",
    "predicted_risk": "HIGH",
    "predicted_score": 20,
    "reported_risk": "LOW",
}


class TestSubmitFeedback:
    def test_valid_feedback_is_accepted(self):
        response = client.post("/feedback", json=_VALID)
        assert response.status_code == 200
        assert response.json()["recorded"] is True

    def test_response_reports_running_total(self):
        client.post("/feedback", json=_VALID)
        response = client.post("/feedback", json={**_VALID, "url": "https://other.com"})
        assert response.json()["total"] == 2

    def test_optional_fields_are_accepted(self):
        payload = {**_VALID, "confidence": 0.9, "variant": "candidate"}
        assert client.post("/feedback", json=payload).status_code == 200

    def test_risk_labels_are_case_insensitive(self):
        payload = {**_VALID, "predicted_risk": "high", "reported_risk": "low"}
        assert client.post("/feedback", json=payload).status_code == 200


class TestValidation:
    def test_invalid_risk_label_is_rejected(self):
        payload = {**_VALID, "reported_risk": "CATASTROPHIC"}
        assert client.post("/feedback", json=payload).status_code == 422

    def test_score_above_100_is_rejected(self):
        assert client.post("/feedback", json={**_VALID, "predicted_score": 150}).status_code == 422

    def test_negative_score_is_rejected(self):
        assert client.post("/feedback", json={**_VALID, "predicted_score": -5}).status_code == 422

    def test_confidence_above_one_is_rejected(self):
        assert client.post("/feedback", json={**_VALID, "confidence": 1.5}).status_code == 422

    def test_missing_required_field_is_rejected(self):
        assert client.post("/feedback", json={"url": "https://example.com"}).status_code == 422


class TestFeedbackStats:
    def test_stats_endpoint_returns_200(self):
        assert client.get("/feedback/stats").status_code == 200

    def test_stats_start_empty(self):
        assert client.get("/feedback/stats").json()["total"] == 0

    def test_stats_reflect_submitted_feedback(self):
        client.post("/feedback", json=_VALID)
        data = client.get("/feedback/stats").json()
        assert data["total"] == 1
        assert data["false_positives"] == 1

    def test_stats_have_required_keys(self):
        data = client.get("/feedback/stats").json()
        for key in ("total", "false_positives", "false_negatives", "by_predicted_risk"):
            assert key in data


class TestPrivacy:
    def test_submitted_url_is_not_readable_from_stats(self):
        url = "https://muy-privado.example.com/perfil"
        client.post("/feedback", json={**_VALID, "url": url})
        assert "muy-privado" not in str(client.get("/feedback/stats").json())


class TestExperimentStatusEndpoint:
    def test_status_endpoint_returns_200(self):
        assert client.get("/experiment/status").status_code == 200

    def test_status_reports_disabled_by_default(self):
        assert client.get("/experiment/status").json()["enabled"] is False

    def test_experiment_config_is_absent_from_public_metadata(self):
        """El reparto de tráfico no debe publicarse sin autenticación."""
        assert "experiment" not in client.get("/metadata").json()
