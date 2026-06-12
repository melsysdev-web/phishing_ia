import pytest
from backend.app.services.risk_engine import RiskEngine


def _base_features(**overrides):
    base = {
        "url_length": 22,
        "path_length": 1,
        "num_hyphens": 0,
        "has_https": True,
        "has_ip": False,
        "contains_at_symbol": False,
        "contains_double_slash_redirect": False,
        "num_subdomains": 0,
        "full_url": "https://example.com"
    }
    base.update(overrides)
    return base


def _base_domain(**overrides):
    base = {"domain_age_days": None, "tld": "com"}
    base.update(overrides)
    return base


# ── Risk level classification ────────────────────────────────────────

def test_safe_url_is_low_risk(url_features_safe, domain_info_trusted):
    result = RiskEngine.calculate(url_features_safe, domain_info_trusted)
    assert result["risk"] == "LOW"
    assert result["score"] >= 80


def test_phishing_url_is_high_risk(url_features_phishing, domain_info_suspicious):
    result = RiskEngine.calculate(url_features_phishing, domain_info_suspicious)
    assert result["risk"] == "HIGH"
    assert result["score"] < 50


def test_result_has_required_keys(url_features_safe, domain_info_trusted):
    result = RiskEngine.calculate(url_features_safe, domain_info_trusted)
    for key in ["risk", "confidence", "score", "reasons"]:
        assert key in result


def test_risk_values_are_valid(url_features_safe, domain_info_trusted):
    result = RiskEngine.calculate(url_features_safe, domain_info_trusted)
    assert result["risk"] in ("LOW", "MEDIUM", "HIGH")


# ── HTTPS ─────────────────────────────────────────────────────────────

def test_https_adds_reason():
    result = RiskEngine.calculate(
        _base_features(has_https=True),
        _base_domain()
    )
    assert "HTTPS válido" in result["reasons"]


def test_no_https_adds_reason_and_reduces_score():
    with_https = RiskEngine.calculate(_base_features(has_https=True), _base_domain())
    without_https = RiskEngine.calculate(_base_features(has_https=False), _base_domain())
    assert "No utiliza HTTPS" in without_https["reasons"]
    assert without_https["score"] < with_https["score"]


# ── IP in URL ─────────────────────────────────────────────────────────

def test_ip_in_url_penalizes():
    without_ip = RiskEngine.calculate(_base_features(has_ip=False), _base_domain())
    with_ip = RiskEngine.calculate(_base_features(has_ip=True), _base_domain())
    assert with_ip["score"] < without_ip["score"]
    assert any("IP" in r for r in with_ip["reasons"])


# ── @ symbol ─────────────────────────────────────────────────────────

def test_at_symbol_penalizes():
    result = RiskEngine.calculate(
        _base_features(contains_at_symbol=True),
        _base_domain()
    )
    assert any("@" in r for r in result["reasons"])


# ── Subdomains ────────────────────────────────────────────────────────

def test_excessive_subdomains_penalizes():
    normal = RiskEngine.calculate(_base_features(num_subdomains=1), _base_domain())
    excessive = RiskEngine.calculate(_base_features(num_subdomains=4), _base_domain())
    assert excessive["score"] < normal["score"]
    assert any("subdominio" in r for r in excessive["reasons"])


# ── URL / path length ─────────────────────────────────────────────────

def test_long_url_penalizes():
    short = RiskEngine.calculate(_base_features(url_length=30), _base_domain())
    long_ = RiskEngine.calculate(_base_features(url_length=100), _base_domain())
    assert long_["score"] <= short["score"]


def test_long_path_penalizes():
    short = RiskEngine.calculate(_base_features(path_length=10), _base_domain())
    long_ = RiskEngine.calculate(_base_features(path_length=60), _base_domain())
    assert long_["score"] <= short["score"]


# ── Hyphens ───────────────────────────────────────────────────────────

def test_many_hyphens_penalizes():
    few = RiskEngine.calculate(_base_features(num_hyphens=1), _base_domain())
    many = RiskEngine.calculate(_base_features(num_hyphens=5), _base_domain())
    assert many["score"] <= few["score"]


# ── Suspicious keywords ───────────────────────────────────────────────

def test_phishing_keywords_penalize():
    clean_url = _base_features(full_url="https://example.com/home")
    phishing_url = _base_features(
        full_url="https://example.com/login/verify/account/reset/bank/paypal"
    )
    clean = RiskEngine.calculate(clean_url, _base_domain())
    suspicious = RiskEngine.calculate(phishing_url, _base_domain())
    assert suspicious["score"] <= clean["score"]


