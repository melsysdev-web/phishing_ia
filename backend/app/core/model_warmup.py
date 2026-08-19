"""
Model warmup on application startup to prevent OOM errors on Render.

Pre-loads all ML models exactly once during app startup, before handling
any requests. This prevents concurrent model loading which causes memory spikes.
"""
import logging

logger = logging.getLogger("phishing_api")


def warmup_models():
    """Pre-load all ML models sequentially during startup.

    This must run ONCE before any requests arrive. Models are cached via
    @lru_cache, so subsequent calls return instantly from memory.

    Loads in this order (fastest to slowest):
    1. Random Forest (small pickle file)
    2. RoBERTa URL classifier (larger transformer model)
    3. RoBERTa content classifier (larger transformer model)
    """
    logger.info("🔄 Warming up ML models...")

    try:
        # 1. Random Forest — fast, small file
        logger.info("  → Loading Random Forest...")
        from backend.app.random_forest.predictor import RandomForestPredictor
        RandomForestPredictor.predict({})  # Trigger lazy load via dummy call
        logger.info("  ✓ Random Forest loaded")

        # 2. RoBERTa URL classifier — medium, ~500MB
        logger.info("  → Loading RoBERTa URL classifier...")
        from backend.app.roberta.predictor import RobertaPredictor
        RobertaPredictor.predict("")  # Trigger lazy load via dummy call
        logger.info("  ✓ RoBERTa URL classifier loaded")

        # 3. Content classifier — medium, ~500MB
        logger.info("  → Loading content classifier...")
        from backend.app.roberta.content_classifier_service import ContentClassifierService
        ContentClassifierService.classify("")  # Trigger lazy load via dummy call
        logger.info("  ✓ Content classifier loaded")

        logger.info("✅ All ML models warmed up successfully")
        return True

    except Exception as exc:
        # If warmup fails, log it but don't crash the app.
        # Models will load lazily on first request instead.
        logger.warning(f"⚠️  Model warmup failed (will retry on first request): {exc}")
        return False
