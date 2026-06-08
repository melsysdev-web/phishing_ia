from backend.app.utils.url_features import (
    extract_url_features
)

from backend.app.utils.domain_utils import (
    get_domain_info
)

from backend.app.services.risk_engine import (
    RiskEngine
)

from backend.app.utils.feature_mapper import (
    FeatureMapper
)

from backend.app.random_forest.predictor import (
    RandomForestPredictor
)


class PhishingService:

    @staticmethod
    def analyze(url: str):

        # Extraer características URL
        url_features = extract_url_features(
            url
        )

        # Información WHOIS
        domain_info = get_domain_info(
            url
        )

        # Motor de riesgo actual
        risk_result = RiskEngine.calculate(
            url_features,
            domain_info
        )

        # Convertir al formato esperado por Random Forest
        rf_features = FeatureMapper.map(
            url,
            url_features
        )

        # Predicción ML
        ml_prediction = (
            RandomForestPredictor.predict(
                rf_features
            )
        )

        return {
            "url": url,

            "risk_assessment":
                risk_result,

            "machine_learning":
                ml_prediction,

            "url_features":
                url_features,

            "domain_info":
                domain_info
        }