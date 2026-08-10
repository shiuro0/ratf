from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from typing import Any

import redis

from .config import Settings


class Storage:
    backend_name = "unknown"

    def get_json(self, key: str) -> Any | None:  # pragma: no cover
        raise NotImplementedError

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:  # pragma: no cover
        raise NotImplementedError

    def exists(self, key: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    def claim_json(self, key: str, value: Any, ttl_seconds: int) -> bool:  # pragma: no cover
        """Atomically create a key if it does not exist."""
        raise NotImplementedError

    def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:  # pragma: no cover
        raise NotImplementedError

    def clear(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def ping(self) -> bool:  # pragma: no cover
        raise NotImplementedError


class RedisStorage(Storage):
    backend_name = "redis"

    def __init__(self, url: str):
        # Do not make module/application construction depend on a single Redis
        # ping. The Docker entrypoint performs a bounded readiness wait before
        # Gunicorn starts, while health checks continue to report dependency
        # loss after startup. This prevents a transient Redis/DNS race from
        # turning into a Gunicorn worker restart loop.
        self.client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

    def get_json(self, key: str) -> Any | None:
        raw = self.client.get(key)
        return None if raw is None else json.loads(raw)

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        raw = json.dumps(value, default=str, separators=(",", ":"))
        if ttl_seconds:
            self.client.setex(key, ttl_seconds, raw)
        else:
            self.client.set(key, raw)

    def exists(self, key: str) -> bool:
        return bool(self.client.exists(key))

    def claim_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        raw = json.dumps(value, default=str, separators=(",", ":"))
        return bool(self.client.set(key, raw, nx=True, ex=max(int(ttl_seconds), 1)))

    def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        # Lua keeps increment and initial expiry atomic. Existing keys retain the
        # original window rather than receiving a sliding expiry on every request.
        script = """
        local value = redis.call('INCR', KEYS[1])
        if value == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
        return value
        """
        return int(self.client.eval(script, 1, key, max(int(ttl_seconds), 1)))

    def clear(self) -> None:
        self.client.flushdb()

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except redis.RedisError:
            return False


class MemoryStorage(Storage):
    backend_name = "memory"

    def __init__(self):
        self.data: dict[str, tuple[Any, float | None]] = {}
        self.counters: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
        self._lock = threading.RLock()

    @staticmethod
    def _expired(expiry: float | None) -> bool:
        return expiry is not None and time.time() > expiry

    def get_json(self, key: str) -> Any | None:
        with self._lock:
            item = self.data.get(key)
            if not item:
                return None
            value, expiry = item
            if self._expired(expiry):
                self.data.pop(key, None)
                return None
            return value

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        with self._lock:
            expiry = time.time() + ttl_seconds if ttl_seconds else None
            self.data[key] = (value, expiry)

    def exists(self, key: str) -> bool:
        return self.get_json(key) is not None

    def claim_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        with self._lock:
            if self.get_json(key) is not None:
                return False
            self.set_json(key, value, ttl_seconds)
            return True

    def incr_with_ttl(self, key: str, ttl_seconds: int) -> int:
        with self._lock:
            value, expiry = self.counters.get(key, (0, 0.0))
            now = time.time()
            if expiry < now:
                value = 0
                expiry = now + ttl_seconds
            value += 1
            self.counters[key] = (value, expiry)
            return value

    def clear(self) -> None:
        with self._lock:
            self.data.clear()
            self.counters.clear()

    def ping(self) -> bool:
        return True


def create_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "memory":
        return MemoryStorage()
    storage = RedisStorage(settings.redis_url)
    # Preserve the explicitly requested development fallback without making
    # normal fail-closed startup depend on one immediate network round trip.
    if settings.allow_memory_fallback and not storage.ping():
        return MemoryStorage()
    return storage
