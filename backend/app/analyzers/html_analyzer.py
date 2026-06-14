from bs4 import BeautifulSoup

from backend.app.analyzers.html_fetcher import (
    HtmlFetcher
)

from backend.app.analyzers.html_features import (
    HtmlFeatures
)


def _extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
        tag.decompose()

    # Prefer semantic content containers
    content = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=lambda x: x and "content" in x.lower())
        or soup.find(class_=lambda x: x and "content" in " ".join(x).lower())
    )

    if content:
        paragraphs = content.find_all("p")
        if paragraphs:
            text = " ".join(
                p.get_text(strip=True)
                for p in paragraphs
                if len(p.get_text(strip=True)) > 30
            )
            if len(text) >= 50:
                return " ".join(text.split())[:2000]

    # Fallback: collect all <p> tags with meaningful content
    paragraphs = soup.find_all("p")
    if paragraphs:
        text = " ".join(
            p.get_text(strip=True)
            for p in paragraphs
            if len(p.get_text(strip=True)) > 30
        )
        if len(text) >= 50:
            return " ".join(text.split())[:2000]

    # Last resort: full page text
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())[:2000]


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
            page["html"], url
        )

        page_text = _extract_page_text(
            page["html"]
        )

        return {
            "success": True,
            "html_features": features,
            "page_text": page_text
        }