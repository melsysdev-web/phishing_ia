import torch

from .model_loader import (
    tokenizer,
    model
)


class RobertaPredictor:

    @staticmethod
    def predict(url: str):

        inputs = tokenizer(
            url,
            return_tensors="pt",
            truncation=True,
            max_length=128
        )

        with torch.no_grad():

            outputs = model(
                **inputs
            )

            probabilities = (
                torch.softmax(
                    outputs.logits,
                    dim=1
                )
            )[0]

        prediction = int(
            torch.argmax(
                probabilities
            )
        )

        return {

            "prediction":
                prediction,

            "legitimate_probability":
                round(
                    float(
                        probabilities[1]
                    ),
                    4
                ),

            "phishing_probability":
                round(
                    float(
                        probabilities[0]
                    ),
                    4
                )
        }