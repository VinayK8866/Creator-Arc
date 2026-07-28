from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import verify_master_password
from app.services.blog_service import blog_service
from app.models.platform_metadata import PlatformMetadata
from app.models.blog_post import BlogPost
from app.api.endpoints.text import enforce_rate_limit

router = APIRouter()


class BlogGenerateRequest(BaseModel):
    topic: str
    platform: str # medium, substack, reddit, quora, wordpress, squarespace, wix
    tone: str = "human-like"


class PlatformResponse(BaseModel):
    platform: str
    display_name: str
    storytelling_cadence: str
    heading_style: str
    layout_constraints: dict
    seo_optimizations: Optional[dict] = None

    class Config:
        from_attributes = True


@router.get("/platforms", response_model=List[PlatformResponse])
def get_platforms(db: Session = Depends(get_db), _auth: str = Depends(verify_master_password)):
    """Retrieve supported platforms, layout rules, andcadences from database."""
    platforms = db.query(PlatformMetadata).all()
    return platforms


@router.post("/generate-base")
def generate_factual_base(
    request: BlogGenerateRequest,
    fastapi_req: Request,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Module 1 Endpoint: Generate factual structured arguments for a topic at cold temperature."""
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    
    enforce_rate_limit(fastapi_req)

    # Check if platform is supported
    platform_exists = db.query(PlatformMetadata).filter(PlatformMetadata.platform == request.platform).first()
    if not platform_exists:
        raise HTTPException(status_code=400, detail=f"Platform '{request.platform}' is not supported.")

    try:
        factual_base = blog_service.generate_factual_base(db, request.topic, request.platform)
        return factual_base
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-stream")
async def generate_blog_stream(
    request: BlogGenerateRequest,
    fastapi_req: Request,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Module 2 Endpoint: progressive SSE stream executing chunk-by-chunk humanization,
    adversarial ONNX loop verification, and cross-encoder fact checking.
    """
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    enforce_rate_limit(fastapi_req)

    async def sse_generator():
        try:
            async for event_message in blog_service.generate_blog_stream(
                db=db,
                topic=request.topic,
                platform=request.platform,
                tone=request.tone
            ):
                yield event_message
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.get("/posts")
def get_recent_posts(db: Session = Depends(get_db), _auth: str = Depends(verify_master_password)):
    """Retrieve history of successfully humanized posts."""
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).limit(15).all()
    return posts


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: str,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Delete a blog post from history."""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    return {"status": "success", "message": "Post deleted successfully"}


class PublishPostRequest(BaseModel):
    published_url: Optional[str] = None
    publication_name: Optional[str] = None


@router.patch("/posts/{post_id}/publish")
def mark_post_published(
    post_id: str,
    req: PublishPostRequest,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Mark a blog post as published on the target platform and record publication metadata."""
    import datetime
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.publication_status = "published"
    post.published_url = req.published_url or post.published_url
    post.publication_name = req.publication_name or post.publication_name
    if not post.published_at:
        post.published_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(post)
    return {
        "status": "success",
        "post_id": post.id,
        "publication_status": post.publication_status,
        "published_url": post.published_url,
        "published_at": post.published_at.isoformat() if post.published_at else None
    }


