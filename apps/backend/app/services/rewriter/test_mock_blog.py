import asyncio
import sys
import json
from app.core.config import settings

# Force mock mode by clearing GEMINI_API_KEY temporarily
settings.GEMINI_API_KEY = ""

from app.core.database import SessionLocal
from app.services.blog_service import blog_service
from app.models.blog_post import BlogPost
from app.models.platform_metadata import PlatformMetadata


async def run_mock_test():
    db = SessionLocal()
    try:
        # Ensure we have platform metadata seeded
        from app.services.rewriter.migration import seed_platform_metadata
        seed_platform_metadata(db)
        
        topic = "Mock Test: Python Celery workers"
        platform = "medium"
        tone = "human-like"

        print("Executing mock stream generation...")
        async for event_message in blog_service.generate_blog_stream(db, topic, platform, tone):
            # Parse SSE event
            lines = event_message.strip().split("\n")
            event_type = "message"
            event_data = ""
            for line in lines:
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    event_data = line.replace("data:", "").strip()
            
            if event_data:
                parsed = json.loads(event_data)
                print(f"[{event_type.upper()}] {parsed.get('message') or parsed.get('suggested_title') or parsed.get('heading') or 'Data'}")

        print("\nChecking database post status...")
        # Query the last post
        post = db.query(BlogPost).filter(BlogPost.topic == topic).order_by(BlogPost.created_at.desc()).first()
        if post:
            print(f"ID: {post.id}")
            print(f"Status: {post.status}")
            print(f"Humanized Content Length: {len(post.humanized_content) if post.humanized_content else 0}")
            print(f"Chunks Count: {len(post.content_chunks) if post.content_chunks else 0}")
            
            assert post.status == "completed", f"Status is not completed, got: {post.status}"
            assert len(post.humanized_content) > 0, "Humanized content is empty"
            print("Mock Test: SUCCESS!")
        else:
            print("Error: Post not found in database!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_mock_test())
