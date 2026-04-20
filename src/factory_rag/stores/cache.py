import json

import redis


class QueryCache:
    def __init__(self, redis_url, ttl_seconds):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.client = None

    def _get_client(self):
        if self.client is None:
            self.client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        return self.client

    def ping(self):
        try:
            return bool(self._get_client().ping())
        except Exception:
            return False

    def get(self, key):
        try:
            value = self._get_client().get(key)
            if not value:
                return None
            return json.loads(value)
        except Exception:
            return None

    def set(self, key, value):
        try:
            payload = json.dumps(value)
            self._get_client().setex(key, self.ttl_seconds, payload)
        except Exception:
            return None
