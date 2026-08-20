"""
Tests para el escalado dinámico de deltas en RiskEngine.

La penalización por dominio nuevo se atenúa cuando VirusTotal y Safe Browsing
coinciden en que la URL está limpia, porque un sitio legítimo recién
registrado comparte esa señal con el phishing.
"""

from backend.app.services.risk_engine import _YOUNG_DOMAIN_DAMPING, RiskEngine

_VT_CLEAN = {"verdict": "clean", "stats": {"malicious": 0}}
_SB_CLEAN = {"is_threat": False}


def _calc(age_days, vt=None, sb=None, **overrides):
    args = {
        "url_features": {"full_url": "https://nueva-empresa.com", "has_https": True},
        "domain_info": {"tld": "com", "domain_age_days": age_days},
        "vt_result": vt,
        "sb_result": sb,
    }
    args.update(overrides)
    return RiskEngine.calculate(**args)


def _has_damped_reason(result):
    return any("atenuado" in r for r in result["reasons"])


class TestYoungDomainDamping:
    def test_clean_external_sources_raise_score_for_new_domain(self):
        undamped = _calc(10)
        damped = _calc(10, vt=_VT_CLEAN, sb=_SB_CLEAN)
        assert damped["score"] > undamped["score"]

    def test_damping_is_reported_in_reasons(self):
        result = _calc(10, vt=_VT_CLEAN, sb=_SB_CLEAN)
        assert _has_damped_reason(result)

    def test_damping_applies_to_under_30_days(self):
        result = _calc(5, vt=_VT_CLEAN, sb=_SB_CLEAN)
        assert _has_damped_reason(result)

    def test_damping_applies_to_under_180_days(self):
        result = _calc(100, vt=_VT_CLEAN, sb=_SB_CLEAN)
        assert _has_damped_reason(result)

    def test_old_domain_is_not_damped(self):
        result = _calc(2000, vt=_VT_CLEAN, sb=_SB_CLEAN)
        assert not _has_damped_reason(result)

    def test_penalty_is_reduced_not_removed(self):
        """Un dominio nuevo sigue puntuando peor que uno antiguo."""
        new_domain = _calc(10, vt=_VT_CLEAN, sb=_SB_CLEAN)
        old_domain = _calc(2000, vt=_VT_CLEAN, sb=_SB_CLEAN)
        assert new_domain["score"] < old_domain["score"]

    def test_damping_factor_is_between_zero_and_one(self):
        assert 0 < _YOUNG_DOMAIN_DAMPING < 1


class TestDampingRequiresBothSources:
    def test_vt_clean_alone_does_not_damp(self):
        result = _calc(10, vt=_VT_CLEAN, sb=None)
        assert not _has_damped_reason(result)

    def test_sb_clean_alone_does_not_damp(self):
        result = _calc(10, vt=None, sb=_SB_CLEAN)
        assert not _has_damped_reason(result)

    def test_errored_vt_does_not_damp(self):
        result = _calc(10, vt={"error": "quota_exceeded"}, sb=_SB_CLEAN)
        assert not _has_damped_reason(result)

    def test_errored_sb_does_not_damp(self):
        result = _calc(10, vt=_VT_CLEAN, sb={"error": "unavailable"})
        assert not _has_damped_reason(result)

    def test_vt_malicious_does_not_damp(self):
        result = _calc(
            10,
            vt={"verdict": "malicious", "stats": {"malicious": 5}},
            sb=_SB_CLEAN,
        )
        assert not _has_damped_reason(result)


class TestDampingNeverRescuesConfirmedThreat:
    def test_safe_browsing_threat_stays_high_risk(self):
        result = _calc(
            10,
            vt=_VT_CLEAN,
            sb={
                "is_threat": True,
                "verdict": "dangerous",
                "threats": [{"type": "SOCIAL_ENGINEERING"}],
            },
        )
        assert result["risk"] == "HIGH"
        assert not _has_damped_reason(result)

    def test_virustotal_threat_stays_high_risk(self):
        result = _calc(
            10,
            vt={"verdict": "malicious", "stats": {"malicious": 9}},
            sb=_SB_CLEAN,
        )
        assert result["risk"] == "HIGH"
