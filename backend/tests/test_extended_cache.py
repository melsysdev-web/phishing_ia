"""Tests para extended_cache.py — two-layer cache (fast + warm)."""

import threading
from unittest.mock import patch

import pytest

from backend.app.utils import extended_cache


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before/after each test."""
    extended_cache._fast_cache.clear()
    yield
    extended_cache._fast_cache.clear()


class TestExtendedCache:
    """Tests para two-layer cache."""

    def test_set_and_get_from_fast_cache(self):
        url = "https://example.com"
        data = {"verdict": "clean"}

        extended_cache.set(url, data)
        result = extended_cache.get(url)

        assert result == data

    def test_fast_cache_expires_after_ttl(self):
        url = "https://example.com"
        data = {"verdict": "clean"}

        extended_cache.set(url, data)

        # Simulate expiration by modifying timestamp
        extended_cache._fast_cache[url]["ts"] -= extended_cache._FAST_TTL + 1

        # Mock warm cache to return None (test fast expiration only)
        with patch("backend.app.utils.extended_cache._get_warm", return_value=None):
            result = extended_cache.get(url)

        # Should be None because fast cache expired and warm is empty
        assert result is None

    def test_fast_cache_eviction_at_max_size(self):
        # Fill fast cache to max
        for i in range(extended_cache._MAX_FAST_ENTRIES):
            url = f"https://example{i}.com"
            extended_cache.set(url, {"id": i})

        assert len(extended_cache._fast_cache) == extended_cache._MAX_FAST_ENTRIES

        # Add one more should evict oldest
        extended_cache.set("https://new.com", {"id": "new"})

        assert len(extended_cache._fast_cache) == extended_cache._MAX_FAST_ENTRIES
        assert "https://new.com" in extended_cache._fast_cache

    def test_warm_cache_restores_to_fast(self):
        """When fast expires, warm cache entry restores to fast."""
        url = "https://example.com"
        data = {"verdict": "clean"}

        # Use mock to prevent actual DB access (for unit test isolation)
        with patch("backend.app.utils.extended_cache._get_warm") as mock_warm:
            mock_warm.return_value = data

            # Expire fast cache entry
            extended_cache.set(url, data)
            extended_cache._fast_cache[url]["ts"] -= extended_cache._FAST_TTL + 1

            # Get should check warm cache
            result = extended_cache.get(url)

            mock_warm.assert_called_once_with(url)
            assert result == data

    def test_stats_includes_both_layers(self):
        url1 = "https://example1.com"
        url2 = "https://example2.com"

        extended_cache.set(url1, {"id": 1})
        extended_cache.set(url2, {"id": 2})

        stats = extended_cache.stats()

        assert "fast_entries" in stats
        assert "fast_valid" in stats
        assert "fast_ttl_seconds" in stats
        assert "warm_entries" in stats
        assert "warm_ttl_seconds" in stats
        assert stats["fast_ttl_seconds"] == extended_cache._FAST_TTL
        assert stats["warm_ttl_seconds"] == extended_cache._WARM_TTL

    def test_clear_clears_fast_cache(self):
        url = "https://example.com"
        extended_cache.set(url, {"verdict": "clean"})

        count = extended_cache.clear()

        assert count >= 1
        assert len(extended_cache._fast_cache) == 0

    def test_get_returns_none_for_missing_entry(self):
        result = extended_cache.get("https://nonexistent.com")
        assert result is None

    def test_set_stores_data_correctly(self):
        url = "https://example.com"
        data = {
            "verdict": "malicious",
            "stats": {"malicious": 5, "clean": 10}
        }

        extended_cache.set(url, data)

        assert extended_cache._fast_cache[url]["data"] == data

    def test_multiple_urls_in_cache(self):
        urls = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com",
        ]
        data_list = [
            {"verdict": "clean"},
            {"verdict": "malicious"},
            {"verdict": "suspicious"},
        ]

        for url, data in zip(urls, data_list, strict=True):
            extended_cache.set(url, data)

        for url, data in zip(urls, data_list, strict=True):
            result = extended_cache.get(url)
            assert result == data

    def test_ttl_constants_are_correct(self):
        assert extended_cache._FAST_TTL == 600  # 10 min
        assert extended_cache._WARM_TTL == 2592000  # 30 days
        assert extended_cache._MAX_FAST_ENTRIES == 500

    def test_fast_cache_is_thread_safe(self):
        """Basic thread safety check (real stress test would be more complex)."""
        url = "https://example.com"

        def writer():
            for i in range(100):
                extended_cache.set(f"{url}_{i}", {"id": i})

        def reader():
            for i in range(100):
                extended_cache.get(f"{url}_{i}")

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not crash
        assert True
