"""Tests para model_agreement en FusionEngine."""

from backend.app.ml.fusion.fusion_engine import FusionEngine


def _pred(prob):
    return {"phishing_probability": prob}


class TestModelAgreement:
    def test_identical_predictions_give_full_agreement(self):
        result = FusionEngine.combine(_pred(0.8), _pred(0.8))
        assert result["model_agreement"] == 1.0

    def test_opposite_predictions_give_zero_agreement(self):
        result = FusionEngine.combine(_pred(0.0), _pred(1.0))
        assert result["model_agreement"] == 0.0

    def test_partial_disagreement_gives_partial_agreement(self):
        result = FusionEngine.combine(_pred(0.3), _pred(0.5))
        assert abs(result["model_agreement"] - 0.8) < 0.001

    def test_agreement_is_symmetric(self):
        a = FusionEngine.combine(_pred(0.2), _pred(0.7))["model_agreement"]
        b = FusionEngine.combine(_pred(0.7), _pred(0.2))["model_agreement"]
        assert a == b

    def test_rf_failure_uses_single_model_agreement(self):
        result = FusionEngine.combine({"error": "boom"}, _pred(0.9))
        assert result["model_agreement"] == FusionEngine.SINGLE_MODEL_AGREEMENT

    def test_roberta_failure_uses_single_model_agreement(self):
        result = FusionEngine.combine(_pred(0.9), {"error": "boom"})
        assert result["model_agreement"] == FusionEngine.SINGLE_MODEL_AGREEMENT

    def test_both_models_failing_returns_error_without_agreement(self):
        result = FusionEngine.combine({"error": "a"}, {"error": "b"})
        assert "error" in result
        assert "model_agreement" not in result

    def test_agreement_within_unit_range(self):
        for rf in (0.0, 0.25, 0.5, 0.75, 1.0):
            for rob in (0.0, 0.25, 0.5, 0.75, 1.0):
                agreement = FusionEngine.combine(_pred(rf), _pred(rob))["model_agreement"]
                assert 0.0 <= agreement <= 1.0

    def test_fusion_still_returns_existing_fields(self):
        result = FusionEngine.combine(_pred(0.6), _pred(0.6))
        assert result["phishing_probability"] == 0.6
        assert result["legitimate_probability"] == 0.4
        assert result["prediction"] == 0
