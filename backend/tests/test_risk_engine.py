from backend.app.services.risk_engine import RiskEngine

_SAFE_FEATS = {
    "full_url": "https://www.google.com/",
    "has_https": True,
    "has_ip": False,
    "contains_at_symbol": False,
    "contains_double_slash_redirect": False,
    "num_subdomains": 1,
    "num_hyphens": 0,
}

_PHISHING_FEATS = {
    "full_url": "http://192.168.1.1/login",
    "has_https": False,
    "has_ip": True,
    "contains_at_symbol": False,
    "contains_double_slash_redirect": False,
    "num_subdomains": 0,
    "num_hyphens": 0,
}

_EMPTY_DOMAIN = {}
_OLD_DOMAIN = {"domain_age_days": 3650, "tld": "com"}
_NEW_DOMAIN = {"domain_age_days": 5, "tld": "com"}


class TestRiskEngineOutputShape:

    def test_returns_required_keys(self):
        result = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        assert {"risk", "score", "confidence", "reasons"}.issubset(result.keys())

    def test_score_is_integer_in_range(self):
        result = RiskEngine.calculate(_PHISHING_FEATS, _EMPTY_DOMAIN)
        assert 0 <= result["score"] <= 100

    def test_risk_is_valid_label(self):
        result = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        assert result["risk"] in {"LOW", "MEDIUM", "HIGH"}

    def test_reasons_is_list(self):
        result = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) > 0


class TestRiskEngineUrlSignals:

    def test_https_raises_score_vs_http(self):
        safe = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        unsafe = RiskEngine.calculate(
            {**_SAFE_FEATS, "has_https": False, "full_url": "http://www.google.com/"},
            _EMPTY_DOMAIN,
        )
        assert safe["score"] > unsafe["score"]

    def test_ip_url_is_high_risk(self):
        result = RiskEngine.calculate(_PHISHING_FEATS, _EMPTY_DOMAIN)
        assert result["risk"] == "HIGH"

    def test_at_symbol_drives_score_below_50(self):
        feats = {
            **_SAFE_FEATS,
            "full_url": "https://legit.com@evil.com/",
            "contains_at_symbol": True,
        }
        result = RiskEngine.calculate(feats, _EMPTY_DOMAIN)
        assert result["score"] < 50

    def test_excessive_subdomains_reduce_score(self):
        many = RiskEngine.calculate(
            {**_SAFE_FEATS, "num_subdomains": 4}, _EMPTY_DOMAIN
        )
        few = RiskEngine.calculate(
            {**_SAFE_FEATS, "num_subdomains": 1}, _EMPTY_DOMAIN
        )
        assert many["score"] < few["score"]

    def test_excessive_domain_hyphens_reduce_score(self):
        hyphens = RiskEngine.calculate(
            {**_SAFE_FEATS, "num_hyphens_domain": 5}, _EMPTY_DOMAIN
        )
        clean = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        assert hyphens["score"] < clean["score"]

    def test_path_hyphens_do_not_reduce_score(self):
        """Los slugs de noticias y documentación usan guiones y son legítimos."""
        path_hyphens = RiskEngine.calculate(
            {**_SAFE_FEATS, "num_hyphens": 9, "num_hyphens_domain": 0}, _EMPTY_DOMAIN
        )
        clean = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        assert path_hyphens["score"] == clean["score"]

    def test_url_shortener_reduces_score(self):
        short = RiskEngine.calculate(
            {**_SAFE_FEATS, "full_url": "https://bit.ly/abc123"}, _EMPTY_DOMAIN
        )
        normal = RiskEngine.calculate(
            {**_SAFE_FEATS, "full_url": "https://example.com/page"}, _EMPTY_DOMAIN
        )
        assert short["score"] < normal["score"]

    def test_brand_impersonation_in_subdomain_reduces_score(self):
        impersonation = RiskEngine.calculate(
            {**_SAFE_FEATS, "full_url": "https://paypal.evil.com/login"}, _EMPTY_DOMAIN
        )
        clean = RiskEngine.calculate(
            {**_SAFE_FEATS, "full_url": "https://normal.example.com/"}, _EMPTY_DOMAIN
        )
        assert impersonation["score"] < clean["score"]

    def test_trusted_brand_domain_low_risk(self):
        result = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        assert result["risk"] == "LOW"

    def test_double_slash_redirect_reduces_score(self):
        with_redirect = RiskEngine.calculate(
            {**_SAFE_FEATS, "contains_double_slash_redirect": True}, _EMPTY_DOMAIN
        )
        clean = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        assert with_redirect["score"] < clean["score"]


