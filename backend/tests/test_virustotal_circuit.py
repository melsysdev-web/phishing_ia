"""Tests para integración de circuit breaker en virustotal_service.py."""

from unittest.mock import patch, MagicMock

import pytest

from backend.app.services.virustotal_service import VirusTotalService
from backend.app.core.quota_circuit import vt_quota


class TestVirusTotalCircuitIntegration:
    """Tests para VT + circuit breaker."""

    def setup_method(self):
        """Reset circuit breaker before each test."""
        vt_quota.call_count = 0
        vt_quota.tripped = False
        vt_quota.trip_reason = None

    def test_analyze_returns_quota_exceeded_when_circuit_open(self):
        vt_quota.tripped = True
        response = VirusTotalService.analyze("https://example.com")
        assert response["error"] == "quota_exceeded"
        assert "quota" in response.get("detail", "").lower()

    def test_analyze_records_call_on_success(self):
        with patch(
            "backend.app.services.virustotal_service._SESSION.get"
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 0,
                            "suspicious": 0,
                            "harmless": 50,
                            "undetected": 10,
                        }
                    }
                }
            }
            mock_get.return_value = mock_response

            initial_count = vt_quota.call_count
            VirusTotalService.analyze("https://example.com")
            assert vt_quota.call_count == initial_count + 1

    def test_analyze_returns_not_in_vt_on_404(self):
        with patch(
            "backend.app.services.virustotal_service._SESSION.get"
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            response = VirusTotalService.analyze("https://newurl.com")
            assert response["error"] == "url_not_in_virustotal"
            # Should NOT submit
            assert mock_get.call_count == 1  # Only GET, no POST

    def test_analyze_trips_circuit_on_429(self):
        with patch(
            "backend.app.services.virustotal_service._SESSION.get"
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response

            vt_quota.tripped = False
            response = VirusTotalService.analyze("https://example.com")

            assert response["error"] == "quota_exceeded"
            assert vt_quota.tripped is True
            assert vt_quota.trip_reason == "http_429_received"

    def test_no_api_key_returns_error(self):
        with patch(
            "backend.app.services.virustotal_service._API_KEY", None
        ):
            response = VirusTotalService.analyze("https://example.com")
            assert response["error"] == "VIRUSTOTAL_API_KEY not configured"

    def test_timeout_returns_error(self):
        import requests

        with patch(
            "backend.app.services.virustotal_service._SESSION.get"
        ) as mock_get:
            mock_get.side_effect = requests.Timeout()
            response = VirusTotalService.analyze("https://example.com")
            error_msg = response.get("error", "").lower()
            assert "timeout" in error_msg or "timed out" in error_msg

    def test_valid_response_parsed_correctly(self):
        with patch(
            "backend.app.services.virustotal_service._SESSION.get"
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 5,
                            "suspicious": 2,
                            "harmless": 40,
                            "undetected": 5,
                        }
                    }
                }
            }
            mock_get.return_value = mock_response

            response = VirusTotalService.analyze("https://example.com")
            assert response["verdict"] == "malicious"
            assert response["is_malicious"] is True
            assert response["stats"]["malicious"] == 5

    def test_malformed_response_handled(self):
        with patch(
            "backend.app.services.virustotal_service._SESSION.get"
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"invalid": "format"}
            mock_get.return_value = mock_response

            response = VirusTotalService.analyze("https://example.com")
            assert "error" in response
            assert "formato" in response["error"].lower()

    def test_other_status_code_returns_error(self):
        with patch(
            "backend.app.services.virustotal_service._SESSION.get"
        ) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            response = VirusTotalService.analyze("https://example.com")
            assert "error" in response
            assert "500" in response["error"]
