"""Bounded process-local query-vector cache, not an answer cache."""
from collections import OrderedDict
import hashlib
import hmac
import json
import secrets
from threading import RLock
from time import monotonic
from hybrid_retrieval import unit


class QueryVectorCache:
    def __init__(self, *, capacity=256, ttl=300, enabled=False, clock=monotonic):
        if type(capacity) is not int or not 1 <= capacity <= 1024 or not 1 <= ttl <= 600:
            raise ValueError('invalid cache bounds')
        self.capacity, self.ttl, self.enabled = capacity, ttl, enabled
        self._clock, self._key = clock, secrets.token_bytes(32)
        self._entries, self._lock = OrderedDict(), RLock()

    def _lookup_key(self, workspace, revision, encoder, query, cacheable):
        if not self.enabled or cacheable is not True:
            return None
        if not all(isinstance(x, str) and x.strip() for x in (workspace, revision, encoder, query)):
            return None
        if any(len(x) > 256 for x in (workspace, revision, encoder)) or len(query.encode('utf-8')) > 4096:
            return None
        # Exact content only. Do not normalize potentially distinct questions.
        payload = json.dumps([workspace, revision, encoder, query], ensure_ascii=False).encode('utf-8')
        return hmac.new(self._key, payload, hashlib.sha256).digest()

    def get(self, *, workspace, revision, encoder, query, cacheable=False):
        key = self._lookup_key(workspace, revision, encoder, query, cacheable)
        if key is None:
            return None
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires, vector = entry
            if expires <= self._clock():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return vector

    def put(self, *, workspace, revision, encoder, query, vector, cacheable=False):
        key = self._lookup_key(workspace, revision, encoder, query, cacheable)
        if key is None:
            return False
        normalized = unit(vector)
        with self._lock:
            self._entries[key] = (self._clock() + self.ttl, normalized)
            self._entries.move_to_end(key)
            while len(self._entries) > self.capacity:
                self._entries.popitem(last=False)
        return True

    def clear(self):
        with self._lock:
            self._entries.clear()
