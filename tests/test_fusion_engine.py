import pytest
from backend.app.ml.fusion.fusion_engine import FusionEngine


# ── Normal combination ────────────────────────────────────────────────

def test_weighted_average_applied():
    rf = {"phishing_probability": 0.8}
    roberta = {"phishing_probability": 0.6}
    result = FusionEngine.combine(rf, roberta)
    expected = FusionEngine.RF_WEIGHT * 0.8 + FusionEngine.ROBERTA_WEIGHT * 0.6
    assert abs(result["phishing_probability"] - expected) < 0.001


def test_weights_sum_to_one_on_success():
    result = FusionEngine.combine(
        {"phishing_probability": 0.5},
        {"phishing_probability": 0.5}
    )
    assert abs(result["rf_weight"] + result["roberta_weight"] - 1.0) < 0.001


def test_probabilities_sum_to_one():
    result = FusionEngine.combine(
        {"phishing_probability": 0.7},
        {"phishing_probability": 0.4}
    )
    total = result["phishing_probability"] + result["legitimate_probability"]
    assert abs(total - 1.0) < 0.001


def test_result_has_required_keys():
    result = FusionEngine.combine(
        {"phishing_probability": 0.5},
        {"phishing_probability": 0.5}
    )
    for key in [
        "prediction", "phishing_probability",
        "legitimate_probability", "rf_weight", "roberta_weight"
    ]:
        assert key in result


# ── Prediction threshold ──────────────────────────────────────────────

def test_phishing_prediction_when_above_threshold():
    result = FusionEngine.combine(
        {"phishing_probability": 0.9},
        {"phishing_probability": 0.8}
    )
    assert result["prediction"] == 1
    assert result["phishing_probability"] >= 0.5


def test_legitimate_prediction_when_below_threshold():
    result = FusionEngine.combine(
        {"phishing_probability": 0.1},
        {"phishing_probability": 0.2}
    )
    assert result["prediction"] == 0
    assert result["phishing_probability"] < 0.5


def test_exactly_half_is_phishing():
    result = FusionEngine.combine(
        {"phishing_probability": 0.5},
        {"phishing_probability": 0.5}
    )
    assert result["prediction"] == 1


# ── Fallback on model failure ─────────────────────────────────────────

def test_rf_failure_falls_back_to_roberta():
    result = FusionEngine.combine(
        {"error": "Model not loaded"},
        {"phishing_probability": 0.75}
    )
    assert result["rf_weight"] == 0.0
    assert result["roberta_weight"] == 1.0
    assert result["phishing_probability"] == 0.75


def test_roberta_failure_falls_back_to_rf():
    result = FusionEngine.combine(
        {"phishing_probability": 0.9},
        {"error": "CUDA out of memory"}
    )
    assert result["rf_weight"] == 1.0
    assert result["roberta_weight"] == 0.0
    assert result["phishing_probability"] == 0.9


def test_rf_failure_prediction_from_roberta():
    result = FusionEngine.combine(
        {"error": "not found"},
        {"phishing_probability": 0.8}
    )
    assert result["prediction"] == 1


def test_roberta_failure_prediction_from_rf():
    result = FusionEngine.combine(
        {"phishing_probability": 0.1},
        {"error": "timeout"}
    )
    assert result["prediction"] == 0


# ── Both models fail ──────────────────────────────────────────────────

def test_both_models_fail_returns_error():
    result = FusionEngine.combine(
        {"error": "Model file not found"},
        {"error": "Tokenizer not loaded"}
    )
    assert "error" in result


def test_both_models_fail_includes_individual_errors():
    result = FusionEngine.combine(
        {"error": "RF error"},
        {"error": "RoBERTa error"}
    )
    assert result["rf_error"] == "RF error"
    assert result["roberta_error"] == "RoBERTa error"


# ── Default weights ───────────────────────────────────────────────────

def test_default_rf_weight():
    assert FusionEngine.RF_WEIGHT == 0.4


def test_default_roberta_weight():
    assert FusionEngine.ROBERTA_WEIGHT == 0.6
