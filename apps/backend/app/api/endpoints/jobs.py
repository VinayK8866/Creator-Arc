from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.job import Job
from pydantic import BaseModel
from typing import Any, Optional
from app.core.security import verify_master_password

router = APIRouter()


class JobResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    type: str
    status: str
    payload: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


class UpdateModelRequest(BaseModel):
    repo_id: str = "nicoamoretti/roberta-openai-detector-onnx"
    filename: str = "onnx/model.onnx"


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/update-scorer-model")
def update_scorer_model(
    request: UpdateModelRequest,
    _auth: str = Depends(verify_master_password)
):
    from app.services.rewriter.engine import rewriter_engine
    success = rewriter_engine.scorer.update_model(repo_id=request.repo_id, filename=request.filename)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update/download ONNX model")
    return {"message": "Scorer model updated successfully", "repo_id": request.repo_id}
