import uuid
import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from app.core.database import Base


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    blog_post_id = Column(String, ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_week = Column(Integer, nullable=False)  # Week number since publication (1, 2, 3...)
    screenshot_url = Column(String, nullable=True)  # Path to uploaded screenshot file

    # Gemini Vision extracted metrics
    extracted_metrics = Column(JSON, nullable=True)
    # Expected shape:
    # {
    #   "views": int,
    #   "reads": int,
    #   "read_ratio": float,        # reads/views as percentage
    #   "claps": int,
    #   "fans": int,                # unique clappers
    #   "highlights": int,
    #   "responses": int,
    #   "external_views": int,      # from search/social
    #   "internal_views": int,      # from Medium distribution
    #   "new_followers": int
    # }

    extraction_confidence = Column(Float, nullable=True)  # 0.0-1.0 confidence of OCR extraction
    raw_ocr_text = Column(Text, nullable=True)  # Raw text Gemini Vision extracted before parsing

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
