from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.service_of_process import ServiceRequest as ServiceRequestModel, ServiceStatus
from backend.app.models.document import Document as DocumentModel
from backend.app.models.recipient import Recipient as RecipientModel
import uuid

router = APIRouter()

class Recipient(BaseModel):
    id: str
    name: str
    address: str

    class Config:
        from_attributes = True

class Document(BaseModel):
    id: str
    name: str
    path: str

    class Config:
        from_attributes = True

class ServiceRequest(BaseModel):
    id: str
    status: ServiceStatus
    document: Document
    recipient: Recipient

    class Config:
        from_attributes = True

class ServiceRequestCreate(BaseModel):
    document_id: str
    recipient_id: str

@router.post("/service-of-process", response_model=ServiceRequest)
async def create_service_request(
    request: ServiceRequestCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new service of process request.
    """
    # Check if document and recipient exist
    document = db.query(DocumentModel).filter(DocumentModel.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    recipient = db.query(RecipientModel).filter(RecipientModel.id == request.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    new_request = ServiceRequestModel(
        id=str(uuid.uuid4()),
        document_id=request.document_id,
        recipient_id=request.recipient_id,
        status=ServiceStatus.PENDING,
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

@router.get("/service-of-process", response_model=List[ServiceRequest])
async def get_service_requests(db: Session = Depends(get_db)):
    """
    Get all service of process requests.
    """
    return db.query(ServiceRequestModel).all()

# Add endpoints for creating and getting recipients and documents

class RecipientCreate(BaseModel):
    name: str
    address: str

@router.post("/recipients", response_model=Recipient)
async def create_recipient(
    request: RecipientCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new recipient.
    """
    new_recipient = RecipientModel(
        id=str(uuid.uuid4()),
        **request.dict(),
    )
    db.add(new_recipient)
    db.commit()
    db.refresh(new_recipient)
    return new_recipient

@router.get("/recipients", response_model=List[Recipient])
async def get_recipients(db: Session = Depends(get_db)):
    """
    Get all recipients.
    """
    return db.query(RecipientModel).all()

class DocumentCreate(BaseModel):
    name: str
    path: str

@router.post("/documents", response_model=Document)
async def create_document(
    request: DocumentCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new document.
    """
    new_document = DocumentModel(
        id=str(uuid.uuid4()),
        **request.dict(),
    )
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    return new_document

@router.get("/documents", response_model=List[Document])
async def get_documents(db: Session = Depends(get_db)):
    """
    Get all documents.
    """
    return db.query(DocumentModel).all()