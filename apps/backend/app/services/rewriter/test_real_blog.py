import asyncio
import sys
import json
from app.core.config import settings

# Do NOT clear GEMINI_API_KEY to use the real API
print(f"API Key present: {bool(settings.GEMINI_API_KEY)}")

from app.core.database import SessionLocal
from app.services.blog_service import blog_service
from app.models.blog_post import BlogPost


async def run_real_test():
    db = SessionLocal()
    try:
        topic = "Healthy sleeping habits"
        platform = "medium"
        tone = "human-like"

        print("Executing real stream generation...")
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
                print(f"[{event_type.upper()}] {parsed.get('message') or parsed.get('suggested_title') or parsed.get('heading') or parsed.get('detail') or 'Data'}")

        print("\nChecking database post status...")
        post = db.query(BlogPost).filter(BlogPost.topic == topic).order_by(BlogPost.created_at.desc()).first()
        if post:
            print(f"ID: {post.id}")
            print(f"Status: {post.status}")
            print(f"Humanized Content Length: {len(post.humanized_content) if post.humanized_content else 0}")
            print(f"Chunks Count: {len(post.content_chunks) if post.content_chunks else 0}")
        else:
            print("Error: Post not found in database!")
            
    except Exception as e:
        print(f"Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_real_test())
