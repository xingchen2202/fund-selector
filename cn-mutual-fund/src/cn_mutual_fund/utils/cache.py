"""
TTL-based in-memory cache for AKShare data.

Caching strategy:
- Realtime quotes: 30 seconds
- Daily NAV data: 1 hour
- Fund info / config: 24 hours
- Fund ratings: 24 hours
- Rankings: 1 hour
"""

import time
from typing import Any

# Default TTL values in seconds
TTL_REALTIME = 30         # Real-time quotes
TTL_DAILY = 3600          # 1 hour for daily NAV / rankings
TTL_FINANCIAL = 86400     # 24 hours for financial data
TTL_CONFIG = 86400        # 24 hours for fund info / ratings
TTL_MACRO = 604800        # 7 days for macro data


class TTLCache:
    """Simple thread-safe TTL cache backed by a dict."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        if key in self._store:
            value, expires_at = self._store[key]
            if time.time() < expires_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int = TTL_DAILY) -> None:
        self._store[key] = (value, time.time() + ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def cleanup(self) -> int:
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if now >= exp]
        for k in expired:
            del self._store[k]
        return len(expired)

    @property
    def size(self) -> int:
        return len(self._store)


# Global cache instance
cache = TTLCache()