# ── Domain age ────────────────────────────────────────────────────────

def test_very_new_domain_penalizes():
    result = RiskEngine.calculate(_base_features(), _base_domain(domain_age_days=10))
    assert any("30 días" in r for r in result["reasons"])


def test_relatively_new_domain_penalizes():
    result = RiskEngine.calculate(_base_features(), _base_domain(domain_age_days=90))
    assert any("nuevo" in r for r in result["reasons"])


def test_old_domain_adds_score():
    young = RiskEngine.calculate(_base_features(), _base_domain(domain_age_days=400))
    old = RiskEngine.calculate(_base_features(), _base_domain(domain_age_days=5000))
    assert old["score"] > young["score"]


def test_none_domain_age_ignored():
    result = RiskEngine.calculate(_base_features(), _base_domain(domain_age_days=None))
    assert result is not None


# ── TLD ───────────────────────────────────────────────────────────────

def test_suspicious_tld_penalizes():
    trusted = RiskEngine.calculate(_base_features(), _base_domain(tld="com"))
    suspicious = RiskEngine.calculate(_base_features(), _base_domain(tld="xyz"))
    assert suspicious["score"] < trusted["score"]
    assert any("xyz" in r for r in suspicious["reasons"])


def test_trusted_tld_adds_reason():
    result = RiskEngine.calculate(_base_features(), _base_domain(tld="gov"))
    assert any("gov" in r for r in result["reasons"])


# ── HTML analysis ─────────────────────────────────────────────────────

def test_password_field_penalizes(url_features_safe, domain_info_trusted):
    without_html = RiskEngine.calculate(url_features_safe, domain_info_trusted)
    with_html = RiskEngine.calculate(
        url_features_safe,
        domain_info_trusted,
        html_analysis={
            "success": True,
            "html_features": {
                "HasPasswordField": 1,
                "HasHiddenFields": 0,
                "HasTitle": 1,
                "HasFavicon": 1,
                "NoOfJS": 0,
                "NoOfImage": 0
            }
        }
    )
    assert with_html["score"] < without_html["score"]
    assert any("contraseña" in r for r in with_html["reasons"])


def test_html_analysis_failure_is_skipped(url_features_safe, domain_info_trusted):
    result = RiskEngine.calculate(
        url_features_safe,
        domain_info_trusted,
        html_analysis={"success": False, "error": "timeout"}
    )
    assert result is not None
    assert "risk" in result


# ── Score bounds ──────────────────────────────────────────────────────

def test_score_never_below_zero(url_features_phishing, domain_info_suspicious):
    result = RiskEngine.calculate(url_features_phishing, domain_info_suspicious)
    assert result["score"] >= 0


def test_score_never_above_100(url_features_safe, domain_info_trusted):
    result = RiskEngine.calculate(url_features_safe, domain_info_trusted)
    assert result["score"] <= 100


# ── ML Fusion ─────────────────────────────────────────────────────────

def test_ml_high_phishing_prob_penalizes():
    base = RiskEngine.calculate(_base_features(), _base_domain())
    with_ml = RiskEngine.calculate(
        _base_features(), _base_domain(),
        ml_result={"phishing_probability": 0.90, "legitimate_probability": 0.10}
    )
    assert with_ml["score"] < base["score"]
    assert any("alta confianza" in r for r in with_ml["reasons"])


def test_ml_moderate_phishing_prob_penalizes():
    base = RiskEngine.calculate(_base_features(), _base_domain())
    with_ml = RiskEngine.calculate(
        _base_features(), _base_domain(),
        ml_result={"phishing_probability": 0.70, "legitimate_probability": 0.30}
    )
    assert with_ml["score"] < base["score"]
    assert any("ML" in r for r in with_ml["reasons"])


def test_ml_low_phishing_prob_adds_score():
    base = RiskEngine.calculate(_base_features(), _base_domain())
    with_ml = RiskEngine.calculate(
        _base_features(), _base_domain(),
        ml_result={"phishing_probability": 0.10, "legitimate_probability": 0.90}
    )
    assert with_ml["score"] > base["score"]
    assert any("legítima" in r for r in with_ml["reasons"])


def test_ml_error_is_ignored():
    base = RiskEngine.calculate(_base_features(), _base_domain())
    with_error = RiskEngine.calculate(
        _base_features(), _base_domain(),
        ml_result={"error": "Both models failed"}
    )
    assert with_error["score"] == base["score"]


def test_ml_none_is_ignored():
    result = RiskEngine.calculate(_base_features(), _base_domain(), ml_result=None)
    assert result is not None
