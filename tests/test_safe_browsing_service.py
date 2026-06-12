from unittest.mock import patch, MagicMock

import pytest
import requests

from backend.app.services.safe_browsing_service import SafeBrowsingService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_post(status_code=200, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    return r


_CLEAN_RESPONSE       = {}
_MALWARE_RESPONSE     = {"matches": [{"threatType": "MALWARE",             "platformType": "ANY_PLATFORM", "cacheDuration": "300s"}]}
_PHISHING_RESPONSE    = {"matches": [{"threatType": "SOCIAL_ENGINEERING",  "platformType": "ANY_PLATFORM", "cacheDuration": "300s"}]}
_UNWANTED_RESPONSE    = {"matches": [{"threatType": "UNWANTED_SOFTWARE",   "platformType": "ANY_PLATFORM", "cacheDuration": "300s"}]}
_MULTI_THREAT         = {"matches": [
    {"threatType": "MALWARE",           "platformType": "ANY_PLATFORM", "cacheDuration": "300s"},
    {"threatType": "SOCIAL_ENGINEERING","platformType": "ANY_PLATFORM", "cacheDuration": "300s"},
]}


# ── Sin API key ───────────────────────────────────────────────────────────────

def test_no_api_key_returns_error():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", ""
    ):
        result = SafeBrowsingService.analyze("https://example.com")
    assert "error" in result


# ── URL limpia ────────────────────────────────────────────────────────────────

def test_clean_url_returns_no_threat():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _CLEAN_RESPONSE)):
        result = SafeBrowsingService.analyze("https://google.com")

    assert result["is_threat"] is False
    assert result["verdict"] == "clean"
    assert result["threats"] == []


# ── Amenazas detectadas ───────────────────────────────────────────────────────

def test_malware_url_is_dangerous():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _MALWARE_RESPONSE)):
        result = SafeBrowsingService.analyze("http://malware-host.xyz/payload.exe")

    assert result["is_threat"] is True
    assert result["verdict"] == "dangerous"
    assert any(t["type"] == "MALWARE" for t in result["threats"])


def test_phishing_url_is_dangerous():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _PHISHING_RESPONSE)):
        result = SafeBrowsingService.analyze("http://paypal-secure-login.xyz")

    assert result["is_threat"] is True
    assert result["verdict"] == "dangerous"
    assert any(t["type"] == "SOCIAL_ENGINEERING" for t in result["threats"])


def test_unwanted_software_is_suspicious():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _UNWANTED_RESPONSE)):
        result = SafeBrowsingService.analyze("http://adware-bundle.top/install.exe")

    assert result["is_threat"] is True
    assert result["verdict"] == "suspicious"


def test_multiple_threats_all_returned():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _MULTI_THREAT)):
        result = SafeBrowsingService.analyze("http://very-bad-site.com")

    assert len(result["threats"]) == 2
    types = {t["type"] for t in result["threats"]}
    assert "MALWARE" in types
    assert "SOCIAL_ENGINEERING" in types


def test_multi_threat_with_malware_is_dangerous():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _MULTI_THREAT)):
        result = SafeBrowsingService.analyze("http://very-bad-site.com")

    assert result["verdict"] == "dangerous"


# ── Estructura de amenaza ─────────────────────────────────────────────────────

def test_threat_entry_has_type_and_platform():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _MALWARE_RESPONSE)):
        result = SafeBrowsingService.analyze("http://evil.com")

    threat = result["threats"][0]
    assert "type" in threat
    assert "platform" in threat


def test_threat_entry_has_cache_duration():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(200, _MALWARE_RESPONSE)):
        result = SafeBrowsingService.analyze("http://evil.com")

    assert "cache_duration" in result["threats"][0]


# ── Errores HTTP ──────────────────────────────────────────────────────────────

def test_api_error_400_returns_error():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(400)):
        result = SafeBrowsingService.analyze("https://example.com")

    assert "error" in result
    assert "400" in result["error"]


def test_api_error_403_returns_error():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", return_value=_mock_post(403)):
        result = SafeBrowsingService.analyze("https://example.com")

    assert "error" in result


def test_timeout_returns_error():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch("requests.post", side_effect=requests.Timeout):
        result = SafeBrowsingService.analyze("https://example.com")

    assert "error" in result
    assert "timed out" in result["error"].lower()


