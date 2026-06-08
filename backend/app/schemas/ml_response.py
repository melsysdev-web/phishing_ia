from pydantic import BaseModel


class MLPredictionResponse(
    BaseModel
):
    prediction: int

    legitimate_probability: float

    phishing_probability: float