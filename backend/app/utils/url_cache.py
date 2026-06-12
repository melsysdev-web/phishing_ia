import time
import threading

_TTL = 600       # segundos (10 minutos)
_MAX_SIZE = 500  # URLs máximas en caché

_store: dict = {}
_lock = threading.Lock()


def get(url: str) -> dict | None:
    with _lock:
        entry = _store.get(url)
        if not entry:
            return None
        if time.time() - entry["ts"] > _TTL:
            del _store[url]
            return None
        return entry["data"]


def set(url: str, data: dict) -> None:
    with _lock:
        if len(_store) >= _MAX_SIZE:
            oldest_url = min(_store, key=lambda k: _store[k]["ts"])
            del _store[oldest_url]
        _store[url] = {"ts": time.time(), "data": data}


def stats() -> dict:
    with _lock:
        now = time.time()
        valid = sum(
            1 for e in _store.values()
            if now - e["ts"] < _TTL
        )
        return {
            "entries": len(_store),
            "valid": valid,
            "ttl_seconds": _TTL,
            "max_size": _MAX_SIZE,
        }


def clear() -> int:
    with _lock:
        n = len(_store)
        _store.clear()
        return n
