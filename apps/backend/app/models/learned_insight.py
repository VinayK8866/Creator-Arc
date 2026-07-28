import uuid
import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from app.core.database import Base


class LearnedInsight(Base):
    __tablename__ = "learned_insights"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))

    # Categorization
    insight_type = Column(String, nullable=False, index=True)
    # One of: 'structural', 'formatting', 'tone', 'algorithmic', 'anti_pattern', 'seo'
    # - structural: heading style, section count, paragraph length
    # - formatting: pull quotes, TK markers, blockquotes usage
    # - tone: conversational vs formal, contractions, rhetorical questions
    # - algorithmic: Medium distribution signals (clap velocity, read ratio triggers)
    # - anti_pattern: patterns that correlate with POOR performance
    # - seo: keyword placement, title structure, slug patterns

    rule_id = Column(String, nullable=True)  # Optional link to Medium strategy rule e.g. "SR-01", "AD-25"

    insight_text = Column(Text, nullable=False)
    # Human-readable insight that gets injected into prompts, e.g.:
    # "Posts with question-style H2 headings achieved 35% higher read ratios."

    # Statistical backing
    confidence_score = Column(Float, nullable=False, default=0.5)  # 0.0-1.0
    sample_size = Column(Integer, nullable=False, default=0)  # Number of posts this insight is based on
    avg_read_ratio = Column(Float, nullable=True)  # Average read ratio for posts matching this insight
    avg_views = Column(Float, nullable=True)  # Average views for posts matching this insight

    is_active = Column(Boolean, nullable=False, default=True)  # Whether to inject into prompts
    source = Column(String, nullable=False, default="auto")  # 'auto' (system-generated) or 'manual' (user-set)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
