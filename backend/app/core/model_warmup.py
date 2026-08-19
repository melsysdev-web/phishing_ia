"""
Optional model warmup strategy based on deployment environment.

On Render's free tier (512MB), loading all models (~500MB each) at startup
causes OOM. Strategy:
- ENVIRONMENT=development: Eager loading (warmup_models preloads)
- ENVIRONMENT=production: Pure lazy loading (no warmup, load on first request)
"""
import logging

from backend.app.core.config import settings

logger = logging.getLogger("phishing_api")


def warmup_models():
    """Skip warmup in production to avoid OOM on Render free tier (512MB).

    In development, pre-load models. In production, rely on lazy loading
    via @lru_cache in model loaders — first request takes ~30-60s as models
    download and initialize, but subsequent requests are cached.
    """
    environment = settings.environment.lower()

    if environment == "production":
        logger.info(
            "⚠️  Production mode: using lazy model loading. "
            "First request will download+initialize models (~30-60s)."
        )
        return True

    logger.info("🔄 Development mode: warming up ML models during startup...")

    loaded_count = 0
    failed_models = []

    try:
        logger.info("  → Loading Random Forest...")
        from backend.app.random_forest.predictor import RandomForestPredictor
        RandomForestPredictor.predict({})
        logger.info("  ✓ Random Forest loaded")
        loaded_count += 1
    except Exception as e:
        logger.warning(f"  ✗ Random Forest failed: {e}")
        failed_models.append("Random Forest")

    try:
        logger.info("  → Loading RoBERTa URL classifier...")
        from backend.app.roberta.predictor import RobertaPredictor
        RobertaPredictor.predict("")
        logger.info("  ✓ RoBERTa URL classifier loaded")
        loaded_count += 1
    except Exception as e:
        logger.warning(f"  ✗ RoBERTa URL classifier failed: {e}")
        failed_models.append("RoBERTa URL")

    try:
        logger.info("  → Loading content classifier...")
        from backend.app.roberta.content_classifier_service import ContentClassifierService
        ContentClassifierService.classify("")
        logger.info("  ✓ Content classifier loaded")
        loaded_count += 1
    except Exception as e:
        logger.warning(f"  ✗ Content classifier failed: {e}")
        failed_models.append("Content classifier")

    if loaded_count == 3:
        logger.info("✅ All 3 ML models warmed up successfully")
    elif loaded_count > 0:
        missing = ", ".join(failed_models)
        logger.warning(f"⚠️  Warmup partial: {loaded_count}/3. Missing: {missing}")
    else:
        logger.warning("⚠️  All models failed to load during warmup")

    return True