def test_connection_error_returns_error():
    with patch(
        "backend.app.services.safe_browsing_service._API_KEY", "fake-key"
    ), patch(
        "requests.post",
        side_effect=requests.RequestException("Network unreachable")
    ):
        result = SafeBrowsingService.analyze("https://example.com")

    assert "error" in result


# ── Integración con RiskEngine ────────────────────────────────────────────────

def test_risk_engine_penalizes_safe_browsing_dangerous():
    from backend.app.services.risk_engine import RiskEngine

    url_features = {
        "url_length": 30, "path_length": 10, "num_hyphens": 0,
        "has_https": True, "has_ip": False, "contains_at_symbol": False,
        "contains_double_slash_redirect": False, "num_subdomains": 0,
        "full_url": "https://clean-looking-but-flagged.com"
    }
    domain_info = {"domain_age_days": 500, "tld": "com"}

    without_sb = RiskEngine.calculate(url_features, domain_info)
    with_sb    = RiskEngine.calculate(
        url_features, domain_info,
        sb_result={
            "is_threat": True,
            "verdict": "dangerous",
            "threats": [{"type": "SOCIAL_ENGINEERING"}]
        }
    )

    assert with_sb["score"] < without_sb["score"]
    assert any("Safe Browsing" in r for r in with_sb["reasons"])


def test_risk_engine_penalizes_virustotal_malicious():
    from backend.app.services.risk_engine import RiskEngine

    url_features = {
        "url_length": 30, "path_length": 10, "num_hyphens": 0,
        "has_https": True, "has_ip": False, "contains_at_symbol": False,
        "contains_double_slash_redirect": False, "num_subdomains": 0,
        "full_url": "https://flagged-by-vt.com"
    }
    domain_info = {"domain_age_days": 500, "tld": "com"}

    without_vt = RiskEngine.calculate(url_features, domain_info)
    with_vt    = RiskEngine.calculate(
        url_features, domain_info,
        vt_result={
            "verdict": "malicious",
            "is_malicious": True,
            "stats": {"malicious": 7, "suspicious": 1, "harmless": 60, "undetected": 10, "total_engines": 78}
        }
    )

    assert with_vt["score"] < without_vt["score"]
    assert any("VirusTotal" in r for r in with_vt["reasons"])


def test_risk_engine_rewards_clean_virustotal():
    from backend.app.services.risk_engine import RiskEngine

    url_features = {
        "url_length": 30, "path_length": 10, "num_hyphens": 0,
        "has_https": True, "has_ip": False, "contains_at_symbol": False,
        "contains_double_slash_redirect": False, "num_subdomains": 0,
        "full_url": "https://clean-site.com"
    }
    domain_info = {"domain_age_days": 500, "tld": "com"}

    without_vt = RiskEngine.calculate(url_features, domain_info)
    with_vt    = RiskEngine.calculate(
        url_features, domain_info,
        vt_result={
            "verdict": "clean",
            "is_malicious": False,
            "stats": {"malicious": 0, "suspicious": 0, "harmless": 78, "undetected": 11, "total_engines": 89}
        }
    )

    assert with_vt["score"] >= without_vt["score"]
    assert any("VirusTotal" in r and "limpia" in r.lower() for r in with_vt["reasons"])


def test_risk_engine_ignores_vt_error():
    from backend.app.services.risk_engine import RiskEngine

    url_features = {
        "url_length": 30, "path_length": 10, "num_hyphens": 0,
        "has_https": True, "has_ip": False, "contains_at_symbol": False,
        "contains_double_slash_redirect": False, "num_subdomains": 0,
        "full_url": "https://example.com"
    }
    domain_info = {"domain_age_days": 500, "tld": "com"}

    result = RiskEngine.calculate(
        url_features, domain_info,
        vt_result={"error": "API key invalid"}
    )

    assert "risk" in result
    assert result["score"] >= 0


def test_risk_engine_ignores_sb_error():
    from backend.app.services.risk_engine import RiskEngine

    url_features = {
        "url_length": 30, "path_length": 10, "num_hyphens": 0,
        "has_https": True, "has_ip": False, "contains_at_symbol": False,
        "contains_double_slash_redirect": False, "num_subdomains": 0,
        "full_url": "https://example.com"
    }
    domain_info = {"domain_age_days": 500, "tld": "com"}

    result = RiskEngine.calculate(
        url_features, domain_info,
        sb_result={"error": "Safe Browsing timed out"}
    )

    assert "risk" in result
    assert result["score"] >= 0
