import os
import shutil
from pathlib import Path
from typing import Optional, Union, List
from datetime import datetime
import json

from backend.app.storage.encryption_service import EncryptionService

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
        }
        storage_path.with_suffix(".meta").write_text(json.dumps(metadata))

        return current_time

    def get_document(self, doc_type: str, case_id: str, doc_id: str, version: Optional[str] = None) -> Optional[str]:
        """
        Retrieves and decrypts a document.
        If version is None, retrieves the latest version.
        """
        if version is None:
            # Find the latest version
            case_path = self._get_storage_path(doc_type, case_id, "").parent # Get case directory
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
        case_path = self._get_storage_path(doc_type, case_id, "").parent
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
            case_path = self._get_storage_path(doc_type, case_id, "").parent
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
            case_path = self._get_storage_path(doc_type, case_id, "").parent
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
                versions = self.list_document_versions(doc_type_dir.name, case_id, doc_id)
                if not versions:
                    continue
                latest_version = versions[0]
                meta_path = self._get_storage_path(doc_type_dir.name, case_id, doc_id, version=latest_version).with_suffix(".meta")
                if meta_path.exists():
                    with open(meta_path, "r") as f:
                        metadata = json.load(f)
                    file_name = metadata.get("file_name", doc_id)
                else:
                    file_name = doc_id

                documents.append({
                    "id": doc_id,
                    "name": file_name,
                    "type": doc_type_dir.name,
                    "url": f"/api/{case_id}/{doc_type_dir.name}/{doc_id}"
                })
        return documents