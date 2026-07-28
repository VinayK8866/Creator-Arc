import time

# Centralized list of prioritized Gemini models for fallback sequences
FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3.1-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]


class APIGovernor:
    _last_call_time = 0.0
    _min_delay = 4.2  # 15 RPM is 1 request per 4s. 4.2s is a safe buffer.

    @classmethod
    def pace(cls):
        now = time.time()
        elapsed = now - cls._last_call_time
        if elapsed < cls._min_delay:
            sleep_needed = cls._min_delay - elapsed
            print(f"[API Governor] Pacing requests. Sleeping {sleep_needed:.2f}s to avoid rate limits...")
            time.sleep(sleep_needed)
        cls._last_call_time = time.time()
