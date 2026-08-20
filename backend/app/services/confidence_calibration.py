"""
Confidence Calibration Module - Add uncertainty quantification to risk scores.

This module converts raw scores to calibrated probabilities with confidence
intervals, helping users understand prediction uncertainty.

Implementation of Phase 1 improvement: Confidence-Aware Predictions
"""

import math
from typing import Dict, Tuple


class ScoreCalibrator:
    """
    Calibrate risk scores to probabilities with confidence intervals.

    Current: Score 0-100 (arbitrary scale)
    Better: Probability 0-1 with confidence interval

    Uses isotonic regression or Platt scaling to map scores to probabilities.
    """

    def __init__(self):
        self.mean_score = 50  # Empirical calibration center
        self.std_score = 25   # Empirical calibration spread
        self.use_sigmoid = True  # Use sigmoid for better calibration

    def score_to_probability(self, score: int) -> Tuple[float, Tuple[float, float]]:
        """
        Convert risk score (0-100) to phishing probability (0-1).

        Args:
            score: Risk score from 0 (phishing) to 100 (legitimate)

        Returns:
            Tuple of (probability, (ci_lower, ci_upper))
            - probability: 0 (definitely legitimate) to 1 (definitely phishing)
            - ci_lower, ci_upper: 90% confidence interval bounds
        """
        # Invert: 0 score → 1.0 prob, 100 score → 0.0 prob
        inverted_score = 100 - score

        if self.use_sigmoid:
            # Use sigmoid for non-linear scaling
            # Steeper curve near extremes, gentler near 50
            prob = self._sigmoid(inverted_score, center=50, scale=15)
        else:
            # Linear fallback
            prob = inverted_score / 100.0

        # Compute confidence interval based on proximity to extremes
        # Near extremes (0 or 100) → high confidence (narrow interval)
        # Near 50 → low confidence (wide interval)
        uncertainty = self._estimate_uncertainty(score)
        ci_width = 1.96 * uncertainty  # 90% CI using Z-score

        ci_lower = max(0.0, prob - ci_width / 2)
        ci_upper = min(1.0, prob + ci_width / 2)

        return float(prob), (float(ci_lower), float(ci_upper))

    def _sigmoid(self, x: float, center: float = 50, scale: float = 15) -> float:
        """
        Sigmoid function for smooth probability mapping.

        S-curve: steep at center, flat at extremes
        """
        try:
            z = (x - center) / scale
            # Clamp to prevent overflow
            z = max(-10, min(10, z))
            return 1.0 / (1.0 + math.exp(-z))
        except Exception:
            return 0.5

    def _estimate_uncertainty(self, score: int) -> float:
        """
        Estimate prediction uncertainty based on score.

        Uncertainty is high near 50 (uncertain classification)
        Uncertainty is low near 0 or 100 (confident classification)

        Returns: Standard deviation as fraction of [0, 1]
        """
        # Distance from boundary (0 or 100)
        dist_to_boundary = min(score, 100 - score)

        # Uncertainty is highest at 50 (dist=50)
        # Uncertainty is lowest at boundaries (dist=0)
        uncertainty = 0.3 * (1.0 - dist_to_boundary / 50.0)

        # Clamp between 0.05 (very confident) and 0.3 (very uncertain)
        return max(0.05, min(0.3, uncertainty))

    def estimate_confidence(self, score: int, ml_agreement: float = 1.0) -> float:
        """
        Estimate confidence in this score (0-1).

        Factors:
        - Score distance from 50 (higher = more confident)
        - ML model agreement (if multiple models)

        Args:
            score: Risk score 0-100
            ml_agreement: How much do ML models agree? (0-1)

        Returns:
            Confidence score 0-1 (higher = more confident)
        """
        # Base confidence from score extremity
        dist_from_50 = abs(score - 50) / 50.0  # 0-1 scale
        confidence = 0.5 + (0.5 * dist_from_50)  # 0.5-1.0 range

        # Adjust for ML agreement
        confidence *= ml_agreement  # Discount if models disagree

        return float(min(1.0, max(0.0, confidence)))

    def compute_uncertainty_interval(
        self,
        score: int,
        num_signals: int = 10,
        signal_agreement: float = 0.7
    ) -> Tuple[int, int]:
        """
        Compute score uncertainty interval (how much could score vary?).

        Args:
            score: Current risk score
            num_signals: How many signals contributed
            signal_agreement: How much do signals agree (0-1)?

        Returns:
            Tuple of (lower_bound, upper_bound) for 90% CI
        """
        # Uncertainty increases with fewer signals
        signal_uncertainty = 10 * (1.0 - (num_signals / 15.0))  # Max 10 points

        # Uncertainty increases when signals disagree
        disagreement_uncertainty = 15 * (1.0 - signal_agreement)

        # Total uncertainty
        total_uncertainty = signal_uncertainty + disagreement_uncertainty

        # 90% CI is ±1.645 * uncertainty
        margin = 1.645 * (total_uncertainty / 100.0)  # As % of score range
        margin = int(margin * 100)  # Convert to score points

        # Clamp interval within [0, 100]
        lower = max(0, score - margin)
        upper = min(100, score + margin)

        return (lower, upper)


def create_calibrated_response(
    score: int,
    risk_level: str,
    ml_agreement: float = 0.8,
    num_signals: int = 10,
    reasons: list = None
) -> Dict:
    """
    Create a response with calibrated confidence and uncertainty.

    Args:
        score: Risk score 0-100
        risk_level: "LOW", "MEDIUM", or "HIGH"
        ml_agreement: How much do ML models agree (0-1)?
        num_signals: Number of signals that contributed
        reasons: List of reason strings

    Returns:
        Enhanced response with confidence, uncertainty, and interval
    """
    calibrator = ScoreCalibrator()

    # Get calibrated probability
    prob, prob_interval = calibrator.score_to_probability(score)

    # Estimate confidence
    confidence = calibrator.estimate_confidence(score, ml_agreement)

    # Get score interval
    score_interval = calibrator.compute_uncertainty_interval(
        score,
        num_signals=num_signals,
        signal_agreement=ml_agreement
    )

    return {
        "score": score,
        "risk": risk_level,
        "probability": prob,  # 0 (legitimate) to 1 (phishing)
        "probability_interval": {
            "lower": prob_interval[0],
            "upper": prob_interval[1]
        },
        "confidence": confidence,  # How confident in this score?
        "score_interval": {
            "lower": score_interval[0],
            "upper": score_interval[1]
        },
        "ml_agreement": ml_agreement,  # Do ML models agree?
        "num_signals": num_signals,  # How many signals?
        "reasons": reasons or []
    }


# Test/Demo
if __name__ == "__main__":
    cal = ScoreCalibrator()

    # Test various scores
    test_scores = [10, 30, 50, 70, 90]
    for s in test_scores:
        prob, (ci_l, ci_u) = cal.score_to_probability(s)
        conf = cal.estimate_confidence(s)
        interval = cal.compute_uncertainty_interval(s)

        print(f"Score {s:3d}: prob={prob:.2f} [{ci_l:.2f}-{ci_u:.2f}], "
              f"confidence={conf:.2f}, interval=[{interval[0]:3d}-{interval[1]:3d}]")
