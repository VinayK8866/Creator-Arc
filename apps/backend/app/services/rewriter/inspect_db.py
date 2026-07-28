from app.core.database import SessionLocal
from app.models.blog_post import BlogPost
import json

db = SessionLocal()
try:
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).limit(3).all()
    print(f"Total posts found: {len(posts)}")
    for i, post in enumerate(posts):
        print(f"\n--- Post {i+1} ---")
        print(f"ID: {post.id}")
        print(f"Topic: {post.topic}")
        print(f"Platform: {post.platform}")
        print(f"Suggested Title: {post.suggested_title}")
        print(f"Status: {post.status}")
        
        # Check humanized content
        content = post.humanized_content
        print(f"Humanized Content Length: {len(content) if content else 'None/Empty'}")
        if content:
            print("Preview Content (first 150 chars):")
            print(repr(content[:150]))
            
        # Check chunks
        chunks = post.content_chunks
        print(f"Content Chunks Count: {len(chunks) if chunks else 'None/Empty'}")
        if chunks:
            print("First Chunk details:")
            print(f"  Heading: {chunks[0].get('heading')}")
            print(f"  Text Length: {len(chunks[0].get('humanized_text', ''))}")
            print(f"  Score: {chunks[0].get('score')}")
finally:
    db.close()
