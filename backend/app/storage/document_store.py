import os
import shutil
from pathlib import Path
from typing import Optional, Union, List
from datetime import datetime
import json

from .encryption_service import EncryptionService

class DocumentStore:
    """
    Manages secure storage, retrieval, and versioning of documents.
    Ensures strict segregation between 'My Documents' and 'Opposition Documents'.
    """
    def __init__(self, base_dir: Union[str, Path], encryption_key: str):
        self.base_dir = Path(base_dir)
        self.my_docs_dir = self.base_dir / "my_documents"
        self.opposition_docs_dir = self.base_dir / "opposition_documents"
        self.encryption_service = EncryptionService(encryption_key)

        self.my_docs_dir.mkdir(parents=True, exist_ok=True)
        self.opposition_docs_dir.mkdir(parents=True, exist_ok=True)

    def _get_storage_path(self, doc_type: str, case_id: str, doc_id: str, version: Optional[str] = None) -> Path:
        if doc_type == "my_documents":
            storage_root = self.my_docs_dir
        elif doc_type == "opposition_documents":
            storage_root = self.opposition_docs_dir
        else:
            raise ValueError("Invalid document type. Must be 'my_documents' or 'opposition_documents'.")

        case_path = storage_root / case_id
        case_path.mkdir(parents=True, exist_ok=True)

        if version:
            return case_path / f"{doc_id}_v{version}"
        return case_path / doc_id

    def save_document(
        self,
        doc_type: str,
        case_id: str,
        doc_id: str,
        content: Union[str, bytes],
        file_name: str,
        author: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        custom_metadata: Optional[dict] = None,
        relative_path: Optional[str] = None,
        hash_sha256: Optional[str] = None,
        forensic_metadata: Optional[dict] = None,
    ) -> str:
        """
        Saves and encrypts a document, returning its version.
        """
        current_time = datetime.now().strftime("%Y%m%d%H%M%S")
        storage_path = self._get_storage_path(doc_type, case_id, doc_id, version=current_time)

        encrypted_content = self.encryption_service.encrypt(content)
        storage_path.with_suffix(".encrypted").write_bytes(encrypted_content)

        metadata = {
            "file_name": file_name,
            "author": author,
            "keywords": keywords,
            "tags": tags,
            "custom_metadata": custom_metadata,
            "created_at": current_time,
            "relative_path": relative_path,
            "hash_sha256": hash_sha256,
            "forensic_metadata": forensic_metadata,
            "status": "queued", # Initialize status
        }
        storage_path.with_suffix(".meta").write_text(json.dumps(metadata))

        return current_time

    def update_document_status(self, doc_type: str, case_id: str, doc_id: str, status: str, version: Optional[str] = None):
        """
        Updates the status of a document in its metadata.
        """
        if version is None:
            # Find latest version
            case_path = self._get_storage_path(doc_type, case_id, "")
            versions = sorted([
                f.name.replace(f"{doc_id}_v", "").replace(".encrypted", "")
                for f in case_path.glob(f"{doc_id}_v*.encrypted")
            ], reverse=True)
            if not versions:
                return
            version = versions[0]
        
        meta_path = self._get_storage_path(doc_type, case_id, doc_id, version=version).with_suffix(".meta")
        if meta_path.exists():
            with open(meta_path, "r") as f:
                metadata = json.load(f)
            
            metadata["status"] = status
            metadata["updated_at"] = datetime.now().strftime("%Y%m%d%H%M%S")
            
            with open(meta_path, "w") as f:
                json.dump(metadata, f)

    def get_document(self, doc_type: str, case_id: str, doc_id: str, version: Optional[str] = None) -> Optional[str]:
        """
        Retrieves and decrypts a document.
        If version is None, retrieves the latest version.
        """
        if version is None:
            # Find the latest version
            case_path = self._get_storage_path(doc_type, case_id, "") # Get case directory
            versions = sorted([
                f.name.replace(f"{doc_id}_v", "").replace(".encrypted", "")
                for f in case_path.glob(f"{doc_id}_v*.encrypted")
            ], reverse=True)
            if not versions:
                return None
            latest_version = versions[0]
            storage_path = self._get_storage_path(doc_type, case_id, doc_id, version=latest_version).with_suffix(".encrypted")
        else:
            storage_path = self._get_storage_path(doc_type, case_id, doc_id, version=version).with_suffix(".encrypted")

        if not storage_path.exists():
            return None

        encrypted_content = storage_path.read_bytes()
        return self.encryption_service.decrypt(encrypted_content)

    def list_document_versions(self, doc_type: str, case_id: str, doc_id: str) -> List[str]:
        """
        Lists all available versions for a given document.
        """
        case_path = self._get_storage_path(doc_type, case_id, "")
        versions = sorted([
            f.name.replace(f"{doc_id}_v", "").replace(".encrypted", "")
            for f in case_path.glob(f"{doc_id}_v*.encrypted")
        ], reverse=True)
        return versions

    def delete_document(self, doc_type: str, case_id: str, doc_id: str, version: Optional[str] = None):
        """
        Deletes a specific version of a document, or all versions if version is None.
        """
        if version:
            storage_path = self._get_storage_path(doc_type, case_id, doc_id, version=version)
            if storage_path.with_suffix(".encrypted").exists():
                storage_path.with_suffix(".encrypted").unlink()
            if storage_path.with_suffix(".meta").exists():
                storage_path.with_suffix(".meta").unlink()
        else:
            # Delete all versions and potentially the document directory if empty
            case_path = self._get_storage_path(doc_type, case_id, "")
            for f in case_path.glob(f"{doc_id}_v*"):
                f.unlink()
            # Clean up case directory if empty
            if not any(case_path.iterdir()):
                shutil.rmtree(case_path)

    def get_document_path(self, doc_type: str, case_id: str, doc_id: str, version: Optional[str] = None) -> Optional[Path]:
        """
        Returns the absolute path to a document (encrypted).
        """
        if version is None:
            case_path = self._get_storage_path(doc_type, case_id, "")
            versions = sorted([
                f.name.replace(f"{doc_id}_v", "").replace(".encrypted", "")
                for f in case_path.glob(f"{doc_id}_v*.encrypted")
            ], reverse=True)
            if not versions:
                return None
            latest_version = versions[0]
            return self._get_storage_path(doc_type, case_id, doc_id, version=latest_version).with_suffix(".encrypted")
        else:
            storage_path = self._get_storage_path(doc_type, case_id, doc_id, version=version).with_suffix(".encrypted")
            return storage_path if storage_path.exists() else None

    def list_all_documents(self, case_id: str) -> List[dict]:
        """
        Lists all documents for a given case.
        """
        documents = []
        for doc_type_dir in [self.my_docs_dir, self.opposition_docs_dir]:
            case_path = doc_type_dir / case_id
            if not case_path.exists():
                continue

            doc_ids = set()
            for doc_file in case_path.glob("*.encrypted"):
                doc_ids.add(doc_file.name.split("_v")[0])

            for doc_id in doc_ids:
                try:
                    versions = self.list_document_versions(doc_type_dir.name, case_id, doc_id)
                    if not versions:
                        continue
                    latest_version = versions[0]
                    meta_path = self._get_storage_path(doc_type_dir.name, case_id, doc_id, version=latest_version).with_suffix(".meta")
                    
                    created_at = None
                    size = 0
                    content_type = "application/octet-stream"
                    file_name = doc_id # Default
                    status = "unknown"
                    hash_sha256 = None
                    forensic_metadata = {}

                    if meta_path.exists():
                        try:
                            with open(meta_path, "r") as f:
                                metadata = json.load(f)
                            file_name = metadata.get("file_name", doc_id)
                            status = metadata.get("status", "unknown")
                            hash_sha256 = metadata.get("hash_sha256")
                            forensic_metadata = metadata.get("forensic_metadata") or {}
                            created_at = metadata.get("created_at")
                            
                            # Format created_at to ISO string if it's in YYYYMMDDHHMMSS format
                            if created_at and len(created_at) == 14:
                                try:
                                    dt = datetime.strptime(created_at, "%Y%m%d%H%M%S")
                                    created_at = dt.isoformat()
                                except ValueError:
                                    pass

                            size = forensic_metadata.get("size_bytes", 0)
                            
                            # Infer content type from extension if not present
                            import mimetypes
                            content_type, _ = mimetypes.guess_type(file_name)
                            if not content_type:
                                content_type = "application/octet-stream"
                                
                            # Extract additional metadata
                            tags = metadata.get("tags", [])
                            categories = metadata.get("keywords", []) # Mapping keywords to categories
                            review_status = metadata.get("review_status", "pending")
                            custom_metadata = metadata.get("custom_metadata", {})
                                
                        except Exception as e:
                            print(f"Error reading metadata for {doc_id}: {e}")
                            pass

                    documents.append({
                        "id": doc_id,
                        "filename": file_name, # Frontend expects filename
                        "name": file_name, # Keep for backward compatibility
                        "type": doc_type_dir.name,
                        "content_type": content_type,
                        "size": size,
                        "created_at": created_at or datetime.now().isoformat(),
                        "url": f"/api/{case_id}/{doc_type_dir.name}/{doc_id}",
                        "status": status,
                        "hash_sha256": hash_sha256,
                        "forensic_metadata": forensic_metadata,
                        "tags": tags,
                        "categories": categories,
                        "review_status": review_status,
                        "metadata": custom_metadata, # Expose custom metadata (summary, entities)
                    })
                except Exception as e:
                    print(f"Error listing document {doc_id}: {e}")
                    continue
        return documents

    def write_document(self, doc_id: str, document: dict) -> None:
        """
        Writes document metadata to storage.
        Used by ingestion worker to update document details.
        """
        # Determine doc_type and case_id from document metadata if possible,
        # otherwise default to 'my_documents' and 'default_case' (or search for existing)
        
        # Try to find existing document to get correct path
        # This is a bit inefficient but necessary without case_id/doc_type in arguments
        found = False
        for doc_type in ["my_documents", "opposition_documents"]:
            # We don't know the case_id easily, so we might have to search or assume default
            # For now, let's assume 'default_case' if not found, or try to find it
            
            # Better approach: Check if 'type' and 'case_id' are in the document dict
            # The ingestion service passes a dictionary that might have these
            
            # If we can't find it, we can't write it safely.
            # However, the ingestion worker usually calls this after registration.
            pass

        # IngestionService._register_document calls this with:
        # { "id": doc_id, "title": title, **metadata }
        # metadata contains "type" (doc_type) and "case_id" (if we added it)
        
        doc_type = document.get("type", "my_documents")
        # Map 'image', 'pdf' etc to 'my_documents' if they are not the top-level types
        if doc_type not in ["my_documents", "opposition_documents"]:
             # It might be the file type (e.g. 'pdf'), so default to my_documents
             # But we need to know where it was originally saved.
             # The ingestion service doesn't strictly track 'case_id' in the same way the API does.
             # It uses 'origin' or 'source_type'.
             
             # Fallback: Search for the document ID in the store to find its location
             doc_type = "my_documents" # Default
        
        case_id = document.get("case_id", "default_case")
        
        # Search for existing document to confirm location
        target_path = None
        for dt in ["my_documents", "opposition_documents"]:
            # Check default case first
            path = self._get_storage_path(dt, case_id, doc_id)
            if path.parent.exists(): # Case dir exists
                # Check for any version
                if list(path.parent.glob(f"{doc_id}_v*")):
                    doc_type = dt
                    target_path = path
                    break
        
        if not target_path:
             # If not found, we might be creating it, but save_document should have done that.
             # If this is a pure metadata update from ingestion, we assume it exists.
             # If it doesn't exist, we can't easily create the encrypted file here without content.
             # But write_document is mostly for metadata updates in this context.
             pass

        # Update the metadata file of the latest version
        self.update_document_metadata(doc_type, case_id, doc_id, document)

    def update_document_metadata(self, doc_type: str, case_id: str, doc_id: str, metadata_updates: dict, version: Optional[str] = None):
        """
        Updates the metadata of a document.
        """
        if version is None:
            # Find latest version
            case_path = self._get_storage_path(doc_type, case_id, "")
            if not case_path.exists():
                return
                
            versions = sorted([
                f.name.replace(f"{doc_id}_v", "").replace(".encrypted", "")
                for f in case_path.glob(f"{doc_id}_v*.encrypted")
            ], reverse=True)
            if not versions:
                return
            version = versions[0]
        
        meta_path = self._get_storage_path(doc_type, case_id, doc_id, version=version).with_suffix(".meta")
        
        current_metadata = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    current_metadata = json.load(f)
            except Exception:
                pass
        
        # Merge updates
        current_metadata.update(metadata_updates)
        current_metadata["updated_at"] = datetime.now().strftime("%Y%m%d%H%M%S")
        
        with open(meta_path, "w") as f:
            json.dump(current_metadata, f)

    def read_document(self, doc_id: str) -> dict:
        """
        Reads document metadata.
        Used by ingestion service to check checksums etc.
        """
        # Search for the document in all locations
        for doc_type in ["my_documents", "opposition_documents"]:
            # We have to search all cases? That's expensive.
            # For now, assume default_case or search known paths if possible.
            # Since we don't have a global index, we iterate.
            
            root = self.base_dir / doc_type
            if not root.exists():
                continue
                
            for case_dir in root.iterdir():
                if not case_dir.is_dir():
                    continue
                    
                # Look for doc_id in this case
                # Pattern: doc_id_v*.meta
                meta_files = list(case_dir.glob(f"{doc_id}_v*.meta"))
                if meta_files:
                    # Found it
                    # Get latest
                    meta_files.sort(reverse=True)
                    latest = meta_files[0]
                    
                    with open(latest, "r") as f:
                        data = json.load(f)
                        data["id"] = doc_id # Ensure ID is present
                        return data
                        
        raise FileNotFoundError(f"Document {doc_id} not found")