class FusionEngine:

    RF_WEIGHT = 0.4
    ROBERTA_WEIGHT = 0.6

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

        elif roberta_error:
            phishing_prob = rf_prediction.get(
                "phishing_probability", 0.5
            )
            rf_w, roberta_w = 1.0, 0.0

        else:
            rf_w = FusionEngine.RF_WEIGHT
            roberta_w = FusionEngine.ROBERTA_WEIGHT

            phishing_prob = (
                rf_w * rf_prediction.get(
                    "phishing_probability", 0.5
                )
                + roberta_w * roberta_prediction.get(
                    "phishing_probability", 0.5
                )
            )

        prediction = 1 if phishing_prob >= 0.5 else 0

        return {
            "prediction": prediction,
            "phishing_probability": round(phishing_prob, 4),
            "legitimate_probability": round(
                1.0 - phishing_prob, 4
            ),
            "rf_weight": rf_w,
            "roberta_weight": roberta_w
        }
