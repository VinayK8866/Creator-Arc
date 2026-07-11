import uuid
import datetime
from sqlalchemy import JSON, Column, DateTime, String, Float, Boolean
from app.core.database import Base


class RewritePair(Base):
    __tablename__ = "rewrite_pairs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    original_text = Column(String, nullable=False)
    facts = Column(JSON, nullable=True)  # List of facts extracted by Abstractor
    humanized_text = Column(String, nullable=False)
    score = Column(Float, nullable=False, index=True) # Adversarial score rating
    is_candidate = Column(Boolean, nullable=False, default=False, index=True) # True if score <= 0.15
    dialect = Column(String, nullable=False, index=True) # e.g. en-US, en-IN
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.score is not None:
            self.is_candidate = (self.score < 0.15)
