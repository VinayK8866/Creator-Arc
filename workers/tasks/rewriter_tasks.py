import time
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.style_reference import StyleReference
from app.services.rewriter.migration import get_embedding
from app.services.rewriter.rate_limiter import api_rate_limiter


@celery_app.task(name="workers.tasks.rewriter_tasks.batch_generate_embeddings_task")
def batch_generate_embeddings_task(style_ids: list):
    """Asynchronous background task to generate embeddings for a batch of style references."""
    print(f"Task: Starting batch embedding update for {len(style_ids)} style references...")
    db = SessionLocal()
    
    try:
        refs = db.query(StyleReference).filter(StyleReference.id.in_(style_ids)).all()
        
        for ref in refs:
            print(f"Task: Processing reference ID {ref.id}...")
            
            # Wait for rate-limiter token to respect API limits
            api_rate_limiter.wait_for_token()
            
            embedding = None
            for attempt in range(3):
                try:
                    embedding = get_embedding(ref.content)
                    break
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        print(f"Task: 429 quota hit. Sleeping 12s on attempt {attempt+1}/3...")
                        time.sleep(12)
                    else:
                        print(f"Task Error: {str(e)}")
                        break
            
            if embedding:
                ref.embedding = embedding
                db.commit()
                print(f"Task: Updated embedding for reference ID {ref.id} in DB.")
            else:
                print(f"Task Error: Failed to generate embedding for ID {ref.id}.")
                
            # Rate-limiting safety sleep
            time.sleep(2.2)
            
    except Exception as e:
        print(f"Task Error: Batch task execution failed. Error: {str(e)}")
    finally:
        db.close()
        
    print("Task: Batch embedding task finished.")
