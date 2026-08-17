import threading
import time

_TTL = 3600       # segundos (1 hora) — datos de registro WHOIS son estables
_MAX_SIZE = 1000  # dominios máximos en caché

_store: dict = {}
_lock = threading.Lock()


def get(domain: str) -> dict | None:
    with _lock:
        entry = _store.get(domain)
        if not entry:
            return None
        if time.time() - entry["ts"] > _TTL:
            del _store[domain]
            return None
        return entry["data"]


def set(domain: str, data: dict) -> None:
    with _lock:
        if len(_store) >= _MAX_SIZE:
            oldest_domain = min(_store, key=lambda k: _store[k]["ts"])
            del _store[oldest_domain]
        _store[domain] = {"ts": time.time(), "data": data}


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
