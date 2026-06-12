from unittest.mock import patch, MagicMock

import pytest
import requests

from backend.app.services.virustotal_service import VirusTotalService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_get(status_code=200, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    return r


def _mock_post(status_code=200, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    return r


_STATS_CLEAN = {
    "data": {
        "attributes": {
            "last_analysis_stats": {
                "malicious": 0, "suspicious": 0,
                "harmless": 72, "undetected": 17
            }
        }
    }
}

_STATS_MALICIOUS = {
    "data": {
        "attributes": {
            "last_analysis_stats": {
                "malicious": 5, "suspicious": 1,
                "harmless": 60, "undetected": 10
            }
        }
    }
}

_STATS_SUSPICIOUS = {
    "data": {
        "attributes": {
            "last_analysis_stats": {
                "malicious": 1, "suspicious": 2,
                "harmless": 68, "undetected": 8
            }
        }
    }
}

_ANALYSIS_RESPONSE = {
    "data": {
        "attributes": {
            "stats": {
                "malicious": 4, "suspicious": 0,
                "harmless": 65, "undetected": 10
            }
        }
    }
}

_SUBMIT_RESPONSE = {"data": {"id": "analysis-abc123"}}


# ── Sin API key ───────────────────────────────────────────────────────────────

def test_no_api_key_returns_error():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", ""
    ):
        result = VirusTotalService.analyze("https://example.com")
    assert "error" in result


# ── URL encontrada (GET 200) ──────────────────────────────────────────────────

def test_clean_url_returns_clean_verdict():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, _STATS_CLEAN)):
        result = VirusTotalService.analyze("https://google.com")

    assert result["verdict"] == "clean"
    assert result["stats"]["malicious"] == 0


def test_malicious_url_returns_malicious_verdict():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, _STATS_MALICIOUS)):
        result = VirusTotalService.analyze("http://evil.xyz/payload")

    assert result["verdict"] == "malicious"
    assert result["is_malicious"] is True
    assert result["stats"]["malicious"] == 5


def test_suspicious_url_returns_suspicious_verdict():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, _STATS_SUSPICIOUS)):
        result = VirusTotalService.analyze("http://suspicious-site.top/login")

    assert result["verdict"] == "suspicious"


# ── Umbrales del veredicto ────────────────────────────────────────────────────

def test_three_malicious_engines_is_malicious():
    body = {"data": {"attributes": {"last_analysis_stats": {
        "malicious": 3, "suspicious": 0, "harmless": 60, "undetected": 5
    }}}}
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, body)):
        result = VirusTotalService.analyze("http://borderline.com")

    assert result["verdict"] == "malicious"


def test_two_malicious_engines_is_suspicious():
    body = {"data": {"attributes": {"last_analysis_stats": {
        "malicious": 2, "suspicious": 0, "harmless": 60, "undetected": 5
    }}}}
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, body)):
        result = VirusTotalService.analyze("http://borderline.com")

    assert result["verdict"] == "suspicious"


def test_zero_detections_is_clean():
    body = {"data": {"attributes": {"last_analysis_stats": {
        "malicious": 0, "suspicious": 0, "harmless": 80, "undetected": 5
    }}}}
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, body)):
        result = VirusTotalService.analyze("https://clean-site.com")

    assert result["verdict"] == "clean"
    assert result["is_malicious"] is False
    assert result["is_suspicious"] is False


# ── URL no encontrada (GET 404) → submit + fetch ──────────────────────────────

def test_404_triggers_submission():
    mock_get_404 = _mock_get(404)
    mock_get_analysis = _mock_get(200, _ANALYSIS_RESPONSE)
    mock_post_submit = _mock_post(200, _SUBMIT_RESPONSE)

    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch(
        "requests.get", side_effect=[mock_get_404, mock_get_analysis]
    ), patch("requests.post", return_value=mock_post_submit):
        result = VirusTotalService.analyze("https://new-site.com")

    assert "verdict" in result
    assert result["stats"]["malicious"] == 4


def test_404_submit_failure_returns_error():
    mock_get_404  = _mock_get(404)
    mock_post_err = _mock_post(403)

    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=mock_get_404), \
       patch("requests.post", return_value=mock_post_err):
        result = VirusTotalService.analyze("https://new-site.com")

    assert "error" in result


def test_404_analysis_fetch_failure_returns_error():
    mock_get_404      = _mock_get(404)
    mock_post_ok      = _mock_post(200, _SUBMIT_RESPONSE)
    mock_get_analysis = _mock_get(500)

    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch(
        "requests.get", side_effect=[mock_get_404, mock_get_analysis]
    ), patch("requests.post", return_value=mock_post_ok):
        result = VirusTotalService.analyze("https://new-site.com")

    assert "error" in result


# ── Errores HTTP ──────────────────────────────────────────────────────────────

def test_server_error_returns_error():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(500)):
        result = VirusTotalService.analyze("https://example.com")

    assert "error" in result
    assert "500" in result["error"]


def test_timeout_returns_error():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", side_effect=requests.Timeout):
        result = VirusTotalService.analyze("https://example.com")

    assert "error" in result
    assert "timed out" in result["error"].lower()


def test_connection_error_returns_error():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch(
        "requests.get",
        side_effect=requests.RequestException("Connection refused")
    ):
        result = VirusTotalService.analyze("https://example.com")

    assert "error" in result


# ── Estructura de respuesta ───────────────────────────────────────────────────

def test_response_has_verdict_and_stats():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, _STATS_CLEAN)):
        result = VirusTotalService.analyze("https://example.com")

    assert "verdict" in result
    assert "stats" in result
    assert "malicious" in result["stats"]
    assert "total_engines" in result["stats"]


def test_total_engines_is_sum_of_all_categories():
    with patch(
        "backend.app.services.virustotal_service._API_KEY", "fake-key"
    ), patch("requests.get", return_value=_mock_get(200, _STATS_CLEAN)):
        result = VirusTotalService.analyze("https://example.com")

    s = result["stats"]
    assert s["total_engines"] == s["malicious"] + s["harmless"] + s["undetected"]
