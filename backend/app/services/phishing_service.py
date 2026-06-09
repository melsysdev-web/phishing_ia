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

from backend.app.roberta.predictor import (
    RobertaPredictor
)

from backend.app.ml.fusion.fusion_engine import (
    FusionEngine
)

from backend.app.analyzers.html_analyzer import (
    HtmlAnalyzer
)

from backend.app.services.virustotal_service import (
    VirusTotalService
)

from backend.app.services.safe_browsing_service import (
    SafeBrowsingService
)


class PhishingService:

    @staticmethod
    def analyze(url: str):

        # ==========================
        # URL FEATURES
        # ==========================

        url_features = extract_url_features(
            url
        )

        # ==========================
        # DOMAIN INFO (WHOIS)
        # ==========================

        domain_info = get_domain_info(
            url
        )

        # ==========================
        # HTML ANALYZER
        # ==========================

        html_analysis = HtmlAnalyzer.analyze(
            url
        )

        # ==========================
        # VIRUSTOTAL
        # ==========================

        vt_result = VirusTotalService.analyze(
            url
        )

        # ==========================
        # SAFE BROWSING
        # ==========================

        sb_result = SafeBrowsingService.analyze(
            url
        )

        # ==========================
        # RISK ENGINE
        # ==========================

        risk_result = RiskEngine.calculate(
            url_features,
            domain_info,
            html_analysis,
            vt_result,
            sb_result
        )

        # ==========================
        # RANDOM FOREST
        # ==========================

        rf_features = FeatureMapper.map(
            url,
            url_features,
            html_analysis
        )

        rf_prediction = (
            RandomForestPredictor.predict(
                rf_features
            )
        )

        # ==========================
        # ROBERTA
        # ==========================

        roberta_prediction = (
            RobertaPredictor.predict(url)
        )

        # ==========================
        # FUSION (RF + RoBERTa)
        # ==========================

        fusion_result = FusionEngine.combine(
            rf_prediction,
            roberta_prediction
        )

        # ==========================
        # RESPONSE
        # ==========================

        return {

            "url": url,

            "risk_assessment":
                risk_result,

            "machine_learning": {
                "fusion": fusion_result,
                "random_forest": rf_prediction,
                "roberta": roberta_prediction
            },

            "html_analysis":
                html_analysis,

            "url_features":
                url_features,

            "domain_info":
                domain_info,

            "virustotal":
                vt_result,

            "safe_browsing":
                sb_result
        }