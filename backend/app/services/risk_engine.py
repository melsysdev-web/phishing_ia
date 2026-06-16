from urllib.parse import urlparse
import tldextract

# ── Listas de referencia ──────────────────────────────────────────────────────

_BRAND_NAMES = {
    'google', 'paypal', 'amazon', 'facebook', 'apple', 'microsoft',
    'netflix', 'instagram', 'twitter', 'linkedin', 'dropbox', 'spotify',
    'adobe', 'samsung', 'ebay', 'youtube', 'whatsapp', 'telegram',
    'bankofamerica', 'chase', 'wellsfargo', 'citibank', 'hsbc',
}

# Dominios registrables de marcas de alta confianza
_TRUSTED_BRANDS = {
    'google.com', 'youtube.com', 'facebook.com', 'instagram.com',
    'twitter.com', 'x.com', 'linkedin.com', 'amazon.com', 'apple.com',
    'microsoft.com', 'github.com', 'netflix.com', 'paypal.com',
    'wikipedia.org', 'reddit.com', 'whatsapp.com', 'telegram.org',
    'adobe.com', 'dropbox.com', 'spotify.com', 'zoom.us',
    'office.com', 'live.com', 'outlook.com', 'yahoo.com',
    'cloudflare.com', 'amazonaws.com', 'azure.com', 'office365.com',
}

# Acortadores de URL conocidos
_URL_SHORTENERS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd',
    'short.link', 'rebrand.ly', 'buff.ly', 'adf.ly', 'lnkd.in',
    'cutt.ly', 'shorturl.at', 'rb.gy', 'clck.ru', 'trib.al',
    'tiny.cc', 'bl.ink', 'snip.ly', 'tr.im',
}

# Hosting gratuito con alta tasa de abuso en phishing
_SUSPICIOUS_HOSTS = {
    '000webhostapp.com', 'yolasite.com', 'weebly.com', 'jimdo.com',
    'wixsite.com', 'mystrikingly.com', 'freewha.com',
    'infinityfreemember.com', 'bravesites.com', 'sitey.me',
}

# Parámetros que indican redirección abierta
_REDIRECT_PARAMS = {
    'redirect', 'redirect_uri', 'redirect_url', 'url', 'goto',
    'next', 'return', 'returnurl', 'return_url', 'dest', 'destination',
    'forward', 'redir', 'ref_url',
}

_SUSPICIOUS_TLDS = {
    "xyz", "top", "click", "online", "shop",
    "tk", "ml", "ga", "cf", "gq", "pw", "icu", "buzz",
    "loan", "win", "stream", "faith", "party", "bid",
}

_TRUSTED_TLDS = {"com", "org", "edu", "gov", "net"}

_TRUSTED_CCTLDS = {
    "sv", "mx", "ar", "co", "br", "au", "uk", "de", "fr",
    "jp", "ca", "es", "it", "nl", "se", "ch", "pt", "cr",
    "gt", "hn", "pa", "do", "pe", "cl", "ec", "in", "sg",
}


