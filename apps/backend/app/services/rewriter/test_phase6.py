import asyncio
from app.services.rewriter.lexicon import LexiconProcessor
from app.services.rewriter.rate_limiter import user_rate_limiter
from app.services.rewriter.engine import rewriter_engine

def test_dialect_expansion():
    print("--- Testing Dialect Expansion Instructions ---")
    
    # Singapore English (en-SG)
    instructions_sg = LexiconProcessor.get_dialect_instructions("en-SG")
    assert "take MC" in instructions_sg
    assert "chop" in instructions_sg
    assert "kiasu" in instructions_sg
    print("en-SG instructions test: PASSED")

    # Australian English (en-AU)
    instructions_au = LexiconProcessor.get_dialect_instructions("en-AU")
    assert "this arvo" in instructions_au
    assert "uni" in instructions_au
    assert "no worries" in instructions_au
    assert "a fortnight" in instructions_au
    print("en-AU instructions test: PASSED")

    # British English (en-GB)
    instructions_gb = LexiconProcessor.get_dialect_instructions("en-GB")
    assert "analyse" in instructions_gb
    assert "flat" in instructions_gb
    assert "colour" in instructions_gb
    assert "lift" in instructions_gb
    print("en-GB instructions test: PASSED")


def test_rate_limiter():
    print("\n--- Testing Tier-Based Rate Limiting ---")
    client_id = "test_client_123"
    
    # Free tier test: capacity = 3, refill = 0.05
    # Acquire 3 tokens immediately
    for i in range(3):
        is_limited, wait_time = user_rate_limiter.is_rate_limited(client_id, "Free")
        assert not is_limited
        print(f"Free tier token {i+1} acquired successfully.")
        
    # The 4th should be limited
    is_limited, wait_time = user_rate_limiter.is_rate_limited(client_id, "Free")
    assert is_limited
    assert wait_time > 0
    print(f"Free tier 4th token rate limited correctly (must wait {wait_time:.2f}s).")

    # Premium tier test
    premium_client = "premium_client_123"
    for i in range(10):
        is_limited, wait_time = user_rate_limiter.is_rate_limited(premium_client, "Premium")
        assert not is_limited
    print("Premium tier handled 10 rapid-fire requests successfully without limiting: PASSED")


async def test_streaming_generator():
    print("\n--- Testing Streaming Rewrite Generator ---")
    test_text = "Building a startup is a long journey. Many developers want to write clean code all the time."
    events_received = []
    
    # We run the stream
    async for event in rewriter_engine.rewrite_stream(test_text, tone="human-like", dialect="en-IN", max_retries=1):
        events_received.append(event)
        print(f"Event: {event['event']} | Data preview: {str(event['data'])[:60]}")
        
    # Verify we got status events, text chunks, and a final result
    event_names = [e["event"] for e in events_received]
    assert "status" in event_names
    assert "text_chunk" in event_names
    assert "result" in event_names
    
    result_event = next(e for e in events_received if e["event"] == "result")
    assert "rewritten" in result_event["data"]
    assert "score" in result_event["data"]
    assert "nli_score" in result_event["data"]
    print("Streaming Generator Test: PASSED")


def main():
    test_dialect_expansion()
    test_rate_limiter()
    asyncio.run(test_streaming_generator())
    print("\nALL PHASE 6 BACKEND TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
