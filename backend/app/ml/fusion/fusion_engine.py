class FusionEngine:

    RF_WEIGHT = 0.4
    ROBERTA_WEIGHT = 0.6
    SINGLE_MODEL_AGREEMENT = 0.6

    @staticmethod
    def combine(
        rf_prediction: dict,
        roberta_prediction: dict
    ) -> dict:

        rf_error = "error" in rf_prediction
        roberta_error = "error" in roberta_prediction

        if rf_error and roberta_error:
            return {
                "error": "Both models failed",
                "rf_error": rf_prediction.get("error"),
                "roberta_error": roberta_prediction.get("error")
            }

        if rf_error:
            phishing_prob = roberta_prediction.get(
                "phishing_probability", 0.5
            )
            rf_w, roberta_w = 0.0, 1.0
            # Un solo modelo: no hay segunda opinión que corrobore.
            agreement = FusionEngine.SINGLE_MODEL_AGREEMENT

        elif roberta_error:
            phishing_prob = rf_prediction.get(
                "phishing_probability", 0.5
            )
            rf_w, roberta_w = 1.0, 0.0
            agreement = FusionEngine.SINGLE_MODEL_AGREEMENT

        else:
            rf_w = FusionEngine.RF_WEIGHT
            roberta_w = FusionEngine.ROBERTA_WEIGHT

            rf_prob = rf_prediction.get("phishing_probability", 0.5)
            roberta_prob = roberta_prediction.get("phishing_probability", 0.5)

            phishing_prob = rf_w * rf_prob + roberta_w * roberta_prob
            agreement = 1.0 - abs(rf_prob - roberta_prob)

        phishing_prob = max(0.0, min(1.0, phishing_prob))
        # Convención del proyecto: 0 = phishing, 1 = legítimo (ver
        # random_forest/predictor.py).
        prediction = 0 if phishing_prob >= 0.5 else 1

        return {
            "prediction": prediction,
            "phishing_probability": round(phishing_prob, 4),
            "legitimate_probability": round(
                1.0 - phishing_prob, 4
            ),
            "rf_weight": rf_w,
            "roberta_weight": roberta_w,
            "model_agreement": round(max(0.0, min(1.0, agreement)), 4)
        }
