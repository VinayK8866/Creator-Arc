import hashlib
import json
import redis
from app.core.config import settings


class EmbeddingCache:
    def __init__(self, key_prefix: str = "embed_cache", expire_seconds: int = 86400):
        self.key_prefix = key_prefix
        self.expire_seconds = expire_seconds
        
        # Local in-memory dict fallback
        self._local_cache = {}
        
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            self.use_redis = True
            print("EmbeddingCache: Connected to Redis successfully.")
        except Exception as e:
            print(f"EmbeddingCache Warning: Redis connection failed ({str(e)}). Using local dictionary cache.")
            self.use_redis = False

    def _get_hash(self, text: str) -> str:
        """Compute MD5 hash of text to use as Redis key suffix."""
        cleaned = text.strip().lower()
        return hashlib.md5(cleaned.encode("utf-8")).hexdigest()

    def get(self, text: str) -> list or None:
        """Retrieve cached float list embedding from Redis or local cache."""
        cache_key = f"{self.key_prefix}:{self._get_hash(text)}"
        
        if not self.use_redis:
            return self._local_cache.get(cache_key)
            
        try:
            cached_val = self.redis_client.get(cache_key)
            if cached_val:
                return json.loads(cached_val)
        except Exception as e:
            print(f"EmbeddingCache Error: Failed to read from Redis ({str(e)}).")
            # Fallback to local
            return self._local_cache.get(cache_key)
            
        return None

    def set(self, text: str, embedding: list):
        """Cache the float list embedding."""
        if not embedding:
            return
            
        cache_key = f"{self.key_prefix}:{self._get_hash(text)}"
        
        # Save to local memory anyway
        self._local_cache[cache_key] = embedding
        
        if self.use_redis:
            try:
                serialized = json.dumps(embedding)
                self.redis_client.setex(cache_key, self.expire_seconds, serialized)
            except Exception as e:
                print(f"EmbeddingCache Error: Failed to write to Redis ({str(e)}).")


# Global embedding cache instance
embedding_cache = EmbeddingCache()
