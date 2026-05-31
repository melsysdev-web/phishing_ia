from backend.app.utils.url_features import (
    extract_url_features
)


class PhishingService:

    @staticmethod
    def analyze(url: str):

        features = extract_url_features(url)

        return {
            "url": url,
            "features": features
        }