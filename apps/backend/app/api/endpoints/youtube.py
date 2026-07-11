from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.job import Job
from app.core.celery_app import celery_app
from app.core.security import verify_master_password
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter()


class YouTubeRequest(BaseModel):
    video_url: str


@router.post("/summarize")
def summarize_video(
    request: YouTubeRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _auth: str = Depends(verify_master_password)
):
    if not request.video_url.startswith("http://") and not request.video_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid media URL")

    # Create job
    job = Job(
        type="yt-summarize",
        status="pending",
        payload={"video_url": request.video_url}
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue or execute directly
    if not settings.USE_CELERY:
        from workers.tasks.youtube_tasks import summarize_video_task
        background_tasks.add_task(summarize_video_task, job.id, request.video_url)
    else:
        celery_app.send_task(
            "workers.tasks.youtube_tasks.summarize_video_task",
            args=[job.id, request.video_url]
        )

    return {"job_id": job.id, "status": "queued"}


@router.post("/tags")
def generate_tags(
    request: YouTubeRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _auth: str = Depends(verify_master_password)
):
    if not request.video_url.startswith("http://") and not request.video_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid media URL")

    job = Job(
        type="yt-tags",
        status="pending",
        payload={"video_url": request.video_url}
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue or execute directly
    if not settings.USE_CELERY:
        from workers.tasks.youtube_tasks import generate_tags_task
        background_tasks.add_task(generate_tags_task, job.id, request.video_url)
    else:
        celery_app.send_task(
            "workers.tasks.youtube_tasks.generate_tags_task",
            args=[job.id, request.video_url]
        )

    return {"job_id": job.id, "status": "queued"}


@router.post("/description")
def generate_description(
    request: YouTubeRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _auth: str = Depends(verify_master_password)
):
    if not request.video_url.startswith("http://") and not request.video_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid media URL")

    job = Job(
        type="yt-description",
        status="pending",
        payload={"video_url": request.video_url}
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue or execute directly
    if not settings.USE_CELERY:
        from workers.tasks.youtube_tasks import generate_description_task
        background_tasks.add_task(generate_description_task, job.id, request.video_url)
    else:
        celery_app.send_task(
            "workers.tasks.youtube_tasks.generate_description_task",
            args=[job.id, request.video_url]
        )

    return {"job_id": job.id, "status": "queued"}
