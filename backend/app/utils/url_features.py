from urllib.parse import urlparse
import re


def extract_url_features(url: str):

    parsed = urlparse(url)

    features = {

        "url_length": len(url),

        "domain_length": len(parsed.netloc),

        "path_length": len(parsed.path),

        "num_dots": url.count("."),

        "num_hyphens": url.count("-"),

        "num_slashes": url.count("/"),

        "num_question_marks": url.count("?"),

        "has_https": parsed.scheme == "https",

        "has_ip": bool(
            re.search(
                r"\d+\.\d+\.\d+\.\d+",
                parsed.netloc
            )
        ),

        # NUEVAS FEATURES

        "contains_at_symbol": "@" in url,

        "contains_double_slash_redirect":
            "//" in parsed.path,

        "num_subdomains":
             max(
                 len(parsed.netloc.split(".")) - 2,
                 0
                )
}

    return features