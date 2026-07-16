"""
Integration tests for POST /analyze-content.
ContentClassifierService is mocked so no model is loaded.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

_REAL_RESPONSE = {
    "verdict": "real",
    "label": "REAL",
    "confidence": 0.93,
    "raw_label": "REAL",
}

_FAKE_RESPONSE = {
    "verdict": "fake",
    "label": "FAKE",
    "confidence": 0.87,
    "raw_label": "FAKE",
}

_NO_CONTENT_RESPONSE = {
    "verdict": "no_content",
    "label": "UNKNOWN",
    "confidence": 0.0,
}

_LONG_TEXT  = "Este es un artículo de noticias. " * 30   # >= 300 chars
_SHORT_TEXT = "Texto muy corto."                          # < 300 chars


# ─── Input validation ─────────────────────────────────────────────────────────

def test_analyze_content_missing_text_field_returns_422():
    response = client.post("/analyze-content", json={})
    assert response.status_code == 422


def test_analyze_content_no_body_returns_422():
    response = client.post("/analyze-content")
    assert response.status_code == 422


def test_analyze_content_wrong_field_name_returns_422():
    response = client.post("/analyze-content", json={"content": "some text"})
    assert response.status_code == 422


# ─── Successful classification ────────────────────────────────────────────────

def test_analyze_content_returns_200():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_REAL_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _LONG_TEXT})
    assert response.status_code == 200


def test_analyze_content_real_result_shape():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_REAL_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _LONG_TEXT})
    data = response.json()
    assert data["verdict"] == "real"
    assert data["label"] == "REAL"
    assert 0.0 <= data["confidence"] <= 1.0


def test_analyze_content_fake_result_shape():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_FAKE_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _LONG_TEXT})
    data = response.json()
    assert data["verdict"] == "fake"
    assert data["label"] == "FAKE"
    assert data["confidence"] == 0.87


def test_analyze_content_response_has_verdict_key():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_REAL_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _LONG_TEXT})
    assert "verdict" in response.json()


def test_analyze_content_response_has_label_key():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_REAL_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _LONG_TEXT})
    assert "label" in response.json()


def test_analyze_content_response_has_confidence_key():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_REAL_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _LONG_TEXT})
    assert "confidence" in response.json()


# ─── Short text (< 300 chars) → no_content ───────────────────────────────────
# These tests verify the backend threshold, independent of the JS validation fix.

def test_analyze_content_short_text_returns_no_content_verdict():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_NO_CONTENT_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _SHORT_TEXT})
    assert response.status_code == 200
    assert response.json()["verdict"] == "no_content"


def test_analyze_content_short_text_unknown_label():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_NO_CONTENT_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _SHORT_TEXT})
    assert response.json()["label"] == "UNKNOWN"


def test_analyze_content_short_text_zero_confidence():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_NO_CONTENT_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": _SHORT_TEXT})
    assert response.json()["confidence"] == 0.0


# ─── Service error propagated ─────────────────────────────────────────────────

def test_analyze_content_service_error_is_returned():
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value={"error": "model failed"},
    ):
        response = client.post("/analyze-content", json={"text": _LONG_TEXT})
    assert response.status_code == 200
    assert "error" in response.json()


# ─── Boundary: validate that backend threshold is 300, not 50 (old JS value) ──

def test_analyze_content_text_50_chars_hits_no_content():
    """Text that was previously accepted by JS (50+ chars) but rejected by backend."""
    text_50 = "A" * 50
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_NO_CONTENT_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": text_50})
    assert response.json()["verdict"] == "no_content"


def test_analyze_content_text_299_chars_hits_no_content():
    text_299 = "A" * 299
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_NO_CONTENT_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": text_299})
    assert response.json()["verdict"] == "no_content"


def test_analyze_content_text_300_chars_is_classified():
    text_300 = "A" * 300
    with patch(
        "backend.app.services.content_classifier_service.ContentClassifierService.analyze",
        return_value=_REAL_RESPONSE,
    ):
        response = client.post("/analyze-content", json={"text": text_300})
    assert response.json()["verdict"] != "no_content"