class TestRiskEngineDomainSignals:

    def test_domain_under_30_days_reason_text(self):
        result = RiskEngine.calculate(_SAFE_FEATS, {"domain_age_days": 10, "tld": "com"})
        assert any("30 días" in r for r in result["reasons"])

    def test_domain_under_180_days_reason_text(self):
        result = RiskEngine.calculate(_SAFE_FEATS, {"domain_age_days": 90, "tld": "com"})
        assert any("nuevo" in r for r in result["reasons"])

    def test_none_domain_age_does_not_crash(self):
        result = RiskEngine.calculate(_SAFE_FEATS, {"domain_age_days": None, "tld": "com"})
        assert "risk" in result

    def test_new_domain_reduces_score(self):
        old = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        new = RiskEngine.calculate(_SAFE_FEATS, _NEW_DOMAIN)
        assert new["score"] < old["score"]

    def test_domain_under_30_days_is_high_risk_factor(self):
        new_domain = RiskEngine.calculate(
            _PHISHING_FEATS, {"domain_age_days": 10, "tld": "com"}
        )
        assert new_domain["risk"] == "HIGH"

    def test_suspicious_tld_reduces_score(self):
        bad_tld = RiskEngine.calculate(
            _SAFE_FEATS, {"domain_age_days": 365, "tld": "xyz"}
        )
        good_tld = RiskEngine.calculate(
            _SAFE_FEATS, {"domain_age_days": 365, "tld": "com"}
        )
        assert bad_tld["score"] < good_tld["score"]

    def test_trusted_tld_raises_score(self):
        com = RiskEngine.calculate(_SAFE_FEATS, {"domain_age_days": 365, "tld": "com"})
        xyz = RiskEngine.calculate(_SAFE_FEATS, {"domain_age_days": 365, "tld": "xyz"})
        assert com["score"] > xyz["score"]


class TestRiskEngineHtmlSignals:

    def test_password_field_reduces_score(self):
        without_html = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        with_html = RiskEngine.calculate(
            _SAFE_FEATS,
            _EMPTY_DOMAIN,
            html_analysis={
                "success": True,
                "html_features": {"HasPasswordField": 1, "HasTitle": 1},
            },
        )
        assert with_html["score"] < without_html["score"]
        assert any("contraseña" in r for r in with_html["reasons"])

    def test_failed_html_analysis_is_skipped(self):
        result = RiskEngine.calculate(
            _SAFE_FEATS, _EMPTY_DOMAIN,
            html_analysis={"success": False, "error": "timeout"},
        )
        assert "risk" in result


class TestRiskEngineReasonText:

    def test_https_reason_present(self):
        result = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        assert "HTTPS válido" in result["reasons"]

    def test_no_https_reason_present(self):
        feats = {**_SAFE_FEATS, "has_https": False, "full_url": "http://www.google.com/"}
        result = RiskEngine.calculate(feats, _EMPTY_DOMAIN)
        assert "No utiliza HTTPS" in result["reasons"]

    def test_ip_reason_present(self):
        result = RiskEngine.calculate(_PHISHING_FEATS, _EMPTY_DOMAIN)
        assert any("IP" in r for r in result["reasons"])

    def test_at_symbol_reason_present(self):
        feats = {
            **_SAFE_FEATS,
            "full_url": "https://legit.com@evil.com/",
            "contains_at_symbol": True,
        }
        result = RiskEngine.calculate(feats, _EMPTY_DOMAIN)
        assert any("@" in r for r in result["reasons"])

    def test_excessive_subdomains_reason_present(self):
        result = RiskEngine.calculate(
            {**_SAFE_FEATS, "num_subdomains": 4}, _EMPTY_DOMAIN
        )
        assert any("subdominio" in r for r in result["reasons"])


