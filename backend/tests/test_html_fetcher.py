from unittest.mock import MagicMock, patch

from backend.app.analyzers.html_fetcher import HtmlFetcher, _is_safe_host


class TestIsSafeHost:

    def test_loopback_blocked(self):
        assert _is_safe_host("127.0.0.1") is False

    def test_localhost_blocked(self):
        assert _is_safe_host("localhost") is False

    def test_private_rfc1918_blocked(self):
        assert _is_safe_host("10.0.0.5") is False
        assert _is_safe_host("192.168.1.1") is False
        assert _is_safe_host("172.16.0.1") is False

    def test_cloud_metadata_ip_blocked(self):
        assert _is_safe_host("169.254.169.254") is False

    def test_public_ip_allowed(self):
        assert _is_safe_host("1.1.1.1") is True

    def test_unresolvable_host_blocked(self):
        assert _is_safe_host("this-domain-does-not-exist-abc123.invalid") is False


class TestGetHtmlBlocksSSRF:

    def test_blocks_loopback_url(self):
        result = HtmlFetcher.get_html("http://127.0.0.1/admin")
        assert result["success"] is False
        assert result["html"] == ""

    def test_blocks_private_network_url(self):
        result = HtmlFetcher.get_html("http://192.168.1.1/")
        assert result["success"] is False

    def test_blocks_disallowed_scheme(self):
        result = HtmlFetcher.get_html("file:///etc/passwd")
        assert result["success"] is False
        assert "esquema" in result["error"].lower()

    @patch("backend.app.analyzers.html_fetcher._is_safe_host", return_value=True)
    @patch("backend.app.analyzers.html_fetcher._SESSION.get")
    def test_follows_safe_redirect(self, mock_get, _mock_safe):
        redirect_resp = MagicMock()
        redirect_resp.is_redirect = True
        redirect_resp.is_permanent_redirect = False
        redirect_resp.headers = {"Location": "https://example.com/final"}

        final_resp = MagicMock()
        final_resp.is_redirect = False
        final_resp.is_permanent_redirect = False
        final_resp.status_code = 200
        final_resp.encoding = "utf-8"
        final_resp.iter_content.return_value = [b"<html>ok</html>"]

        mock_get.side_effect = [redirect_resp, final_resp]

        result = HtmlFetcher.get_html("https://example.com/start")
        assert result["success"] is True
        assert result["html"] == "<html>ok</html>"

    @patch("backend.app.analyzers.html_fetcher._is_safe_host", return_value=True)
    @patch("backend.app.analyzers.html_fetcher._SESSION.get")
    def test_blocks_redirect_to_unsafe_host(self, mock_get, mock_safe):
        redirect_resp = MagicMock()
        redirect_resp.is_redirect = True
        redirect_resp.is_permanent_redirect = False
        redirect_resp.headers = {"Location": "http://169.254.169.254/latest/meta-data/"}
        mock_get.return_value = redirect_resp

        mock_safe.side_effect = [True, False]

        result = HtmlFetcher.get_html("https://example.com/start")
        assert result["success"] is False

    @patch("backend.app.analyzers.html_fetcher._is_safe_host", return_value=True)
    @patch("backend.app.analyzers.html_fetcher._SESSION.get")
    def test_rejects_response_over_size_limit(self, mock_get, _mock_safe):
        resp = MagicMock()
        resp.is_redirect = False
        resp.is_permanent_redirect = False
        resp.status_code = 200
        resp.encoding = "utf-8"
        big_chunk = b"a" * (2 * 1024 * 1024 + 1)
        resp.iter_content.return_value = [big_chunk]
        mock_get.return_value = resp

        result = HtmlFetcher.get_html("https://example.com/huge")
        assert result["success"] is False
        assert "grande" in result["error"].lower()
