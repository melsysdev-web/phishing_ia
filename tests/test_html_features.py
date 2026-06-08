from backend.app.analyzers.html_features import HtmlFeatures


def test_returns_all_keys():
    features = HtmlFeatures.extract("<html></html>")
    expected_keys = [
        "HasTitle", "HasFavicon", "HasDescription",
        "HasPasswordField", "HasHiddenFields",
        "NoOfImage", "NoOfCSS", "NoOfJS"
    ]
    for key in expected_keys:
        assert key in features, f"Missing key: {key}"


def test_safe_page_has_title_favicon_description(sample_html_safe):
    features = HtmlFeatures.extract(sample_html_safe)
    assert features["HasTitle"] == 1
    assert features["HasFavicon"] == 1
    assert features["HasDescription"] == 1


def test_safe_page_counts_assets(sample_html_safe):
    features = HtmlFeatures.extract(sample_html_safe)
    assert features["NoOfImage"] == 1
    assert features["NoOfCSS"] == 1
    assert features["NoOfJS"] == 1


def test_phishing_page_has_password_field(sample_html_phishing):
    features = HtmlFeatures.extract(sample_html_phishing)
    assert features["HasPasswordField"] == 1


def test_phishing_page_has_hidden_fields(sample_html_phishing):
    features = HtmlFeatures.extract(sample_html_phishing)
    assert features["HasHiddenFields"] == 1


def test_phishing_page_missing_title_favicon(sample_html_phishing):
    features = HtmlFeatures.extract(sample_html_phishing)
    assert features["HasTitle"] == 0
    assert features["HasFavicon"] == 0


def test_empty_html_all_zeros():
    features = HtmlFeatures.extract("<html></html>")
    assert features["HasTitle"] == 0
    assert features["HasFavicon"] == 0
    assert features["HasDescription"] == 0
    assert features["HasPasswordField"] == 0
    assert features["HasHiddenFields"] == 0
    assert features["NoOfImage"] == 0
    assert features["NoOfCSS"] == 0
    assert features["NoOfJS"] == 0


def test_multiple_images_counted():
    html = "<html><body>" + "<img src='x.jpg'>" * 7 + "</body></html>"
    features = HtmlFeatures.extract(html)
    assert features["NoOfImage"] == 7


def test_multiple_scripts_counted():
    html = "<html><head>" + "<script src='x.js'></script>" * 4 + "</head></html>"
    features = HtmlFeatures.extract(html)
    assert features["NoOfJS"] == 4


def test_multiple_css_counted():
    html = (
        "<html><head>"
        + '<link rel="stylesheet" href="a.css">' * 3
        + "</head></html>"
    )
    features = HtmlFeatures.extract(html)
    assert features["NoOfCSS"] == 3


def test_no_password_field_in_safe_page(sample_html_safe):
    features = HtmlFeatures.extract(sample_html_safe)
    assert features["HasPasswordField"] == 0
    assert features["HasHiddenFields"] == 0
