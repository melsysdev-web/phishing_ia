import re
from urllib.parse import urlparse

import tldextract


def extract_url_features(url: str):

    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    ext = tldextract.extract(url)
    subdomain_str = ext.subdomain
    num_subdomains = len(subdomain_str.split(".")) if subdomain_str else 0

    features = {

        "url_length": len(url),

        "domain_length": len(parsed.netloc),

        "path_length": len(parsed.path),

        "num_dots": url.count("."),

        # Guiones en toda la URL. Lo consume el Random Forest como NumHyphens;
        # no cambiar su definición sin reentrenar el modelo.
        "num_hyphens": url.count("-"),

        # Guiones sólo en el hostname. Los del path son ruido (cada slug de
        # noticia o blog los usa); los del dominio son la señal real, porque
        # el phishing registra nombres como paypal-secure-login-verify.com.
        "num_hyphens_domain": hostname.count("-"),

        "num_slashes": url.count("/"),

        "num_question_marks": url.count("?"),

        "has_https": parsed.scheme == "https",

        "has_ip": bool(
            re.search(
                r"\d+\.\d+\.\d+\.\d+",
                hostname
            )
        ),

        "contains_at_symbol": "@" in url,

        "contains_double_slash_redirect":
            "//" in parsed.path,

        "num_subdomains": num_subdomains,

        "full_url": url
    }

    return features