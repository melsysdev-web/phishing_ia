"""Tests para confidence_calibration.py — calibración de score a probabilidad."""

from backend.app.services.confidence_calibration import (
    ScoreCalibrator,
    create_calibrated_response,
)


class TestScoreToProbability:
    def test_low_score_maps_to_high_phishing_probability(self):
        cal = ScoreCalibrator()
        prob, _ = cal.score_to_probability(10)
        assert prob > 0.9

    def test_high_score_maps_to_low_phishing_probability(self):
        cal = ScoreCalibrator()
        prob, _ = cal.score_to_probability(90)
        assert prob < 0.1

    def test_midpoint_score_maps_to_even_probability(self):
        cal = ScoreCalibrator()
        prob, _ = cal.score_to_probability(50)
        assert abs(prob - 0.5) < 0.01

    def test_probability_is_monotonically_decreasing(self):
        cal = ScoreCalibrator()
        probs = [cal.score_to_probability(s)[0] for s in range(0, 101, 10)]
        assert probs == sorted(probs, reverse=True)

    def test_probability_always_within_unit_range(self):
        cal = ScoreCalibrator()
        for score in range(0, 101):
            prob, (lo, hi) = cal.score_to_probability(score)
            assert 0.0 <= prob <= 1.0
            assert 0.0 <= lo <= hi <= 1.0

    def test_interval_contains_probability(self):
        cal = ScoreCalibrator()
        for score in (0, 25, 50, 75, 100):
            prob, (lo, hi) = cal.score_to_probability(score)
            assert lo <= prob <= hi


class TestConfidenceEstimation:
    def test_extreme_scores_are_more_confident_than_midpoint(self):
        cal = ScoreCalibrator()
        assert cal.estimate_confidence(0) > cal.estimate_confidence(50)
        assert cal.estimate_confidence(100) > cal.estimate_confidence(50)

    def test_model_disagreement_lowers_confidence(self):
        cal = ScoreCalibrator()
        agree = cal.estimate_confidence(20, ml_agreement=1.0)
        disagree = cal.estimate_confidence(20, ml_agreement=0.4)
        assert disagree < agree

    def test_confidence_within_unit_range(self):
        cal = ScoreCalibrator()
        for score in range(0, 101, 5):
            for agreement in (0.0, 0.5, 1.0):
                conf = cal.estimate_confidence(score, agreement)
                assert 0.0 <= conf <= 1.0


class TestUncertaintyInterval:
    def test_fewer_signals_widens_interval(self):
        cal = ScoreCalibrator()
        wide = cal.compute_uncertainty_interval(50, num_signals=2, signal_agreement=0.7)
        narrow = cal.compute_uncertainty_interval(50, num_signals=15, signal_agreement=0.7)
        assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])

    def test_signal_disagreement_widens_interval(self):
        cal = ScoreCalibrator()
        wide = cal.compute_uncertainty_interval(50, num_signals=10, signal_agreement=0.1)
        narrow = cal.compute_uncertainty_interval(50, num_signals=10, signal_agreement=1.0)
        assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])

    def test_interval_clamped_to_score_range(self):
        cal = ScoreCalibrator()
        lo, hi = cal.compute_uncertainty_interval(0, num_signals=1, signal_agreement=0.0)
        assert lo >= 0
        lo, hi = cal.compute_uncertainty_interval(100, num_signals=1, signal_agreement=0.0)
        assert hi <= 100

    def test_interval_contains_score(self):
        cal = ScoreCalibrator()
        for score in (0, 30, 50, 70, 100):
            lo, hi = cal.compute_uncertainty_interval(score)
            assert lo <= score <= hi


class TestCalibratedResponse:
    def test_response_preserves_score_and_risk(self):
        result = create_calibrated_response(score=75, risk_level="MEDIUM")
        assert result["score"] == 75
        assert result["risk"] == "MEDIUM"

    def test_response_has_all_calibration_fields(self):
        result = create_calibrated_response(score=40, risk_level="HIGH")
        for key in (
            "probability",
            "probability_interval",
            "confidence",
            "score_interval",
            "ml_agreement",
            "num_signals",
        ):
            assert key in result

    def test_reasons_are_passed_through(self):
        reasons = ["No utiliza HTTPS", "Dominio creado hace menos de 30 días"]
        result = create_calibrated_response(score=20, risk_level="HIGH", reasons=reasons)
        assert result["reasons"] == reasons

    def test_reasons_default_to_empty_list(self):
        result = create_calibrated_response(score=50, risk_level="MEDIUM")
        assert result["reasons"] == []
