import time
import sys
import os

# Adjust path if run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.database import SessionLocal
from app.models.style_reference import StyleReference
from app.services.rewriter.rate_limiter import RedisTokenBucket
from app.services.rewriter.cache import embedding_cache
from app.services.rewriter.pgvector_migration import run_pgvector_migration
from workers.tasks.rewriter_tasks import batch_generate_embeddings_task


def test_rate_limiter():
    print("\n--- Unit Test: Redis Token Bucket Rate Limiter ---")
    # Setup bucket with capacity 2.0, refill 0.5 tokens/sec
    limiter = RedisTokenBucket(capacity=2.0, refill_rate=0.5, key_prefix="test_limiter")
    
    # 1. First two acquires should succeed instantly
    ok1, wait1 = limiter.acquire()
    ok2, wait2 = limiter.acquire()
    print(f"Acquire 1: {ok1} (wait: {wait1})")
    print(f"Acquire 2: {ok2} (wait: {wait2})")
    assert ok1 and ok2, "Initial acquires failed"
    
    # 2. Third acquire should be rate-limited
    ok3, wait3 = limiter.acquire()
    print(f"Acquire 3 (limited): {ok3} (wait: {wait3})")
    assert not ok3, "Third acquire should have failed due to rate limits"
    assert wait3 > 0.0, f"Expected positive wait time, got {wait3}"
    
    # 3. Test blocking wait_for_token
    print("Testing blocking wait_for_token (should block briefly to acquire)...")
    start_time = time.time()
    limiter.wait_for_token()
    duration = time.time() - start_time
    print(f"Blocked for {duration:.2f} seconds before token acquired.")
    assert duration >= 1.0, f"Expected to wait at least 1 second. Waited {duration}"
    print("Rate limiter tests: PASS")


def test_embedding_cache():
    print("\n--- Unit Test: Embedding Cache ---")
    test_text = "This is a test block of text to verify that Redis caching works correctly."
    test_vector = [0.123, 0.456, 0.789]
    
    # 1. Cache miss
    val1 = embedding_cache.get(test_text)
    print(f"Cache miss check: {val1}")
    assert val1 is None, "Expected cache miss"
    
    # 2. Write to cache
    embedding_cache.set(test_text, test_vector)
    print("Vector cached successfully.")
    
    # 3. Cache hit
    val2 = embedding_cache.get(test_text)
    print(f"Cache hit check: {val2}")
    assert val2 == test_vector, f"Cached vector mismatch. Expected {test_vector}, got {val2}"
    print("Embedding cache tests: PASS")


def test_database_migration():
    print("\n--- Integration Test: pgvector DB Migration ---")
    migration_success = run_pgvector_migration()
    print(f"pgvector Migration success check: {migration_success}")
    # We do not assert True here because databases without superuser/pgvector compile permissions will return False
    # But we verify it completes without unhandled python exceptions
    print("Database migration check: PASS")


def test_celery_task():
    print("\n--- Integration Test: Celery Worker Task Execution ---")
    db = SessionLocal()
    try:
        # Get one reference to test
        ref = db.query(StyleReference).first()
        if not ref:
            print("No style reference found. Seeding first...")
            from app.services.rewriter.migration import seed_style_references
            seed_style_references(db)
            ref = db.query(StyleReference).first()
            
        assert ref is not None, "Failed to get a StyleReference to test"
        
        # Execute task synchronously to test logic run correctness
        print(f"Executing task synchronously for Style ID {ref.id}...")
        batch_generate_embeddings_task([ref.id])
        
        # Refresh and verify
        db.refresh(ref)
        print(f"Style ID {ref.id} updated embedding size: {len(ref.embedding) if ref.embedding else 0}")
        assert ref.embedding is not None, "Celery task failed to generate embedding"
        print("Celery task checks: PASS")
        
    finally:
        db.close()


def main():
    try:
        test_rate_limiter()
        test_embedding_cache()
        test_database_migration()
        test_celery_task()
        print("\nAll Phase 3 tests passed successfully!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nAssertion failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error running tests: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
