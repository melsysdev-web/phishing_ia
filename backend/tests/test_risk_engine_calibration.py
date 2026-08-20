"""Tests de integración: RiskEngine con calibración de confianza."""

from backend.app.services.risk_engine import RiskEngine


def _calc(**overrides):
    args = {
        "url_features": {"full_url": "https://example.com", "has_https": True},
        "domain_info": {"tld": "com", "domain_age_days": 2000},
    }
    args.update(overrides)
    return RiskEngine.calculate(**args)


class TestCalibratedFields:
    def test_result_keeps_legacy_fields(self):
        result = _calc()
        assert "risk" in result
        assert "score" in result
        assert "reasons" in result

    def test_result_has_calibration_fields(self):
        result = _calc()
        for key in (
            "probability",
            "probability_interval",
            "confidence",
            "score_interval",
            "ml_agreement",
            "num_signals",
        ):
            assert key in result

    def test_confidence_is_no_longer_equal_to_score(self):
        """Antes confidence == score, que mezclaba dos conceptos distintos."""
        result = _calc()
        assert result["confidence"] <= 1.0
        assert result["score"] > 1

    def test_num_signals_matches_reason_count(self):
        result = _calc()
        assert result["num_signals"] == len(result["reasons"])

    def test_probability_is_inverse_of_score(self):
        safe = _calc()
        risky = _calc(
            url_features={"full_url": "http://evil.xyz", "has_https": False, "has_ip": True},
            domain_info={"tld": "xyz", "domain_age_days": 5},
        )
        assert risky["score"] < safe["score"]
        assert risky["probability"] > safe["probability"]


class TestMlAgreementPropagation:
    def test_ml_agreement_flows_from_fusion_result(self):
        result = _calc(ml_result={"phishing_probability": 0.5, "model_agreement": 0.42})
        assert result["ml_agreement"] == 0.42

    def test_missing_ml_result_defaults_to_full_agreement(self):
        result = _calc(ml_result=None)
        assert result["ml_agreement"] == 1.0

    def test_errored_ml_result_defaults_to_full_agreement(self):
        result = _calc(ml_result={"error": "model unavailable"})
        assert result["ml_agreement"] == 1.0

    def test_model_disagreement_lowers_confidence(self):
        agree = _calc(ml_result={"phishing_probability": 0.5, "model_agreement": 1.0})
        disagree = _calc(ml_result={"phishing_probability": 0.5, "model_agreement": 0.2})
        assert disagree["confidence"] < agree["confidence"]


class TestAuthoritativeThreat:
    def test_safe_browsing_threat_forces_full_confidence(self):
        result = _calc(
            sb_result={
                "is_threat": True,
                "verdict": "dangerous",
                "threats": [{"type": "SOCIAL_ENGINEERING"}],
            }
        )
        assert result["risk"] == "HIGH"
        assert result["confidence"] == 1.0

    def test_virustotal_threat_forces_full_confidence(self):
        result = _calc(
            vt_result={"verdict": "malicious", "stats": {"malicious": 7}}
        )
        assert result["risk"] == "HIGH"
        assert result["confidence"] == 1.0

    def test_authoritative_threat_interval_does_not_exceed_score(self):
        result = _calc(
            sb_result={
                "is_threat": True,
                "verdict": "dangerous",
                "threats": [{"type": "MALWARE"}],
            }
        )
        assert result["score_interval"]["upper"] == result["score"]
