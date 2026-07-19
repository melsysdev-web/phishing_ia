import pytest
from backend.app.utils.feature_mapper import FeatureMapper


_BASE_URL_FEATURES = {
    "url_length": 28,
    "domain_length": 11,
    "path_length": 5,
    "num_dots": 1,
    "num_hyphens": 0,
    "num_question_marks": 0,
    "contains_at_symbol": False,
    "contains_double_slash_redirect": False,
    "has_ip": False,
    "has_https": True,
}

_HTML_ANALYSIS_OK = {
    "success": True,
    "html_features": {
        "HasTitle": 1,
        "HasFavicon": 1,
        "HasDescription": 1,
        "HasPasswordField": 0,
        "HasHiddenFields": 0,
        "NoOfImage": 3,
        "NoOfCSS": 2,
        "NoOfJS": 4,
    },
}


class TestFeatureMapper:

    def test_returns_all_rf_columns(self):
        result = FeatureMapper.map(
            "https://example.com/path",
            _BASE_URL_FEATURES,
            _HTML_ANALYSIS_OK,
        )
        expected_keys = {
            "URLLength", "DomainLength", "PathLength", "NumDots",
            "NumHyphens", "NumQuestionMarks", "ContainsAtSymbol",
            "ContainsDoubleSlashRedirect", "IsDomainIP", "TLDLength",
            "NoOfSubDomain", "IsHTTPS",
            "HasTitle", "HasFavicon", "HasDescription",
            "HasPasswordField", "HasHiddenFields",
            "NoOfImage", "NoOfCSS", "NoOfJS",
        }
        assert expected_keys.issubset(result.keys())

    def test_url_numeric_features_mapped(self):
        result = FeatureMapper.map(
            "https://example.com/path",
            _BASE_URL_FEATURES,
            _HTML_ANALYSIS_OK,
        )
        assert result["URLLength"] == 28
        assert result["DomainLength"] == 11
        assert result["PathLength"] == 5
        assert result["NumDots"] == 1
        assert result["NumHyphens"] == 0

    def test_https_mapped_as_int(self):
        result = FeatureMapper.map(
            "https://example.com/path",
            _BASE_URL_FEATURES,
            _HTML_ANALYSIS_OK,
        )
        assert result["IsHTTPS"] == 1

    def test_http_mapped_as_zero(self):
        feats = {**_BASE_URL_FEATURES, "has_https": False}
        result = FeatureMapper.map("http://example.com/path", feats, {})
        assert result["IsHTTPS"] == 0

    def test_ip_domain_mapped_as_int(self):
        feats = {**_BASE_URL_FEATURES, "has_ip": True}
        result = FeatureMapper.map("http://192.168.1.1/login", feats, {})
        assert result["IsDomainIP"] == 1

    def test_no_ip_mapped_as_zero(self):
        result = FeatureMapper.map(
            "https://example.com", _BASE_URL_FEATURES, {}
        )
        assert result["IsDomainIP"] == 0

    def test_at_symbol_mapped_as_int(self):
        feats = {**_BASE_URL_FEATURES, "contains_at_symbol": True}
        result = FeatureMapper.map("http://x.com@evil.com", feats, {})
        assert result["ContainsAtSymbol"] == 1

    def test_html_features_mapped(self):
        result = FeatureMapper.map(
            "https://example.com/path",
            _BASE_URL_FEATURES,
            _HTML_ANALYSIS_OK,
        )
        assert result["HasTitle"] == 1
        assert result["HasFavicon"] == 1
        assert result["HasDescription"] == 1
        assert result["HasPasswordField"] == 0
        assert result["NoOfImage"] == 3
        assert result["NoOfCSS"] == 2
        assert result["NoOfJS"] == 4

    def test_missing_html_analysis_defaults_zeros(self):
        result = FeatureMapper.map(
            "https://example.com", _BASE_URL_FEATURES, {}
        )
        assert result["HasTitle"] == 0
        assert result["HasFavicon"] == 0
        assert result["HasPasswordField"] == 0
        assert result["NoOfImage"] == 0
        assert result["NoOfCSS"] == 0
        assert result["NoOfJS"] == 0

    def test_failed_html_analysis_defaults_zeros(self):
        result = FeatureMapper.map(
            "https://example.com",
            _BASE_URL_FEATURES,
            {"success": False, "error": "timeout"},
        )
        assert result["HasPasswordField"] == 0
        assert result["HasHiddenFields"] == 0

    def test_tld_length_com(self):
        result = FeatureMapper.map(
            "https://example.com/path", _BASE_URL_FEATURES, {}
        )
        assert result["TLDLength"] == 3  # "com"

    def test_tld_length_org(self):
        result = FeatureMapper.map(
            "https://example.org/path", _BASE_URL_FEATURES, {}
        )
        assert result["TLDLength"] == 3  # "org"

    def test_subdomain_count_no_subdomain(self):
        result = FeatureMapper.map(
            "https://example.com/", _BASE_URL_FEATURES, {}
        )
        assert result["NoOfSubDomain"] == 0

    def test_subdomain_count_one_subdomain(self):
        result = FeatureMapper.map(
            "https://mail.example.com/", _BASE_URL_FEATURES, {}
        )
        assert result["NoOfSubDomain"] == 1
