"""
Pure lazy loading strategy for all deployments.

On Render's free tier (512MB), loading all models (~500MB each) at startup
causes OOM. Models load lazily via @lru_cache on first request, preventing
memory spikes during app initialization.
"""
import logging

logger = logging.getLogger("phishing_api")


def warmup_models():
    """Skip model loading on startup to avoid OOM on Render free tier (512MB).

    Models load lazily via @lru_cache on first request (~30-60s for cold start),
    then cache in memory for subsequent requests. This approach always works,
    regardless of environment variables or deployment configuration.
    """
    logger.info(
        "⚠️  Lazy loading enabled: models will load on first request (~30-60s). "
        "Subsequent requests will be fast."
    )
    return True
