import uuid
from sqlalchemy import JSON, Column, String
from app.core.database import Base


class PlatformMetadata(Base):
    __tablename__ = "platform_metadata"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    platform = Column(String, unique=True, nullable=False, index=True) # e.g. medium, substack, reddit, quora, wordpress, squarespace, wix
    display_name = Column(String, nullable=False)
    storytelling_cadence = Column(String, nullable=False)
    heading_style = Column(String, nullable=False)
    layout_constraints = Column(JSON, nullable=False) # formatting rules, blockquote requirements
    seo_optimizations = Column(JSON, nullable=True)
