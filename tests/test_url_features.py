from backend.app.utils.url_features import extract_url_features


def test_safe_url_returns_all_keys():
    features = extract_url_features("https://www.google.com")
    expected_keys = [
        "url_length", "domain_length", "path_length", "num_dots",
        "num_hyphens", "num_slashes", "num_question_marks", "has_https",
        "has_ip", "contains_at_symbol", "contains_double_slash_redirect",
        "num_subdomains", "full_url"
    ]
    for key in expected_keys:
        assert key in features, f"Missing key: {key}"


def test_https_detected():
    features = extract_url_features("https://example.com")
    assert features["has_https"] is True


def test_http_not_https():
    features = extract_url_features("http://example.com")
    assert features["has_https"] is False


def test_ip_based_url_detected():
    features = extract_url_features("http://192.168.1.1/login")
    assert features["has_ip"] is True


def test_domain_url_not_flagged_as_ip():
    features = extract_url_features("https://example.com")
    assert features["has_ip"] is False


def test_at_symbol_detected():
    features = extract_url_features("http://evil.com@real.com/page")
    assert features["contains_at_symbol"] is True


def test_no_at_symbol():
    features = extract_url_features("https://example.com/path")
    assert features["contains_at_symbol"] is False


def test_subdomain_counting():
    features = extract_url_features("https://a.b.c.example.com")
    assert features["num_subdomains"] == 3


def test_no_subdomains():
    features = extract_url_features("https://example.com")
    assert features["num_subdomains"] == 0


def test_double_slash_in_path_detected():
    features = extract_url_features("https://legit.com//redirect.evil.com")
    assert features["contains_double_slash_redirect"] is True


def test_no_double_slash():
    features = extract_url_features("https://example.com/path/page")
    assert features["contains_double_slash_redirect"] is False


def test_url_length_measured():
    url = "https://example.com/" + "a" * 80
    features = extract_url_features(url)
    assert features["url_length"] == len(url)


def test_num_dots_counted():
    features = extract_url_features("https://sub.example.com/a.html")
    assert features["num_dots"] == 3


def test_num_hyphens_counted():
    features = extract_url_features("https://my-phishing-site.com")
    assert features["num_hyphens"] == 2


def test_num_question_marks():
    features = extract_url_features("https://example.com/page?a=1&b=2")
    assert features["num_question_marks"] == 1


def test_full_url_preserved():
    url = "https://www.example.com/path"
    features = extract_url_features(url)
    assert features["full_url"] == url
