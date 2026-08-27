from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock


@dataclass
class CacheEntry:
    data: dict
    etag: str
    fetched_at: datetime
    expires_at: datetime

    @property
    def fresh(self):
        return datetime.now() < self.expires_at


class MemoryTtlCache:
    def __init__(self):
        self._entries = {}
        self._entries_lock = Lock()
        self._key_locks = {}

    def get(self, key):
        with self._entries_lock:
            return self._entries.get(key)

    def set(self, key, data, ttl_seconds, etag=""):
        now = datetime.now()
        entry = CacheEntry(
            data=data,
            etag=str(etag or ""),
            fetched_at=now,
            expires_at=now + timedelta(seconds=max(int(ttl_seconds), 1)),
        )
        with self._entries_lock:
            self._entries[key] = entry
        return entry

    def touch(self, key, ttl_seconds):
        with self._entries_lock:
            entry = self._entries.get(key)
            if not entry:
                return None
            now = datetime.now()
            entry.fetched_at = now
            entry.expires_at = now + timedelta(
                seconds=max(int(ttl_seconds), 1)
            )
            return entry

    def lock_for(self, key):
        with self._entries_lock:
            if key not in self._key_locks:
                self._key_locks[key] = Lock()
            return self._key_locks[key]
