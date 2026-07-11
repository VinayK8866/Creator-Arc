import uuid
from sqlalchemy import JSON, Column, String
from sqlalchemy.types import UserDefinedType
from app.core.database import Base


class SqlAlchemyVector(UserDefinedType):
    """Custom SQLAlchemy type to support PostgreSQL vector column binding and retrieval
    without external dependency restrictions.
    """
    def __init__(self, dim=768):
        self.dim = dim

    def get_col_spec(self, **kw):
        return f"VECTOR({self.dim})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                # Convert list to string representation e.g. '[0.1, 0.2, ...]'
                return f"[{','.join(map(str, value))}]"
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            # Parse string representation to float list
            if isinstance(value, str):
                cleaned = value.strip("[]")
                return [float(x) for x in cleaned.split(",") if x.strip()]
            if isinstance(value, list):
                return value
            return value
        return process


class StyleReference(Base):
    __tablename__ = "style_references"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    content = Column(String, nullable=False)
    embedding = Column(SqlAlchemyVector(768), nullable=True)  # Mapped to VECTOR(768) type
    domain = Column(String, nullable=False, index=True)      # e.g. corporate_email, tech_blog, academic_essay, general_content
    dialect = Column(String, nullable=False, index=True)    # e.g., 'en-IN', 'en-US'
    payload = Column(JSON, nullable=True)  # JSON payload structure: text, domain, tone, word_count
