from fastapi import APIRouter
from app.api.endpoints import text, media, youtube, jobs, blog

api_router = APIRouter()
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(text.router, prefix="/text", tags=["text"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
api_router.include_router(blog.router, prefix="/blog", tags=["blog"])
