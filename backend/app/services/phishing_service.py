import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.app.utils.url_features import extract_url_features
from backend.app.utils.domain_utils import get_domain_info
from backend.app.utils.feature_mapper import FeatureMapper
from backend.app.utils import url_cache

from backend.app.services.risk_engine import RiskEngine
from backend.app.services.virustotal_service import VirusTotalService
from backend.app.services.safe_browsing_service import SafeBrowsingService
from backend.app.services.fact_check_service import FactCheckService

from backend.app.random_forest.predictor import RandomForestPredictor
from backend.app.roberta.predictor import RobertaPredictor
from backend.app.ml.fusion.fusion_engine import FusionEngine
from backend.app.analyzers.html_analyzer import HtmlAnalyzer


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:
        return {"error": str(exc)}


class PhishingService:

    @staticmethod
    def analyze(url: str):

        # ── Caché ──────────────────────────────────────────
        cached = url_cache.get(url)
        if cached:
            return {**cached, "cached": True}

        t0 = time.time()

        # ── URL features (CPU, instantáneo) ────────────────
        url_features = extract_url_features(url)

        # ── Grupo 1: I/O paralelo ──────────────────────────
        # domain_info · html_analysis · vt · sb · fc · roberta
        # (todos independientes entre sí)

        io_tasks = {
            "domain_info":        (get_domain_info,            url),
            "html_analysis":      (HtmlAnalyzer.analyze,       url),
            "vt_result":          (VirusTotalService.analyze,  url),
            "sb_result":          (SafeBrowsingService.analyze, url),
            "fc_result":          (FactCheckService.analyze,   url),
            "roberta_prediction": (RobertaPredictor.predict,   url),
        }

        group1 = {}
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {
                ex.submit(_safe, fn, arg): key
                for key, (fn, arg) in io_tasks.items()
            }
            for future in as_completed(futures):
                group1[futures[future]] = future.result()

        domain_info        = group1["domain_info"]
        html_analysis      = group1["html_analysis"]
        vt_result          = group1["vt_result"]
        sb_result          = group1["sb_result"]
        fc_result          = group1["fc_result"]
        roberta_prediction = group1["roberta_prediction"]

        # ── Grupo 2: depende de html_analysis ──────────────
        rf_features   = FeatureMapper.map(url, url_features, html_analysis)
        rf_prediction = _safe(RandomForestPredictor.predict, rf_features)

        # ── Secuencial: dependen de todo lo anterior ────────

        fusion_result = FusionEngine.combine(
            rf_prediction,
            roberta_prediction
        )

        risk_result = RiskEngine.calculate(
            url_features,
            domain_info,
            html_analysis,
            vt_result,
            sb_result,
            fc_result,
            fusion_result
        )

        # ── Respuesta ───────────────────────────────────────

        result = {
            "url": url,
            "cached": False,
            "analysis_time_ms": round((time.time() - t0) * 1000),

            "risk_assessment":       risk_result,

            "machine_learning": {
                "fusion":        fusion_result,
                "random_forest": rf_prediction,
                "roberta":       roberta_prediction,
            },

            "html_analysis":         html_analysis,
            "url_features":          url_features,
            "domain_info":           domain_info,
            "virustotal":            vt_result,
            "safe_browsing":         sb_result,
            "fact_check":            fc_result,
        }

        url_cache.set(url, result)
        return result
