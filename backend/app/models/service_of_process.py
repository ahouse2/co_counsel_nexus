from sqlalchemy import Column, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base
from backend.app.models.document import Document
from backend.app.models.recipient import Recipient
import enum

class ServiceStatus(enum.Enum):
    PENDING = "Pending"
    SERVED = "Served"
    FAILED = "Failed"

class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"))
    recipient_id = Column(String, ForeignKey("recipients.id"))
    status = Column(Enum(ServiceStatus))

    document = relationship("Document")
    recipient = relationship("Recipient")
