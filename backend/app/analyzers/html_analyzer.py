from backend.app.analyzers.html_fetcher import (
    HtmlFetcher
)

from backend.app.analyzers.html_features import (
    HtmlFeatures
)


class HtmlAnalyzer:

    @staticmethod
    def analyze(url: str):

        page = HtmlFetcher.get_html(
            url
        )

        if not page["success"]:

            return {
                "success": False,
                "error": page["error"]
            }

        features = HtmlFeatures.extract(
            page["html"]
        )

        return {
            "success": True,
            "html_features": features
        }