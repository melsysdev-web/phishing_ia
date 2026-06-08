from backend.app.analyzers.html_analyzer import (
    HtmlAnalyzer
)

result = HtmlAnalyzer.analyze(
    "https://google.com"
)

print(result)