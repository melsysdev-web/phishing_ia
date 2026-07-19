import pytest
from backend.app.utils.url_features import extract_url_features


class TestExtractUrlFeatures:

    def test_returns_all_expected_keys(self):
        feats = extract_url_features("https://example.com/path")
        expected = {
            "url_length", "domain_length", "path_length", "num_dots",
            "num_hyphens", "num_slashes", "num_question_marks", "has_https",
            "has_ip", "contains_at_symbol", "contains_double_slash_redirect",
            "num_subdomains", "full_url",
        }
        assert expected.issubset(feats.keys())

    def test_https_url(self):
        feats = extract_url_features("https://example.com")
        assert feats["has_https"] is True

    def test_http_url_not_https(self):
        feats = extract_url_features("http://example.com")
        assert feats["has_https"] is False

    def test_ip_address_detected(self):
        feats = extract_url_features("http://192.168.1.1/login")
        assert feats["has_ip"] is True

    def test_normal_domain_not_ip(self):
        feats = extract_url_features("https://example.com")
        assert feats["has_ip"] is False

    def test_at_symbol_detected(self):
        feats = extract_url_features("http://legit.com@evil.com/steal")
        assert feats["contains_at_symbol"] is True

    def test_no_at_symbol(self):
        feats = extract_url_features("https://example.com/path")
        assert feats["contains_at_symbol"] is False

    def test_double_slash_in_path(self):
        feats = extract_url_features("https://example.com//redirect")
        assert feats["contains_double_slash_redirect"] is True

    def test_no_double_slash_redirect(self):
        feats = extract_url_features("https://example.com/path")
        assert feats["contains_double_slash_redirect"] is False

    def test_url_length(self):
        url = "https://example.com/page"
        feats = extract_url_features(url)
        assert feats["url_length"] == len(url)

    def test_num_dots_simple_domain(self):
        feats = extract_url_features("https://example.com/path")
        assert feats["num_dots"] == 1

    def test_num_dots_subdomain(self):
        feats = extract_url_features("https://sub.example.co.uk/path")
        assert feats["num_dots"] == 3

    def test_num_hyphens(self):
        feats = extract_url_features("https://my-phishing-site.com/login-page")
        assert feats["num_hyphens"] == 3

    def test_num_hyphens_none(self):
        feats = extract_url_features("https://example.com/path")
        assert feats["num_hyphens"] == 0

    def test_num_question_marks_with_query(self):
        feats = extract_url_features("https://example.com/page?q=1")
        assert feats["num_question_marks"] == 1

    def test_num_question_marks_none(self):
        feats = extract_url_features("https://example.com/path")
        assert feats["num_question_marks"] == 0

    def test_no_subdomain(self):
        feats = extract_url_features("https://example.com/")
        assert feats["num_subdomains"] == 0

    def test_one_subdomain(self):
        feats = extract_url_features("https://www.example.com/")
        assert feats["num_subdomains"] == 1

    def test_multiple_subdomains(self):
        feats = extract_url_features("https://a.b.c.example.com/")
        assert feats["num_subdomains"] >= 3

    def test_full_url_preserved(self):
        url = "https://example.com/path?q=1#section"
        feats = extract_url_features(url)
        assert feats["full_url"] == url

    def test_path_length(self):
        feats = extract_url_features("https://example.com/some/long/path")
        assert feats["path_length"] == len("/some/long/path")
