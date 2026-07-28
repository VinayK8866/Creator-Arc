import uuid
import datetime
from sqlalchemy import JSON, Column, DateTime, String, Text
from app.core.database import Base


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    topic = Column(String, nullable=False)
    platform = Column(String, nullable=False, index=True)
    suggested_title = Column(String, nullable=True)
    seo_title = Column(String, nullable=True)
    feed_title = Column(String, nullable=True)
    title_variations = Column(JSON, nullable=True) # List of 5 draft titles
    url_slug = Column(String, nullable=True) # Custom keyword URL slug
    kicker = Column(String, nullable=True)
    subtitle = Column(String, nullable=True)
    hero_image_url = Column(String, nullable=True)
    hero_image_caption = Column(String, nullable=True)
    compliance_flags = Column(JSON, nullable=True) # AI disclosure, FTC, Offsite notices status
    strategy_audit = Column(JSON, nullable=True) # Full rule compliance audit payload
    tag_recommendations = Column(JSON, nullable=True) # Recommended 5 topic tags
    seo_keywords = Column(JSON, nullable=True) # List of keywords
    original_factual_base = Column(JSON, nullable=True) # Full factual JSON payload
    humanized_content = Column(Text, nullable=True) # Fully assembled markdown text
    content_chunks = Column(JSON, nullable=True) # Detailed array of chunks: heading, facts, humanized, scores
    status = Column(String, nullable=False, default="draft") # draft, processing, completed, failed
    
    # Publication tracking fields
    publication_status = Column(String, nullable=False, default="draft") # draft, published, archived
    published_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    publication_name = Column(String, nullable=True)
    last_snapshot_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

