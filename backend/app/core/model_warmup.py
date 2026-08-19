"""
Model warmup on application startup to prevent OOM errors on Render.

Pre-loads all ML models exactly once during app startup, before handling
any requests. This prevents concurrent model loading which causes memory spikes.

If models are missing (e.g., HuggingFace download failed in Dockerfile build),
they fall back to lazy loading on first request.
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

    If models are missing, they will be downloaded from HuggingFace Hub
    on first request (lazy loading fallback).
    """
    logger.info("🔄 Warming up ML models during startup...")

    loaded_count = 0
    failed_models = []

    # 1. Random Forest — fast, small file
    try:
        logger.info("  → Loading Random Forest...")
        from backend.app.random_forest.predictor import RandomForestPredictor
        RandomForestPredictor.predict({})
        logger.info("  ✓ Random Forest loaded")
        loaded_count += 1
    except Exception as e:
        logger.warning(f"  ✗ Random Forest failed: {e}")
        failed_models.append("Random Forest")

    # 2. RoBERTa URL classifier — medium, ~500MB
    try:
        logger.info("  → Loading RoBERTa URL classifier...")
        from backend.app.roberta.predictor import RobertaPredictor
        RobertaPredictor.predict("")
        logger.info("  ✓ RoBERTa URL classifier loaded")
        loaded_count += 1
    except Exception as e:
        logger.warning(f"  ✗ RoBERTa URL classifier failed: {e}")
        failed_models.append("RoBERTa URL")

    # 3. Content classifier — medium, ~500MB
    try:
        logger.info("  → Loading content classifier...")
        from backend.app.roberta.content_classifier_service import ContentClassifierService
        ContentClassifierService.classify("")
        logger.info("  ✓ Content classifier loaded")
        loaded_count += 1
    except Exception as e:
        logger.warning(f"  ✗ Content classifier failed: {e}")
        failed_models.append("Content classifier")

    # Summary
    if loaded_count == 3:
        logger.info("✅ All 3 ML models warmed up successfully")
        return True
    elif loaded_count > 0:
        logger.warning(f"⚠️  Warmup partial: {loaded_count}/3 loaded. Missing: {', '.join(failed_models)}")
        logger.warning("    Models will load lazily from HuggingFace Hub on first request")
        return True
    else:
        logger.warning("⚠️  All models failed to load during warmup")
        logger.warning("    Models will load lazily from HuggingFace Hub on first request")
        return True
