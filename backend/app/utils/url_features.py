import re
from urllib.parse import urlparse

_STANDARD_URL_CHARS = frozenset('.-/?#_:%:@~')


def extract_url_features(url: str):

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    url_len = len(url) or 1

    num_letters = sum(c.isalpha() for c in url)
    num_digits  = sum(c.isdigit() for c in url)
    obfuscated  = re.findall(r'%[0-9A-Fa-f]{2}', url)
    num_obfuscated = len(obfuscated)

    # chars that are not alphanumeric and not in the standard set
    num_other_special = sum(
        1 for c in url
        if not c.isalnum() and c not in _STANDARD_URL_CHARS
        and c not in '?=&'
    )
    # ratio: all non-alphanumeric / url_len
    num_all_special = sum(1 for c in url if not c.isalnum())

    return {
        "url_length":    url_len,
        "domain_length": len(parsed.netloc),
        "path_length":   len(parsed.path),
        "num_dots":      url.count("."),
        "num_hyphens":   url.count("-"),
        "num_slashes":   url.count("/"),
        "num_question_marks": url.count("?"),
        "has_https":     parsed.scheme == "https",
        "has_ip":        bool(re.search(r"\d+\.\d+\.\d+\.\d+", hostname)),
        "contains_at_symbol":             "@" in url,
        "contains_double_slash_redirect": "//" in parsed.path,
        "num_subdomains": max(len(hostname.split(".")) - 2, 0),
        "full_url": url,

        # Extended URL features
        "num_letters":     num_letters,
        "letter_ratio":    round(num_letters / url_len, 4),
        "num_digits":      num_digits,
        "digit_ratio":     round(num_digits / url_len, 4),
        "num_equals":      url.count("="),
        "num_ampersands":  url.count("&"),
        "num_special_chars":   num_other_special,
        "special_char_ratio":  round(num_all_special / url_len, 4),
        "has_obfuscation":     bool(obfuscated),
        "num_obfuscated_chars": num_obfuscated,
        "obfuscation_ratio":   round(num_obfuscated / url_len, 4),
    }
