from unittest.mock import MagicMock, patch

import requests

from backend.app.services import virustotal_service
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
    with patch.object(virustotal_service, "_API_KEY", ""):
        result = VirusTotalService.analyze("https://example.com")
    assert "error" in result


# ── URL encontrada (GET 200) ──────────────────────────────────────────────────

def test_clean_url_returns_clean_verdict():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, _STATS_CLEAN)
    ):
        result = VirusTotalService.analyze("https://google.com")

    assert result["verdict"] == "clean"
    assert result["stats"]["malicious"] == 0


def test_malicious_url_returns_malicious_verdict():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, _STATS_MALICIOUS)
    ):
        result = VirusTotalService.analyze("http://evil.xyz/payload")

    assert result["verdict"] == "malicious"
    assert result["is_malicious"] is True
    assert result["stats"]["malicious"] == 5


def test_suspicious_url_returns_suspicious_verdict():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, _STATS_SUSPICIOUS)
    ):
        result = VirusTotalService.analyze("http://suspicious-site.top/login")

    assert result["verdict"] == "suspicious"


# ── Umbrales del veredicto ────────────────────────────────────────────────────

def test_three_malicious_engines_is_malicious():
    body = {"data": {"attributes": {"last_analysis_stats": {
        "malicious": 3, "suspicious": 0, "harmless": 60, "undetected": 5
    }}}}
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, body)
    ):
        result = VirusTotalService.analyze("http://borderline.com")

    assert result["verdict"] == "malicious"


def test_two_malicious_engines_is_suspicious():
    body = {"data": {"attributes": {"last_analysis_stats": {
        "malicious": 2, "suspicious": 0, "harmless": 60, "undetected": 5
    }}}}
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, body)
    ):
        result = VirusTotalService.analyze("http://borderline.com")

    assert result["verdict"] == "suspicious"


def test_zero_detections_is_clean():
    body = {"data": {"attributes": {"last_analysis_stats": {
        "malicious": 0, "suspicious": 0, "harmless": 80, "undetected": 5
    }}}}
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, body)
    ):
        result = VirusTotalService.analyze("https://clean-site.com")

    assert result["verdict"] == "clean"
    assert result["is_malicious"] is False
    assert result["is_suspicious"] is False


# ── URL no encontrada (GET 404) → retorna error sin submit ─────────────────────

def test_404_returns_error_without_submit():
    """URLs nuevas (no en VT) no hacen submit, devuelven error."""
    mock_get_404 = _mock_get(404)

    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=mock_get_404
    ) as mock_get, patch.object(
        virustotal_service._SESSION, "post"
    ) as mock_post:
        result = VirusTotalService.analyze("https://new-site.com")

    # Should not call POST (submit)
    mock_post.assert_not_called()
    # Should return error
    assert "error" in result
    assert "url_not_in_virustotal" in result["error"]


def test_404_submit_not_called():
    """Verify submit is never called on 404."""
    mock_get_404  = _mock_get(404)

    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=mock_get_404
    ), patch.object(virustotal_service._SESSION, "post") as mock_post:
        VirusTotalService.analyze("https://new-site.com")

    # POST should never be called (no submit)
    mock_post.assert_not_called()


def test_404_quota_check_before_call():
    """Verify quota is checked BEFORE making the GET call."""
    from backend.app.core.quota_circuit import vt_quota
    mock_get = _mock_get(404)

    vt_quota.tripped = True  # Simulate quota exceeded

    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=mock_get
    ) as mock_session_get:
        result = VirusTotalService.analyze("https://example.com")

    # Should return quota error without calling VT
    assert result["error"] == "quota_exceeded"
    mock_session_get.assert_not_called()

    vt_quota.tripped = False  # Clean up


# ── Errores HTTP ──────────────────────────────────────────────────────────────

def test_server_error_returns_error():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(500)
    ):
        result = VirusTotalService.analyze("https://example.com")

    assert "error" in result
    assert "500" in result["error"]


def test_timeout_returns_error():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", side_effect=requests.Timeout
    ):
        result = VirusTotalService.analyze("https://example.com")

    assert "error" in result
    assert "timed out" in result["error"].lower()


def test_connection_error_returns_error():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION,
        "get",
        side_effect=requests.RequestException("Connection refused"),
    ):
        result = VirusTotalService.analyze("https://example.com")

    assert "error" in result


# ── Estructura de respuesta ───────────────────────────────────────────────────

def test_response_has_verdict_and_stats():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, _STATS_CLEAN)
    ):
        result = VirusTotalService.analyze("https://example.com")

    assert "verdict" in result
    assert "stats" in result
    assert "malicious" in result["stats"]
    assert "total_engines" in result["stats"]


def test_total_engines_is_sum_of_all_categories():
    with patch.object(virustotal_service, "_API_KEY", "fake-key"), patch.object(
        virustotal_service._SESSION, "get", return_value=_mock_get(200, _STATS_CLEAN)
    ):
        result = VirusTotalService.analyze("https://example.com")

    s = result["stats"]
    assert s["total_engines"] == s["malicious"] + s["harmless"] + s["undetected"]
