from urllib.parse import urlparse


class FeatureMapper:

    @staticmethod
    def map(url, url_features, html_analysis):

        parsed = urlparse(url)
        html_features = html_analysis.get("html_features", {})

        return {

            # ── URL features ──────────────────────────────────

            "URLLength":    url_features.get("url_length", 0),
            "DomainLength": url_features.get("domain_length", 0),
            "IsDomainIP":   int(url_features.get("has_ip", False)),
            "TLDLength":    len(parsed.netloc.split(".")[-1]),
            "NoOfSubDomain": max(0, len(parsed.netloc.split(".")) - 2),
            "IsHTTPS":      int(url_features.get("has_https", False)),

            "NoOfLettersInURL":       url_features.get("num_letters", 0),
            "LetterRatioInURL":       url_features.get("letter_ratio", 0.0),
            "NoOfDegitsInURL":        url_features.get("num_digits", 0),
            "DegitRatioInURL":        url_features.get("digit_ratio", 0.0),
            "NoOfEqualsInURL":        url_features.get("num_equals", 0),
            "NoOfAmpersandInURL":     url_features.get("num_ampersands", 0),
            "NoOfOtherSpecialCharsInURL": url_features.get("num_special_chars", 0),
            "SpacialCharRatioInURL":  url_features.get("special_char_ratio", 0.0),
            "HasObfuscation":         int(url_features.get("has_obfuscation", False)),
            "NoOfObfuscatedChar":     url_features.get("num_obfuscated_chars", 0),
            "ObfuscationRatio":       url_features.get("obfuscation_ratio", 0.0),

            # ── HTML features ─────────────────────────────────

            "HasTitle":        html_features.get("HasTitle", 0),
            "HasFavicon":      html_features.get("HasFavicon", 0),
            "HasDescription":  html_features.get("HasDescription", 0),
            "HasPasswordField": html_features.get("HasPasswordField", 0),
            "HasHiddenFields":  html_features.get("HasHiddenFields", 0),
            "NoOfImage":       html_features.get("NoOfImage", 0),
            "NoOfCSS":         html_features.get("NoOfCSS", 0),
            "NoOfJS":          html_features.get("NoOfJS", 0),

            "NoOfiFrame":            html_features.get("NoOfiFrame", 0),
            "HasExternalFormSubmit": html_features.get("HasExternalFormSubmit", 0),
            "HasSocialNet":          html_features.get("HasSocialNet", 0),
            "HasSubmitButton":       html_features.get("HasSubmitButton", 0),
            "HasCopyrightInfo":      html_features.get("HasCopyrightInfo", 0),
            "IsResponsive":          html_features.get("IsResponsive", 0),
            "NoOfSelfRef":           html_features.get("NoOfSelfRef", 0),
            "NoOfEmptyRef":          html_features.get("NoOfEmptyRef", 0),
            "NoOfExternalRef":       html_features.get("NoOfExternalRef", 0),
        }
