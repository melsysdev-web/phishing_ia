from backend.app.utils.feature_mapper import FeatureMapper

EXPECTED_KEYS = [
    # URL structural
    'URLLength', 'DomainLength', 'IsDomainIP', 'TLDLength', 'NoOfSubDomain', 'IsHTTPS',
    # URL character analysis
    'NoOfLettersInURL', 'LetterRatioInURL', 'NoOfDegitsInURL', 'DegitRatioInURL',
    'NoOfEqualsInURL', 'NoOfAmpersandInURL', 'NoOfOtherSpecialCharsInURL',
    'SpacialCharRatioInURL',
    # URL obfuscation
    'HasObfuscation', 'NoOfObfuscatedChar', 'ObfuscationRatio',
    # HTML structure
    'HasTitle', 'HasFavicon', 'HasDescription', 'HasPasswordField', 'HasHiddenFields',
    'NoOfImage', 'NoOfCSS', 'NoOfJS',
    # HTML behavior
    'NoOfiFrame', 'HasExternalFormSubmit', 'HasSocialNet', 'HasSubmitButton',
    'HasCopyrightInfo', 'IsResponsive',
    # HTML links
    'NoOfSelfRef', 'NoOfEmptyRef', 'NoOfExternalRef',
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
    assert result["IsDomainIP"] == 0
    assert isinstance(result["IsHTTPS"], int)
    assert isinstance(result["HasObfuscation"], int)


def test_phishing_booleans_converted(url_features_phishing):
    result = FeatureMapper.map(
        "http://192.168.1.1/login",
        url_features_phishing,
        {"html_features": {}}
    )
    assert result["IsHTTPS"] == 0
    assert result["IsDomainIP"] == 1


def test_url_numeric_features_mapped(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["URLLength"] == url_features_safe["url_length"]
    assert result["DomainLength"] == url_features_safe["domain_length"]


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
            "NoOfJS": 12,
            "NoOfiFrame": 2,
            "HasSocialNet": 1,
            "IsResponsive": 1,
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
    assert result["NoOfiFrame"] == 2
    assert result["HasSocialNet"] == 1
    assert result["IsResponsive"] == 1


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
    assert result["NoOfiFrame"] == 0
    assert result["NoOfSelfRef"] == 0
    assert result["NoOfExternalRef"] == 0


def test_tld_length_extracted_from_url(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["TLDLength"] == 3  # "com"


def test_subdomains_counted(url_features_safe):
    result = FeatureMapper.map(
        "https://www.google.com",
        url_features_safe,
        {"html_features": {}}
    )
    assert result["NoOfSubDomain"] == 1  # "www"
