from datetime import datetime, timezone

import tldextract
import whois

from backend.app.utils import domain_cache


def get_domain_info(url: str):

    extracted = tldextract.extract(url)
    domain = f"{extracted.domain}.{extracted.suffix}"
    tld = extracted.suffix  # siempre disponible, independiente del WHOIS

    cached = domain_cache.get(domain)
    if cached:
        return cached

    result = _lookup_domain_info(domain, tld)
    domain_cache.set(domain, result)
    return result


def _lookup_domain_info(domain: str, tld: str):

    try:

        w = whois.whois(domain, timeout=5)

        creation_date = w.creation_date
        expiration_date = w.expiration_date

        # Algunos WHOIS devuelven listas
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if isinstance(expiration_date, list):
            expiration_date = expiration_date[0]

        age_days = None

        if creation_date:

            # Si la fecha no tiene timezone, agregar UTC
            if creation_date.tzinfo is None:
                creation_date = creation_date.replace(
                    tzinfo=timezone.utc
                )

            age_days = (
                datetime.now(timezone.utc)
                - creation_date
            ).days

        return {
            "domain": domain,
            "registrar": str(w.registrar),
            "creation_date": str(creation_date),
            "expiration_date": str(expiration_date),
            "domain_age_days": age_days,
            "tld": tld
        }

    except Exception as e:

        return {
            "domain": domain,
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "domain_age_days": None,
            "tld": tld,
            "error": str(e)
        }