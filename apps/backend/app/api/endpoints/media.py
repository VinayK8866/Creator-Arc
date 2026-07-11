import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.job import Job
from app.core.celery_app import celery_app
from app.core.security import verify_master_password
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Local upload directory for dev testing
UPLOAD_DIR = "/tmp/creator_arc_uploads" if os.name != 'nt' else "C:/temp/creator_arc_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class MediaURLRequest(BaseModel):
    image_url: str
    options: Optional[dict] = None


@router.post("/upscale")
async def upscale_image(
    image_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    scale: int = Form(2),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _auth: str = Depends(verify_master_password)
):
    if not image_url and not file:
        raise HTTPException(status_code=400, detail="Either image_url or file must be provided")

    input_payload = {"scale": scale}

    if file:
        # Save local file
        file_ext = os.path.splitext(file.filename)[1]
        local_filename = f"{uuid.uuid4()}{file_ext}"
        local_path = os.path.join(UPLOAD_DIR, local_filename)
        with open(local_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        input_payload["local_path"] = local_path
        input_payload["filename"] = file.filename
    else:
        input_payload["image_url"] = image_url

    # Create job in database
    job = Job(
        type="upscale",
        status="pending",
        payload=input_payload
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue or execute directly
    if not settings.USE_CELERY:
        # Dynamic import to avoid circular dependency
        from workers.tasks.media_tasks import upscale_image_task
        background_tasks.add_task(upscale_image_task, job.id, input_payload)
    else:
        celery_app.send_task(
            "workers.tasks.media_tasks.upscale_image_task",
            args=[job.id, input_payload]
        )

    return {"job_id": job.id, "status": "queued"}


@router.post("/remove-bg")
async def remove_background(
    image_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _auth: str = Depends(verify_master_password)
):
    if not image_url and not file:
        raise HTTPException(status_code=400, detail="Either image_url or file must be provided")

    input_payload = {}

    if file:
        file_ext = os.path.splitext(file.filename)[1]
        local_filename = f"{uuid.uuid4()}{file_ext}"
        local_path = os.path.join(UPLOAD_DIR, local_filename)
        with open(local_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        input_payload["local_path"] = local_path
        input_payload["filename"] = file.filename
    else:
        input_payload["image_url"] = image_url

    # Create job
    job = Job(
        type="bg-removal",
        status="pending",
        payload=input_payload
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue or execute directly
    if not settings.USE_CELERY:
        from workers.tasks.media_tasks import remove_bg_task
        background_tasks.add_task(remove_bg_task, job.id, input_payload)
    else:
        celery_app.send_task(
            "workers.tasks.media_tasks.remove_bg_task",
            args=[job.id, input_payload]
        )

    return {"job_id": job.id, "status": "queued"}


class TranscribeLinkRequest(BaseModel):
    url: str


@router.post("/transcribe-link")
async def transcribe_link(
    request: TranscribeLinkRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _auth: str = Depends(verify_master_password)
):
    if not request.url.startswith("http://") and not request.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid media URL")

    # Create job in database
    job = Job(
        type="media-transcribe",
        status="pending",
        payload={"url": request.url}
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue or execute directly
    if not settings.USE_CELERY:
        from workers.tasks.media_tasks import transcribe_link_task
        background_tasks.add_task(transcribe_link_task, job.id, request.url)
    else:
        celery_app.send_task(
            "workers.tasks.media_tasks.transcribe_link_task",
            args=[job.id, request.url]
        )

    return {"job_id": job.id, "status": "queued"}