@router.post("/posts/{post_id}/snapshot")
async def upload_performance_snapshot(
    post_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Upload a Medium/Platform stats dashboard screenshot, OCR extract performance metrics via Gemini Vision,
    and trigger the self-learning feedback loop to generate/update learned insights.
    """
    import os
    import datetime
    from app.models.performance_snapshot import PerformanceSnapshot
    from app.services.performance_engine import performance_engine

    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    image_bytes = await file.read()
    mime_type = file.content_type or "image/png"

    # Save screenshot locally for history
    save_dir = "C:/temp/creator_arc_uploads/snapshots" if os.name == 'nt' else "/tmp/creator_arc_uploads/snapshots"
    os.makedirs(save_dir, exist_ok=True)
    filename = f"snap_{post_id}_{int(datetime.datetime.utcnow().timestamp())}.png"
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    # Calculate week number since publication
    existing_snaps_count = db.query(PerformanceSnapshot).filter(PerformanceSnapshot.blog_post_id == post_id).count()
    week_num = existing_snaps_count + 1

    # Extract metrics via Gemini Vision OCR
    extracted = performance_engine.extract_metrics_from_screenshot(image_bytes, mime_type)

    snapshot = PerformanceSnapshot(
        blog_post_id=post_id,
        snapshot_week=week_num,
        screenshot_url=f"/static/snapshots/{filename}",
        extracted_metrics=extracted,
        extraction_confidence=extracted.get("confidence", 0.9),
        raw_ocr_text=extracted.get("raw_text", "")
    )
    db.add(snapshot)

    post.last_snapshot_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(snapshot)

    # Trigger self-learning loop to regenerate insights based on new performance data
    new_insights = performance_engine.generate_learned_insights(db)

    return {
        "status": "success",
        "snapshot_id": snapshot.id,
        "week": snapshot.snapshot_week,
        "extracted_metrics": extracted,
        "insights_updated": len(new_insights)
    }


@router.get("/posts/{post_id}/performance")
def get_post_performance(
    post_id: str,
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Retrieve full performance snapshot history for a specific blog post."""
    from app.models.performance_snapshot import PerformanceSnapshot
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    snapshots = (
        db.query(PerformanceSnapshot)
        .filter(PerformanceSnapshot.blog_post_id == post_id)
        .order_by(PerformanceSnapshot.snapshot_week.asc())
        .all()
    )

    return {
        "post_id": post.id,
        "suggested_title": post.suggested_title,
        "publication_status": post.publication_status,
        "published_url": post.published_url,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "last_snapshot_at": post.last_snapshot_at.isoformat() if post.last_snapshot_at else None,
        "snapshots": [
            {
                "id": s.id,
                "week": s.snapshot_week,
                "screenshot_url": s.screenshot_url,
                "metrics": s.extracted_metrics,
                "confidence": s.extraction_confidence,
                "created_at": s.created_at.isoformat()
            }
            for s in snapshots
        ]
    }


@router.get("/insights")
def get_learned_insights(
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Retrieve active self-learning insights derived from performance analytics."""
    from app.models.learned_insight import LearnedInsight
    insights = db.query(LearnedInsight).order_by(LearnedInsight.confidence_score.desc()).all()
    return insights


@router.get("/performance-summary")
def get_performance_summary(
    db: Session = Depends(get_db),
    _auth: str = Depends(verify_master_password)
):
    """Retrieve aggregate performance metrics across all published posts and check for pending weekly snapshot alerts."""
    import datetime
    from app.models.performance_snapshot import PerformanceSnapshot

    published_posts = db.query(BlogPost).filter(BlogPost.publication_status == "published").all()
    now = datetime.datetime.utcnow()

    due_for_snapshot = []
    total_views = 0
    total_reads = 0
    total_claps = 0

    for post in published_posts:
        # Check if weekly snapshot is due (older than 7 days or never uploaded)
        days_since = 999
        if post.last_snapshot_at:
            days_since = (now - post.last_snapshot_at).days
        elif post.published_at:
            days_since = (now - post.published_at).days

        if days_since >= 7:
            due_for_snapshot.append({
                "post_id": post.id,
                "title": post.suggested_title or post.topic,
                "days_overdue": days_since if days_since != 999 else 7,
                "published_url": post.published_url
            })

        latest_snap = (
            db.query(PerformanceSnapshot)
            .filter(PerformanceSnapshot.blog_post_id == post.id)
            .order_by(PerformanceSnapshot.snapshot_week.desc())
            .first()
        )
        if latest_snap and latest_snap.extracted_metrics:
            m = latest_snap.extracted_metrics
            total_views += m.get("views", 0)
            total_reads += m.get("reads", 0)
            total_claps += m.get("claps", 0)

    avg_read_ratio = (total_reads / total_views) if total_views > 0 else 0.0

    return {
        "total_published": len(published_posts),
        "total_views": total_views,
        "total_reads": total_reads,
        "total_claps": total_claps,
        "avg_read_ratio": round(avg_read_ratio, 4),
        "due_for_snapshot": due_for_snapshot
    }