class RiskEngine:

    @staticmethod
    def calculate(
        url_features,
        domain_info,
        html_analysis=None,
        vt_result=None,
        sb_result=None,
        fc_result=None,
        content_result=None,
        ml_result=None
    ):
        _signals = []
        authoritative_threat = False

        def _add(delta, text):
            _signals.append((delta, text))

        # ── Extraer datos de URL una sola vez ─────────────────────────────────
        full_url   = url_features.get("full_url", "")
        parsed     = urlparse(full_url) if full_url else None
        ext        = tldextract.extract(full_url) if full_url else None
        registrable = f"{ext.domain}.{ext.suffix}".lower() if ext else ""

        # ── HTTPS ─────────────────────────────────────────────────────────────
        if url_features.get("has_https"):
            _add(+10, "HTTPS válido")
        else:
            _add(-20, "No utiliza HTTPS")

        # ── IP en lugar de dominio ────────────────────────────────────────────
        if url_features.get("has_ip"):
            _add(-30, "Uso de dirección IP en lugar de dominio")

        # ── Símbolo @ ─────────────────────────────────────────────────────────
        if url_features.get("contains_at_symbol"):
            _add(-40, "Contiene símbolo @ en la URL")

        # ── Punycode / IDN homograph ──────────────────────────────────────────
        if parsed and "xn--" in (parsed.hostname or "").lower():
            _add(-25, "Dominio usa codificación Punycode (posible homografía)")

        # ── Puerto no estándar ────────────────────────────────────────────────
        if parsed and parsed.port and parsed.port not in (80, 443):
            _add(-15, f"Puerto no estándar en la URL: :{parsed.port}")

        # ── Acortador de URL ──────────────────────────────────────────────────
        if registrable in _URL_SHORTENERS:
            _add(-20, f"Servicio acortador de URL: {registrable}")

        # ── Hosting gratuito de alto abuso ────────────────────────────────────
        if registrable in _SUSPICIOUS_HOSTS:
            _add(-10, f"Alojado en plataforma gratuita con alta tasa de phishing: {registrable}")

        # ── Parámetro de redirección abierta ──────────────────────────────────
        if parsed and parsed.query:
            params = {p.split("=")[0].lower() for p in parsed.query.split("&") if "=" in p}
            redirect_found = params & _REDIRECT_PARAMS
            if redirect_found:
                _add(-10, f"Parámetro de redirección en URL: {', '.join(sorted(redirect_found))}")

        # ── Dominio registrable excesivamente largo ───────────────────────────
        if ext and len(ext.domain) > 30:
            _add(-8, f"Dominio inusualmente largo ({len(ext.domain)} caracteres)")

        # ── Subdominios excesivos ─────────────────────────────────────────────
        if url_features.get("num_subdomains", 0) > 2:
            _add(-15, "Demasiados subdominios")

        # ── Redirección doble slash ───────────────────────────────────────────
        if url_features.get("contains_double_slash_redirect"):
            _add(-10, "Posible redirección sospechosa")

        # ── Guiones excesivos ─────────────────────────────────────────────────
        if url_features.get("num_hyphens", 0) > 3:
            _add(-10, "Exceso de guiones en la URL")

        # ── Suplantación de marca en subdominio ───────────────────────────────
        if ext and ext.subdomain:
            subdomain_lower = ext.subdomain.lower()
            domain_lower    = ext.domain.lower()
            for brand in _BRAND_NAMES:
                if brand in subdomain_lower and brand not in domain_lower:
                    _add(-30, f"Posible suplantación de marca en subdominio ({brand})")
                    break

        # ── Marca de confianza verificada ─────────────────────────────────────
        if registrable in _TRUSTED_BRANDS:
            _add(+20, f"Dominio de marca verificada: {registrable}")

        # ── Antigüedad del dominio ────────────────────────────────────────────
        age = domain_info.get("domain_age_days")
        if age is not None:
            if age < 30:
                _add(-30, "Dominio creado hace menos de 30 días")
            elif age < 180:
                _add(-15, "Dominio relativamente nuevo (menos de 6 meses)")
            elif age > 3650:
                _add(+20, "Dominio con más de 10 años de antigüedad")
            elif age > 365:
                _add(+10, "Dominio con más de 1 año de antigüedad")

        # ── TLD ───────────────────────────────────────────────────────────────
        tld      = domain_info.get("tld") or ""
        tld_base = tld.split(".")[0] if tld else ""

        if tld in _SUSPICIOUS_TLDS or tld_base in _SUSPICIOUS_TLDS:
            _add(-20, f"TLD con alto índice de abuso: .{tld}")
        elif tld in _TRUSTED_TLDS or tld_base in _TRUSTED_TLDS:
            _add(+10, f"TLD confiable: .{tld}")
        elif tld in _TRUSTED_CCTLDS or tld_base in _TRUSTED_CCTLDS:
            _add(+5, f"Dominio de país reconocido: .{tld}")

        # ── HTML ──────────────────────────────────────────────────────────────
        has_title = True
        if html_analysis and html_analysis.get("success"):
            html_features = html_analysis.get("html_features", {})
            has_title = bool(html_features.get("HasTitle", True))
            if not has_title:
                _add(-5, "Página sin título")

        # ── Regla combinada: dominio nuevo + sin título ───────────────────────
        # Phishing rápido típicamente lanza páginas sin título en dominios recién creados
        if age is not None and age < 180 and not has_title:
            _add(-10, "Dominio nuevo sin título de página (combinación de riesgo)")

        # ── VirusTotal ────────────────────────────────────────────────────────
        if vt_result and "error" not in vt_result:
            verdict = vt_result.get("verdict")
            if verdict == "malicious":
                malicious_count = vt_result.get("stats", {}).get("malicious", 0)
                _add(-40, f"VirusTotal: {malicious_count} motores lo clasifican como malicioso")
                authoritative_threat = True
            elif verdict == "suspicious":
                _add(-20, "VirusTotal: URL marcada como sospechosa")
            elif verdict == "clean":
                _add(+10, "VirusTotal: URL limpia")

        # ── Google Safe Browsing ──────────────────────────────────────────────
        if sb_result and "error" not in sb_result:
            if sb_result.get("is_threat"):
                verdict     = sb_result.get("verdict")
                threat_types = [t.get("type") for t in sb_result.get("threats", [])]
                if verdict == "dangerous":
                    _add(-50, "Google Safe Browsing: URL detectada como " + ", ".join(threat_types))
                    authoritative_threat = True
                elif verdict == "suspicious":
                    _add(-25, "Google Safe Browsing: URL marcada como " + ", ".join(threat_types))
            else:
                _add(+5, "Google Safe Browsing: URL segura")

        # ── Fact Check (solo bonificación) ────────────────────────────────────
        if fc_result and "error" not in fc_result and fc_result.get("verdict") == "reliable":
            if fc_result.get("publisher_count", 0) > 0:
                _add(+10, "Fact Check: dominio reconocido como verificador")
            else:
                _add(+10, "Fact Check: dominio con reclamaciones verificadas")

        # ── Machine Learning (Fusion) ─────────────────────────────────────────
        if ml_result and "error" not in ml_result:
            p = ml_result.get("phishing_probability", 0.5)
            if p >= 0.85:
                _add(-35, f"ML: alta confianza de phishing ({round(p * 100)}%)")
            elif p >= 0.65:
                _add(-15, f"ML: indica posible phishing ({round(p * 100)}%)")
            elif p <= 0.15:
                _add(+20, f"ML: confirma URL legítima ({round((1 - p) * 100)}% confianza)")
            elif p <= 0.35:
                _add(+10, f"ML: URL probablemente legítima ({round((1 - p) * 100)}% confianza)")

        # ── Score final ───────────────────────────────────────────────────────
        score = 50 + sum(delta for delta, _ in _signals)

        # Si VT o Safe Browsing confirman amenaza real, garantizar HIGH
        if authoritative_threat:
            score = min(score, 25)

        score = max(0, min(score, 100))

        # Razones ordenadas por impacto; ML tiene prioridad en empates
        reasons = [
            text for _, text in sorted(
                _signals,
                key=lambda x: (-abs(x[0]), 0 if x[1].startswith("ML:") else 1)
            )
        ]

        # ── Clasificación ─────────────────────────────────────────────────────
        if score >= 80:
            risk = "LOW"
        elif score >= 50:
            risk = "MEDIUM"
        else:
            risk = "HIGH"

        return {
            "risk": risk,
            "confidence": score,
            "score": score,
            "reasons": reasons,
        }
