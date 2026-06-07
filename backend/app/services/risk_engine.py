class RiskEngine:

    @staticmethod
    def calculate(url_features, domain_info):

        score = 50

        reasons = []

        # ==========================
        # HTTPS
        # ==========================

        if url_features.get("has_https"):

            score += 10

            reasons.append(
                "HTTPS válido"
            )

        else:

            score -= 20

            reasons.append(
                "No utiliza HTTPS"
            )

        # ==========================
        # Uso de IP
        # ==========================

        if url_features.get("has_ip"):

            score -= 30

            reasons.append(
                "Uso de dirección IP en lugar de dominio"
            )

        # ==========================
        # Símbolo @
        # ==========================

        if url_features.get(
            "contains_at_symbol"
        ):

            score -= 40

            reasons.append(
                "Contiene símbolo @"
            )

        # ==========================
        # Subdominios
        # ==========================

        if url_features.get(
            "num_subdomains",
            0
        ) > 2:

            score -= 15

            reasons.append(
                "Demasiados subdominios"
            )

        # ==========================
        # Redirecciones
        # ==========================

        if url_features.get(
            "contains_double_slash_redirect"
        ):

            score -= 10

            reasons.append(
                "Posible redirección sospechosa"
            )

        # ==========================
        # Longitud URL
        # ==========================

        if url_features.get(
            "url_length",
            0
        ) > 75:

            score -= 10

            reasons.append(
                "URL excesivamente larga"
            )

        # ==========================
        # Guiones
        # ==========================

        if url_features.get(
            "num_hyphens",
            0
        ) > 3:

            score -= 10

            reasons.append(
                "Demasiados guiones"
            )

        # ==========================
        # Antigüedad dominio
        # ==========================

        age = domain_info.get(
            "domain_age_days"
        )

        if age is not None:

            if age < 30:

                score -= 30

                reasons.append(
                    "Dominio creado hace menos de 30 días"
                )

            elif age < 180:

                score -= 15

                reasons.append(
                    "Dominio relativamente nuevo"
                )

            elif age > 3650:

                score += 20

                reasons.append(
                    "Dominio con más de 10 años de antigüedad"
                )

            elif age > 365:

                score += 10

                reasons.append(
                    "Dominio con más de 1 año de antigüedad"
                )

        # ==========================
        # TLD
        # ==========================

        suspicious_tlds = [
            "xyz",
            "top",
            "click",
            "online",
            "shop"
        ]

        trusted_tlds = [
            "com",
            "org",
            "edu",
            "gov",
            "net"
        ]

        tld = domain_info.get(
            "tld"
        )

        if tld in suspicious_tlds:

            score -= 20

            reasons.append(
                f"TLD sospechoso: .{tld}"
            )

        elif tld in trusted_tlds:

            score += 10

            reasons.append(
                f"TLD confiable: .{tld}"
            )

        # ==========================
        # Limitar score
        # ==========================

        score = max(
            0,
            min(score, 100)
        )

        # ==========================
        # Clasificación
        # ==========================

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

            "reasons": reasons
        }