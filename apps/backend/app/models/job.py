import datetime
import uuid
from sqlalchemy import JSON, Column, DateTime, String
from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True, index=True)
    type = Column(String, nullable=False, index=True)  # e.g., 'upscale', 'bg-removal', 'yt-summarize', 'text-gen'
    status = Column(String, nullable=False, default="pending", index=True)  # pending, processing, completed, failed
    payload = Column(JSON, nullable=True)  # input params: e.g. {"image_url": "...", "scale": 2}
    result = Column(JSON, nullable=True)   # outputs: e.g. {"url": "...", "duration": 5.4} or {"summary": "..."}
    error = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
