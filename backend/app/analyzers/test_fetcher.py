from backend.app.analyzers.html_fetcher import (
    HtmlFetcher
)

result = HtmlFetcher.get_html(
    "https://google.com"
)

print(result["success"])
print(result["status_code"])
print(result["html"][:500])