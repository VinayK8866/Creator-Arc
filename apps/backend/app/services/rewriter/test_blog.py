import asyncio
import sys
import json
from app.core.database import SessionLocal
from app.services.blog_service import blog_service
from app.models.platform_metadata import PlatformMetadata
from app.models.blog_post import BlogPost


async def test_factual_base():
    print("\n--- Testing Module 1: Factual Expansion Layer ---")
    db = SessionLocal()
    try:
        topic = "Decentralized task scheduling with Celery in Python"
        platform = "medium"
        
        result = blog_service.generate_factual_base(db, topic, platform)
        print("Generated Factual Base:")
        print(json.dumps(result, indent=2))
        
        assert "target_platform" in result
        assert "suggested_title" in result
        assert "seo_keywords" in result
        assert "content_chunks" in result
        assert len(result["content_chunks"]) >= 2
        
        for idx, chunk in enumerate(result["content_chunks"]):
            assert "heading" in chunk
            assert "raw_factual_bullet_points" in chunk
            assert isinstance(chunk["raw_factual_bullet_points"], list)
            assert len(chunk["raw_factual_bullet_points"]) >= 1

        print("Factual Base Generation: PASS")
    finally:
        db.close()


async def test_blog_stream():
    print("\n--- Testing Module 2 & 3: Sequential Feeder SSE Pipeline ---")
    db = SessionLocal()
    try:
        topic = "Scaling UPI backend systems under peak loads"
        platform = "reddit"
        tone = "human-like"

        print("Starting live async blog post generation stream...")
        completed_received = False
        chunks_count = 0
        status_msgs = []

        async for event_message in blog_service.generate_blog_stream(db, topic, platform, tone):
            # Parse SSE formatted lines
            lines = event_message.strip().split("\n")
            event_type = "message"
            event_data = ""
            for line in lines:
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    event_data = line.replace("data:", "").strip()
            
            if not event_data:
                continue

            parsed_data = json.loads(event_data)
            
            if event_type == "status":
                status_msgs.append(parsed_data["message"])
                print(f"[STATUS] {parsed_data['message']} (Progress: {parsed_data.get('progress') or 0}%)")
            elif event_type == "factual_base":
                print(f"[FACTUAL BASE] Title: {parsed_data['suggested_title']}, Chunks count: {parsed_data['chunks_count']}")
            elif event_type == "chunk_completed":
                chunks_count += 1
                print(f"[CHUNK COMPLETED] Index: {parsed_data['chunk_index']}, Heading: {parsed_data['heading']}")
                print(f"  -> AI Likelihood: {parsed_data['score']:.2%}, NLI Score: {parsed_data['nli_score']:.2%}")
            elif event_type == "completed":
                completed_received = True
                print("\n[COMPLETED SUCCESS] Full Article Generated:")
                print(parsed_data["full_content"][:300] + "...\n")
            elif event_type == "error":
                print(f"[ERROR] {parsed_data['detail']}")
                raise Exception(parsed_data["detail"])

        assert chunks_count > 0, "No chunks were processed in sequential feeder"
        assert completed_received, "Stream completed without a completion payload"
        print("Sequential Feeder SSE Stream: PASS")
    finally:
        db.close()


async def main():
    try:
        await test_factual_base()
        await test_blog_stream()
        print("\nAll Blog Architect tests passed successfully!")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\nAssertion error: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during test execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
