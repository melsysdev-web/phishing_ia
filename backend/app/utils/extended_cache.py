"""
Extended URL cache with two layers:
- Fast (in-memory): 10 min TTL, 500 entries (current behavior)
- Warm (SQLite): 30 days TTL, unlimited entries (cost savings)

When fast cache misses, tries warm cache before making API calls.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path

from backend.app.core.paths import get_models_dir

_FAST_TTL = 600          # 10 minutes
_WARM_TTL = 2592000      # 30 days
_MAX_FAST_ENTRIES = 500

_fast_cache: dict = {}
_lock = threading.Lock()

# SQLite database for warm cache
_db_path = None


def _get_db_path():
    """Get path to SQLite cache database."""
    global _db_path
    if _db_path is None:
        models_dir = get_models_dir()
        _db_path = Path(models_dir).parent / "url_cache.db"
    return _db_path


def _init_db():
    """Initialize SQLite database if it doesn't exist."""
    db_path = _get_db_path()
    if db_path.exists():
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS url_cache (
                url TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                timestamp REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON url_cache(expires_at)
        """)
        conn.commit()
        conn.close()
    except sqlite3.Error:
        # Silently fail if DB can't be created (e.g., permission issues)
        pass


def get(url: str) -> dict | None:
    """
    Get cached result from fast or warm cache.
    Returns None if not found or expired.
    """
    with _lock:
        # Try fast cache first
        entry = _fast_cache.get(url)
        if entry:
            if time.time() - entry["ts"] < _FAST_TTL:
                return entry["data"]
            else:
                del _fast_cache[url]

    # Try warm cache
    result = _get_warm(url)
    if result:
        # Restore to fast cache
        with _lock:
            if len(_fast_cache) >= _MAX_FAST_ENTRIES:
                oldest = min(
                    _fast_cache,
                    key=lambda k: _fast_cache[k]["ts"]
                )
                del _fast_cache[oldest]
            _fast_cache[url] = {"ts": time.time(), "data": result}
        return result

    return None


def set(url: str, data: dict) -> None:
    """Store result in both fast and warm caches."""
    with _lock:
        # Fast cache
        if len(_fast_cache) >= _MAX_FAST_ENTRIES:
            oldest = min(
                _fast_cache,
                key=lambda k: _fast_cache[k]["ts"]
            )
            del _fast_cache[oldest]
        _fast_cache[url] = {"ts": time.time(), "data": data}

    # Warm cache
    _set_warm(url, data)


def _get_warm(url: str) -> dict | None:
    """Get from SQLite warm cache."""
    try:
        db_path = _get_db_path()
        if not db_path.exists():
            return None

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        now = time.time()
        cursor.execute("""
            SELECT data FROM url_cache
            WHERE url = ? AND expires_at > ?
        """, (url, now))

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None

    except (sqlite3.Error, json.JSONDecodeError):
        return None


def _set_warm(url: str, data: dict) -> None:
    """Store in SQLite warm cache."""
    try:
        _init_db()
        db_path = _get_db_path()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        now = time.time()
        expires_at = now + _WARM_TTL

        cursor.execute("""
            INSERT OR REPLACE INTO url_cache (url, data, timestamp, expires_at)
            VALUES (?, ?, ?, ?)
        """, (url, json.dumps(data), now, expires_at))

        conn.commit()
        conn.close()

    except sqlite3.Error:
        # Silently fail if DB write fails
        pass


def stats() -> dict:
    """Return cache statistics from both layers."""
    with _lock:
        now = time.time()
        fast_valid = sum(
            1 for e in _fast_cache.values()
            if now - e["ts"] < _FAST_TTL
        )

    warm_count = 0
    try:
        db_path = _get_db_path()
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM url_cache WHERE expires_at > ?",
                (time.time(),)
            )
            warm_count = cursor.fetchone()[0]
            conn.close()
    except sqlite3.Error:
        pass

    return {
        "fast_entries": len(_fast_cache),
        "fast_valid": fast_valid,
        "fast_ttl_seconds": _FAST_TTL,
        "fast_max_size": _MAX_FAST_ENTRIES,
        "warm_entries": warm_count,
        "warm_ttl_seconds": _WARM_TTL,
    }


def clear() -> int:
    """Clear all caches (fast + warm)."""
    with _lock:
        fast_count = len(_fast_cache)
        _fast_cache.clear()

    try:
        db_path = _get_db_path()
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM url_cache")
            conn.commit()
            conn.close()
    except sqlite3.Error:
        pass

    return fast_count


def cleanup_expired() -> int:
    """Remove expired entries from warm cache (can be run as cron job)."""
    try:
        db_path = _get_db_path()
        if not db_path.exists():
            return 0

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        now = time.time()
        cursor.execute("DELETE FROM url_cache WHERE expires_at <= ?", (now,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted

    except sqlite3.Error:
        return 0