class TestRiskEngineExternalServices:

    def test_virustotal_malicious_forces_high_and_caps_score(self):
        vt = {"verdict": "malicious", "stats": {"malicious": 10}}
        result = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN, vt_result=vt)
        assert result["risk"] == "HIGH"
        assert result["score"] <= 25

    def test_virustotal_suspicious_reduces_score(self):
        vt_suspicious = {"verdict": "suspicious"}
        base = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        with_vt = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN, vt_result=vt_suspicious)
        assert with_vt["score"] < base["score"]

    def test_virustotal_clean_raises_score(self):
        vt_clean = {"verdict": "clean"}
        base = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        with_vt = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN, vt_result=vt_clean)
        assert with_vt["score"] >= base["score"]

    def test_safe_browsing_dangerous_forces_high_and_caps_score(self):
        sb = {
            "is_threat": True,
            "verdict": "dangerous",
            "threats": [{"type": "MALWARE"}],
        }
        result = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN, sb_result=sb)
        assert result["risk"] == "HIGH"
        assert result["score"] <= 25

    def test_safe_browsing_clean_raises_score(self):
        sb_clean = {"is_threat": False}
        base = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        with_sb = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN, sb_result=sb_clean)
        assert with_sb["score"] >= base["score"]

    def test_ml_high_phishing_probability_reduces_score(self):
        ml = {"phishing_probability": 0.92}
        base = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        with_ml = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN, ml_result=ml)
        assert with_ml["score"] < base["score"]

    def test_ml_low_phishing_probability_raises_score(self):
        ml = {"phishing_probability": 0.05}
        base = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        with_ml = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN, ml_result=ml)
        assert with_ml["score"] > base["score"]

    def test_ml_medium_probability_no_large_delta(self):
        ml = {"phishing_probability": 0.50}
        base = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        with_ml = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN, ml_result=ml)
        assert abs(with_ml["score"] - base["score"]) < 20

    def test_errored_services_are_ignored(self):
        result = RiskEngine.calculate(
            _SAFE_FEATS,
            _EMPTY_DOMAIN,
            vt_result={"error": "API timeout"},
            sb_result={"error": "quota exceeded"},
            fc_result={"error": "not found"},
            ml_result={"error": "model error"},
        )
        assert "risk" in result
        assert 0 <= result["score"] <= 100

    def test_fact_check_reliable_raises_score(self):
        fc = {"verdict": "reliable", "publisher_count": 2}
        base = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        with_fc = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN, fc_result=fc)
        assert with_fc["score"] >= base["score"]

    def test_ml_error_dict_is_ignored(self):
        base = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN)
        with_error = RiskEngine.calculate(
            _SAFE_FEATS, _EMPTY_DOMAIN, ml_result={"error": "model error"}
        )
        assert with_error["score"] == base["score"]

    def test_ml_none_is_ignored(self):
        result = RiskEngine.calculate(_SAFE_FEATS, _EMPTY_DOMAIN, ml_result=None)
        assert result is not None


class TestRiskEngineScoreThresholds:

    def test_score_gte_80_is_low_risk(self):
        result = RiskEngine.calculate(_SAFE_FEATS, _OLD_DOMAIN)
        if result["score"] >= 80:
            assert result["risk"] == "LOW"

    def test_score_lt_50_is_high_risk(self):
        result = RiskEngine.calculate(_PHISHING_FEATS, _NEW_DOMAIN)
        assert result["score"] < 50
        assert result["risk"] == "HIGH"

    def test_score_between_50_and_79_is_medium_risk(self):
        feats = {
            **_SAFE_FEATS,
            "full_url": "https://some-newsite.info/",
            "has_https": True,
        }
        domain = {"domain_age_days": 200, "tld": "info"}
        result = RiskEngine.calculate(feats, domain)
        if 50 <= result["score"] < 80:
            assert result["risk"] == "MEDIUM"
