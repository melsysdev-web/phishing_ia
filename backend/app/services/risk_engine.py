class RiskEngine:

    @staticmethod
    def calculate(
        url_features,
        domain_info,
        html_analysis=None,
        vt_result=None,
        sb_result=None,
        fc_result=None,
        content_result=None
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
        # VIRUSTOTAL
        # ==========================

        if (
            vt_result
            and "error" not in vt_result
        ):

            verdict = vt_result.get("verdict")

            if verdict == "malicious":

                score -= 40

                malicious_count = (
                    vt_result
                    .get("stats", {})
                    .get("malicious", 0)
                )

                reasons.append(
                    f"VirusTotal: {malicious_count} "
                    f"motores lo clasifican como malicioso"
                )

            elif verdict == "suspicious":

                score -= 20

                reasons.append(
                    "VirusTotal: URL marcada como sospechosa"
                )

            elif verdict == "clean":

                score += 10

                reasons.append(
                    "VirusTotal: URL limpia"
                )

        # ==========================
        # SAFE BROWSING
        # ==========================

        if (
            sb_result
            and "error" not in sb_result
            and sb_result.get("is_threat")
        ):

            verdict = sb_result.get("verdict")

            threat_types = [
                t.get("type")
                for t in sb_result.get("threats", [])
            ]

            if verdict == "dangerous":

                score -= 50

                reasons.append(
                    "Google Safe Browsing: URL detectada como "
                    + ", ".join(threat_types)
                )

            elif verdict == "suspicious":

                score -= 25

                reasons.append(
                    "Google Safe Browsing: URL marcada como "
                    + ", ".join(threat_types)
                )

        # ==========================
        # FACT CHECK
        # ==========================

        if (
            fc_result
            and "error" not in fc_result
            and fc_result.get("verdict") != "no_data"
        ):

            fc_verdict = fc_result.get("verdict")

            if fc_verdict == "unreliable":

                score -= 30

                reasons.append(
                    "Fact Check: dominio asociado a "
                    f"{fc_result.get('fake_count', 0)} "
                    "verificaciones falsas"
                )

            elif fc_verdict == "suspicious":

                score -= 15

                reasons.append(
                    "Fact Check: dominio con reclamaciones cuestionadas"
                )

            elif fc_verdict == "reliable":

                score += 10

                publisher_count = fc_result.get(
                    "publisher_count", 0
                )

                if publisher_count > 0:
                    reasons.append(
                        "Fact Check: dominio reconocido como verificador"
                    )
                else:
                    reasons.append(
                        "Fact Check: dominio con reclamaciones verificadas"
                    )

        # ==========================
        # CONTENT CLASSIFICATION
        # ==========================

        if (
            content_result
            and "error" not in content_result
            and content_result.get("label") not in (
                None, "UNKNOWN"
            )
        ):

            label = content_result.get("label")
            confidence = content_result.get("confidence", 0.0)

            if label == "FAKE":

                if confidence >= 0.80:

                    score -= 25

                    reasons.append(
                        f"Contenido clasificado como FALSO "
                        f"(confianza: {round(confidence * 100)}%)"
                    )

                else:

                    score -= 10

                    reasons.append(
                        "Contenido posiblemente falso o engañoso"
                    )

            elif label == "REAL" and confidence >= 0.80:

                score += 10

                reasons.append(
                    f"Contenido clasificado como legítimo "
                    f"(confianza: {round(confidence * 100)}%)"
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