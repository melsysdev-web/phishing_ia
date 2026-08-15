import numpy as np
import pandas as pd

from .model_loader import get_model


class RandomForestPredictor:

    @staticmethod
    def predict(features: dict):

        try:
            model, feature_columns = get_model()

            row = {}

            for column in feature_columns:

                row[column] = features.get(
                    column,
                    0
                )

            df = pd.DataFrame(
                [row]
            )

            # Un solo predict_proba en vez de predict()+predict_proba() por
            # separado — predict() internamente vuelve a correr todo el
            # bosque y hace argmax, así que llamarlo aparte evaluaba el
            # modelo dos veces por request para nada.
            probabilities = (
                model.predict_proba(
                    df
                )[0]
            )

            prediction = int(np.argmax(probabilities))

            return {
                "prediction": prediction,
                # model.classes_ is always sorted ascending ([0, 1]), and the
                # training labels use 0 = phishing, 1 = legitimate (see
                # datasets/raw/phishing_urls.csv), so predict_proba columns
                # are [phishing, legitimate] in that order.
                "phishing_probability":
                    round(
                        float(
                            probabilities[0]
                        ),
                        4
                    ),
                "legitimate_probability":
                    round(
                        float(
                            probabilities[1]
                        ),
                        4
                    )
            }

        except Exception as e:

            return {
                "error": str(e)
            }