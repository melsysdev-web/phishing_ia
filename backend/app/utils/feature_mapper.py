from urllib.parse import urlparse


class FeatureMapper:

    @staticmethod
    def map(url, url_features, html_analysis):

        parsed = urlparse(url)

        html_features = html_analysis.get(
            "html_features",
            {}
        )

        return {

            # URL

            "URLLength":
                url_features.get("url_length", 0),

            "DomainLength":
                url_features.get("domain_length", 0),

            "PathLength":
                url_features.get("path_length", 0),

            "NumDots":
                url_features.get("num_dots", 0),

            "NumHyphens":
                url_features.get("num_hyphens", 0),

            "NumQuestionMarks":
                url_features.get("num_question_marks", 0),

            "ContainsAtSymbol":
                int(
                    url_features.get(
                        "contains_at_symbol",
                        False
                    )
                ),

            "ContainsDoubleSlashRedirect":
                int(
                    url_features.get(
                        "contains_double_slash_redirect",
                        False
                    )
                ),

            "IsDomainIP":
                int(
                    url_features.get(
                        "has_ip",
                        False
                    )
                ),

            "TLDLength":
                len(
                    parsed.netloc.split(".")[-1]
                ),

            "NoOfSubDomain":
                max(
                    0,
                    len(parsed.netloc.split(".")) - 2
                ),

            "IsHTTPS":
                int(
                    url_features.get(
                        "has_https",
                        False
                    )
                ),

            # HTML

            "HasTitle":
                html_features.get(
                    "HasTitle",
                    0
                ),

            "HasFavicon":
                html_features.get(
                    "HasFavicon",
                    0
                ),

            "HasDescription":
                html_features.get(
                    "HasDescription",
                    0
                ),

            "HasPasswordField":
                html_features.get(
                    "HasPasswordField",
                    0
                ),

            "HasHiddenFields":
                html_features.get(
                    "HasHiddenFields",
                    0
                ),

            "NoOfImage":
                html_features.get(
                    "NoOfImage",
                    0
                ),

            "NoOfCSS":
                html_features.get(
                    "NoOfCSS",
                    0
                ),

            "NoOfJS":
                html_features.get(
                    "NoOfJS",
                    0
                )
        }