from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Any
import json
from app.services.gemini_service import gemini_service
from app.services.rewriter.engine import rewriter_engine
from app.services.rewriter.rate_limiter import user_rate_limiter
from app.core.security import verify_master_password

router = APIRouter()


class RewriteRequest(BaseModel):
    text: str
    tone: str = "human-like"  # human-like, professional, engaging, witty
    dialect: str = "en-US"     # en-US, en-IN, en-SG, en-AU, en-GB, etc.


class GeneratePostRequest(BaseModel):
    topic: str
    context: Optional[str] = None
    tone: Optional[str] = "engaging"


def enforce_rate_limit(request: Request):
    """Enforce rate limiting per user tier (Free vs Premium) using client IP/Key."""
    identifier = request.headers.get("X-CreatorArc-Key") or (request.client.host if request.client else "unknown_ip")
    tier = request.headers.get("X-User-Tier", "Free")
    
    is_limited, wait_time = user_rate_limiter.is_rate_limited(identifier, tier)
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail=f"Too Many Requests: '{tier}' rate limit exceeded. Try again in {wait_time:.1f} seconds."
        )


@router.post("/rewrite")
async def rewrite_text(
    request: RewriteRequest,
    fastapi_req: Request,
    _auth: str = Depends(verify_master_password)
):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    enforce_rate_limit(fastapi_req)

    try:
        result = await rewriter_engine.rewrite(
            text=request.text,
            tone=request.tone,
            dialect=request.dialect
        )
        return {
            "original": result["original"],
            "rewritten": result["rewritten"],
            "tone": request.tone,
            "dialect": request.dialect,
            "score": result["score"],
            "attempts": result["attempts"],
            "status": result["status"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rewrite-stream")
async def rewrite_text_stream(
    request: RewriteRequest,
    fastapi_req: Request,
    _auth: str = Depends(verify_master_password)
):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    enforce_rate_limit(fastapi_req)

    async def sse_generator():
        try:
            async for event in rewriter_engine.rewrite_stream(
                text=request.text,
                tone=request.tone,
                dialect=request.dialect
            ):
                event_name = event.get("event", "message")
                event_data = event.get("data", "")
                
                # Format to SSE protocol spec
                yield f"event: {event_name}\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            # Yield error event before closing stream
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.post("/twitter")
async def generate_twitter_post(
    request: GeneratePostRequest,
    fastapi_req: Request,
    _auth: str = Depends(verify_master_password)
):
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    enforce_rate_limit(fastapi_req)

    try:
        posts = await gemini_service.generate_tweets(request.topic, request.context, request.tone)
        return {"topic": request.topic, "posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/linkedin")
async def generate_linkedin_post(
    request: GeneratePostRequest,
    fastapi_req: Request,
    _auth: str = Depends(verify_master_password)
):
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    enforce_rate_limit(fastapi_req)

    try:
        post = await gemini_service.generate_linkedin(request.topic, request.context, request.tone)
        return {"topic": request.topic, "post": post}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
