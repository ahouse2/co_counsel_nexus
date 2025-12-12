from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from backend.app.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, index=True) # Intentionally loose coupling for now to avoid migration issues
    name = Column(String, index=True)
    path = Column(String)
    author = Column(String)
    keywords = Column(JSON)
    tags = Column(JSON)
    custom_metadata = Column(JSON)
    hash_sha256 = Column(String, index=True)
    forensic_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
