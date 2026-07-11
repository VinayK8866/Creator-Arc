import time
import redis
from app.core.config import settings


class RedisTokenBucket:
    def __init__(self, capacity: float = 5.0, refill_rate: float = 0.2, key_prefix: str = "gemini_limiter"):
        """
        capacity: Max tokens the bucket can hold.
        refill_rate: Tokens added per second (0.2 tokens/sec = 12 tokens/min = ~12 RPM safety).
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.key_prefix = key_prefix
        self.token_key = f"{key_prefix}:tokens"
        self.time_key = f"{key_prefix}:last_refill"
        
        # Local in-memory fallback if Redis is offline
        self._local_tokens = capacity
        self._local_last_refill = time.time()
        
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Basic test connection
            self.redis_client.ping()
            self.use_redis = True
            print("RateLimiter: Successfully connected to Redis.")
        except Exception as e:
            print(f"RateLimiter Warning: Redis connection failed ({str(e)}). Falling back to local in-memory bucket.")
            self.use_redis = False

    def _acquire_local(self) -> tuple[bool, float]:
        """In-memory rate limit check."""
        now = time.time()
        elapsed = now - self._local_last_refill
        
        # Refill tokens
        refilled = self._local_tokens + (elapsed * self.refill_rate)
        self._local_tokens = min(self.capacity, refilled)
        self._local_last_refill = now
        
        if self._local_tokens >= 1.0:
            self._local_tokens -= 1.0
            return True, 0.0
            
        # Calculate time needed to get 1 token
        wait_time = (1.0 - self._local_tokens) / self.refill_rate
        return False, wait_time

    def acquire(self) -> tuple[bool, float]:
        """Try to acquire a token from the bucket.
        Returns:
          (success: bool, wait_time: float)
          If success is True, token was acquired and request can proceed.
          If success is False, wait_time specifies seconds to sleep before retrying.
        """
        if not self.use_redis:
            return self._acquire_local()
            
        try:
            # We run a simple pipeline to check tokens to avoid race conditions
            now = time.time()
            
            # Fetch current values
            pipe = self.redis_client.pipeline()
            pipe.get(self.token_key)
            pipe.get(self.time_key)
            tokens_val, last_refill_val = pipe.execute()
            
            # Initialize bucket if keys don't exist
            tokens = float(tokens_val) if tokens_val is not None else self.capacity
            last_refill = float(last_refill_val) if last_refill_val is not None else now
            
            # Refill calculation
            elapsed = now - last_refill
            refilled = tokens + (elapsed * self.refill_rate)
            tokens = min(self.capacity, refilled)
            
            if tokens >= 1.0:
                tokens -= 1.0
                
                # Write back updated values
                pipe = self.redis_client.pipeline()
                pipe.set(self.token_key, tokens)
                pipe.set(self.time_key, now)
                pipe.execute()
                return True, 0.0
            else:
                # Calculate wait time based on current token deficit
                wait_time = (1.0 - tokens) / self.refill_rate
                return False, wait_time
                
        except Exception as e:
            print(f"RateLimiter: Redis transaction error ({str(e)}). Falling back to local in-memory check.")
            return self._acquire_local()

    def wait_for_token(self):
        """Blocks thread execution until a token becomes available."""
        while True:
            acquired, wait_time = self.acquire()
            if acquired:
                return
            print(f"RateLimiter: Limit reached. Blocking for {wait_time:.2f} seconds...")
            time.sleep(wait_time)


# Global rate limiter instance (configured to ~12 requests per minute safety limit)
api_rate_limiter = RedisTokenBucket(capacity=4.0, refill_rate=0.20)


class UserTierRateLimiter:
    def __init__(self):
        # Cache of local token buckets if Redis is offline
        self.local_buckets = {}

    def is_rate_limited(self, identifier: str, tier: str) -> tuple[bool, float]:
        """
        Check if the identifier is rate limited for the given tier.
        Returns (is_limited, wait_time)
        """
        tier_clean = tier.lower().strip()
        # Determine capacity & refill rate based on tier
        if tier_clean == "premium":
            capacity = 20.0
            refill_rate = 0.33  # ~20 RPM
        else:
            capacity = 3.0
            refill_rate = 0.05  # ~3 RPM (strict free tier)

        key_prefix = f"user_limiter:{tier_clean}:{identifier}"
        
        # Check cache or initialize
        if key_prefix not in self.local_buckets:
            self.local_buckets[key_prefix] = RedisTokenBucket(
                capacity=capacity,
                refill_rate=refill_rate,
                key_prefix=key_prefix
            )
            
        bucket = self.local_buckets[key_prefix]
        # Dynamically update in case limits change
        bucket.capacity = capacity
        bucket.refill_rate = refill_rate
        
        acquired, wait_time = bucket.acquire()
        return not acquired, wait_time


# Global instance of user tier rate limiter
user_rate_limiter = UserTierRateLimiter()

