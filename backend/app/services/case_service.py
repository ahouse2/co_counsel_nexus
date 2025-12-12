from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.case import Case
from backend.app.models.document import Document
import uuid
from datetime import datetime
import json
import zipfile
import io
from pathlib import Path

class CaseService:
    def __init__(self, db: Session):
        self.db = db

    def create_case(self, name: str, description: Optional[str] = None) -> Case:
        case = Case(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            status="active"
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        return self.db.query(Case).filter(Case.id == case_id).first()

    def list_cases(self) -> List[Case]:
        return self.db.query(Case).all()

    def update_case(self, case_id: str, name: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None) -> Optional[Case]:
        case = self.get_case(case_id)
        if not case:
            return None
        
        if name:
            case.name = name
        if description:
            case.description = description
        if status:
            case.status = status
            
        self.db.commit()
        self.db.refresh(case)
        return case

    def delete_case(self, case_id: str) -> bool:
        case = self.get_case(case_id)
        if not case:
            return False
        self.db.delete(case)
        self.db.commit()
        return True

    def export_case(self, case_id: str) -> Optional[bytes]:
        case = self.get_case(case_id)
        if not case:
            return None

        # Get all documents for this case
        documents = self.db.query(Document).filter(Document.case_id == case_id).all()
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add case metadata
            case_data = {
                "id": case.id,
                "name": case.name,
                "description": case.description,
                "status": case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "updated_at": case.updated_at.isoformat() if case.updated_at else None
            }
            zip_file.writestr("case_metadata.json", json.dumps(case_data, indent=2))
            
            # Add document metadata list
            docs_data = []
            for doc in documents:
                docs_data.append({
                    "id": doc.id,
                    "name": doc.name,
                    "path": doc.path,
                    "hash_sha256": doc.hash_sha256,
                    "custom_metadata": doc.custom_metadata,
                    "forensic_metadata": doc.forensic_metadata
                })
            zip_file.writestr("documents_metadata.json", json.dumps(docs_data, indent=2))
            
            # Note: We are NOT exporting the actual physical files here to keep it lightweight 
            # and because they might be huge. This is a metadata export.
            # If full export is needed, we would need to read files from DocumentStore.
            
        return zip_buffer.getvalue()

    def import_case(self, zip_content: bytes) -> Case:
        with zipfile.ZipFile(io.BytesIO(zip_content), "r") as zip_file:
            # Read case metadata
            case_data = json.loads(zip_file.read("case_metadata.json"))
            
            # Check if case exists, if so, maybe update or skip? 
            # For now, let's assume we create a new one if ID doesn't exist, or update if it does.
            existing_case = self.get_case(case_data["id"])
            if existing_case:
                # Update existing
                existing_case.name = case_data["name"]
                existing_case.description = case_data.get("description")
                existing_case.status = case_data.get("status")
                self.db.commit()
                self.db.refresh(existing_case)
                return existing_case
            else:
                # Create new with specific ID
                case = Case(
                    id=case_data["id"],
                    name=case_data["name"],
                    description=case_data.get("description"),
                    status=case_data.get("status", "active")
                )
                self.db.add(case)
                self.db.commit()
                self.db.refresh(case)
                return case
