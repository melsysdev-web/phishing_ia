import whois
import tldextract

from datetime import datetime, timezone


def get_domain_info(url: str):

    try:

        extracted = tldextract.extract(url)

        domain = f"{extracted.domain}.{extracted.suffix}"

        w = whois.whois(domain)

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
            "tld": extracted.suffix
        }

    except Exception as e:

        return {
            "domain": None,
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "domain_age_days": None,
            "tld": None,
            "error": str(e)
        }