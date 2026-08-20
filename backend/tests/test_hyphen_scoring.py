"""
Tests para la penalización por guiones.

La regla contaba guiones en toda la URL, así que penalizaba cualquier noticia
o documentación con slug largo y dejaba pasar dominios como
paypal-secure-login-verify.com. Ahora sólo mira el hostname.
"""

from backend.app.services.risk_engine import _MAX_DOMAIN_HYPHENS, RiskEngine
from backend.app.utils.url_features import extract_url_features


def _penalized(url):
    features = extract_url_features(url)
    result = RiskEngine.calculate(features, {"tld": "com", "domain_age_days": 3000})
    return any("guiones" in reason for reason in result["reasons"])


def _score(url):
    features = extract_url_features(url)
    return RiskEngine.calculate(features, {"tld": "com", "domain_age_days": 3000})["score"]


class TestPathHyphensAreIgnored:
    def test_news_article_slug_is_not_penalized(self):
        url = (
            "https://elpais.com/tecnologia/2024-01-15/"
            "la-inteligencia-artificial-y-el-futuro-del-trabajo.html"
        )
        assert not _penalized(url)

    def test_documentation_slug_is_not_penalized(self):
        url = (
            "https://developer.mozilla.org/es/docs/Learn/"
            "Getting-started-with-the-web/Dealing-with-files"
        )
        assert not _penalized(url)

    def test_many_path_hyphens_do_not_lower_score(self):
        plain = _score("https://example.com/articulo")
        slugged = _score("https://example.com/un-articulo-con-un-slug-muy-largo-de-verdad")
        assert plain == slugged

    def test_query_string_hyphens_are_ignored(self):
        assert not _penalized("https://example.com/?q=a-b-c-d-e-f-g-h")


class TestDomainHyphensArePenalized:
    def test_brand_impersonation_domain_is_penalized(self):
        assert _penalized("https://paypal-secure-login-verify.com/")

    def test_lure_domain_is_penalized(self):
        assert _penalized("https://banco-verificacion-cuenta-segura.com/acceso")

    def test_penalized_domain_scores_below_clean_one(self):
        clean = _score("https://example.com/")
        hyphenated = _score("https://paypal-secure-login-verify.com/")
        assert hyphenated < clean


class TestThreshold:
    def test_single_hyphen_domain_is_allowed(self):
        assert not _penalized("https://mi-empresa.com/")

    def test_two_hyphen_domain_is_allowed(self):
        assert not _penalized("https://mi-empresa-local.com/")

    def test_three_hyphen_domain_is_penalized(self):
        assert _penalized("https://uno-dos-tres-cuatro.com/")

    def test_threshold_boundary_matches_constant(self):
        at_limit = "https://" + "-".join(["a"] * (_MAX_DOMAIN_HYPHENS + 1)) + ".com/"
        over_limit = "https://" + "-".join(["a"] * (_MAX_DOMAIN_HYPHENS + 2)) + ".com/"
        assert not _penalized(at_limit)
        assert _penalized(over_limit)


class TestFeatureExtraction:
    def test_domain_hyphens_exclude_path(self):
        features = extract_url_features("https://ejemplo.com/a-b-c-d-e")
        assert features["num_hyphens_domain"] == 0

    def test_domain_hyphens_count_hostname_only(self):
        features = extract_url_features("https://mi-sitio-web.com/a-b-c")
        assert features["num_hyphens_domain"] == 2

    def test_whole_url_count_is_preserved_for_random_forest(self):
        """num_hyphens alimenta al RF como NumHyphens; no debe cambiar."""
        # 2 en el hostname (mi-sitio-web) + 2 en el path (a-b-c)
        features = extract_url_features("https://mi-sitio-web.com/a-b-c")
        assert features["num_hyphens"] == 4

    def test_subdomain_hyphens_are_counted(self):
        features = extract_url_features("https://login-seguro.banco-falso.com/")
        assert features["num_hyphens_domain"] == 2
