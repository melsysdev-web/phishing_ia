from backend.app.utils.feature_mapper import FeatureMapper

EXPECTED_KEYS = [
    'URLLength', 'DomainLength', 'PathLength', 'NumDots', 'NumHyphens',
    'NumQuestionMarks', 'ContainsAtSymbol', 'ContainsDoubleSlashRedirect',
    'IsDomainIP', 'TLDLength', 'NoOfSubDomain', 'IsHTTPS',
    'HasTitle', 'HasFavicon', 'HasDescription',
    'HasPasswordField', 'HasHiddenFields', 'NoOfImage', 'NoOfCSS', 'NoOfJS'
]


def test_output_has_all_required_keys(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    for key in EXPECTED_KEYS:
        assert key in result, f"Missing key: {key}"


def test_booleans_converted_to_int(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["IsHTTPS"] == 1
    assert result["ContainsAtSymbol"] == 0
    assert result["IsDomainIP"] == 0
    assert result["ContainsDoubleSlashRedirect"] == 0
    assert isinstance(result["IsHTTPS"], int)


def test_phishing_booleans_converted(url_features_phishing):
    result = FeatureMapper.map(
        "http://192.168.1.1/login",
        url_features_phishing,
        {"html_features": {}}
    )
    assert result["IsHTTPS"] == 0
    assert result["ContainsAtSymbol"] == 1
    assert result["IsDomainIP"] == 1


def test_url_numeric_features_mapped(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["URLLength"] == url_features_safe["url_length"]
    assert result["DomainLength"] == url_features_safe["domain_length"]
    assert result["PathLength"] == url_features_safe["path_length"]
    assert result["NumDots"] == url_features_safe["num_dots"]
    assert result["NumHyphens"] == url_features_safe["num_hyphens"]
    assert result["NumQuestionMarks"] == url_features_safe["num_question_marks"]


def test_html_features_passed_through(url_features_safe):
    html_analysis = {
        "html_features": {
            "HasPasswordField": 1,
            "HasHiddenFields": 1,
            "HasTitle": 1,
            "HasFavicon": 0,
            "HasDescription": 1,
            "NoOfImage": 8,
            "NoOfCSS": 3,
            "NoOfJS": 12
        }
    }
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        html_analysis
    )
    assert result["HasPasswordField"] == 1
    assert result["HasHiddenFields"] == 1
    assert result["HasTitle"] == 1
    assert result["HasFavicon"] == 0
    assert result["NoOfImage"] == 8
    assert result["NoOfCSS"] == 3
    assert result["NoOfJS"] == 12


def test_missing_html_features_default_to_zero(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["HasPasswordField"] == 0
    assert result["HasTitle"] == 0
    assert result["NoOfImage"] == 0
    assert result["NoOfJS"] == 0


def test_tld_length_extracted_from_url(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["TLDLength"] == 3  # "com" has length 3


def test_subdomains_counted(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["NoOfSubDomain"] == 1  # "www"
