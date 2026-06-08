class RiskEngine:

    @staticmethod
    def calculate(
        url_features,
        domain_info,
        html_analysis=None
    ):

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
        # Subdominios excesivos
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
        # Redirecciones sospechosas
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
        # Longitud Path
        # ==========================

        if url_features.get(
            "path_length",
            0
        ) > 50:

            score -= 10

            reasons.append(
                "Ruta excesivamente larga"
            )

        # ==========================
        # Guiones excesivos
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
        # Keywords sospechosas
        # ==========================

        suspicious_keywords = [

            "login",
            "signin",
            "account",
            "verify",
            "verification",
            "secure",
            "security",
            "password",
            "reset",
            "confirm",
            "update",
            "bank",
            "wallet",
            "paypal"
        ]

        full_url = url_features.get(
            "full_url",
            ""
        ).lower()

        matches = 0

        for keyword in suspicious_keywords:

            if keyword in full_url:

                matches += 1

        if matches >= 3:

            penalty = min(
                matches * 3,
                25
            )

            score -= penalty

            reasons.append(
                f"Contiene {matches} palabras clave asociadas a phishing"
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
        # HTML ANALYSIS
        # ==========================

        if (
            html_analysis
            and html_analysis.get(
                "success"
            )
        ):

            html_features = (
                html_analysis.get(
                    "html_features",
                    {}
                )
            )

            if html_features.get(
                "HasPasswordField"
            ):

                score -= 15

                reasons.append(
                    "Página contiene formulario de contraseña"
                )

            if html_features.get(
                "HasHiddenFields"
            ):

                score -= 5

                reasons.append(
                    "Página contiene campos ocultos"
                )

            if not html_features.get(
                "HasTitle"
            ):

                score -= 5

                reasons.append(
                    "Página sin título"
                )

            if not html_features.get(
                "HasFavicon"
            ):

                score -= 3

                reasons.append(
                    "Página sin favicon"
                )

            if html_features.get(
                "NoOfJS",
                0
            ) > 50:

                score -= 10

                reasons.append(
                    "Cantidad elevada de JavaScript"
                )

            if html_features.get(
                "NoOfImage",
                0
            ) > 100:

                score -= 5

                reasons.append(
                    "Cantidad inusual de imágenes"
                )

        # ==========================
        # Limitar score
        # ==========================

        score = max(
            0,
            min(score, 100)
        )

        # ==========================
        # Clasificación final
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