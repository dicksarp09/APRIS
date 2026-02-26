import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class MemoryStore:
    _instance = None
    _redis_client = None
    _use_redis = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                import redis

                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._use_redis = True
            except Exception:
                self._use_redis = False
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    def get(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        if self._use_redis and self._redis_client:
            try:
                data = self._redis_client.get(f"workflow:{workflow_id}")
                if data:
                    return json.loads(data)
            except Exception:
                pass
        return self._memory_cache.get(workflow_id)

    def set(self, workflow_id: str, state: Dict[str, Any], ttl: int = 3600) -> None:
        self._memory_cache[workflow_id] = state
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.setex(
                    f"workflow:{workflow_id}", ttl, json.dumps(state)
                )
            except Exception:
                pass

    def delete(self, workflow_id: str) -> None:
        self._memory_cache.pop(workflow_id, None)
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.delete(f"workflow:{workflow_id}")
            except Exception:
                pass

    def exists(self, workflow_id: str) -> bool:
        if self._use_redis and self._redis_client:
            try:
                return bool(self._redis_client.exists(f"workflow:{workflow_id}"))
            except Exception:
                pass
        return workflow_id in self._memory_cache

    def clear_expired(self) -> None:
        if not self._use_redis:
            self._memory_cache.clear()


def get_memory_store() -> MemoryStore:
    return MemoryStore()
