from fastapi import APIRouter, Depends, HTTPException
from backend.app.config import Settings, get_settings
from backend.app.storage.document_store import DocumentStore
import json

router = APIRouter()

def get_document_store(settings: Settings = Depends(get_settings)) -> DocumentStore:
    return DocumentStore(base_dir=settings.document_storage_path, encryption_key=settings.encryption_key)

@router.get("/{doc_id}", summary="Get forensic metadata for a document")
async def get_forensic_metadata(
    doc_id: str,
    case_id: str = "default_case",
    store: DocumentStore = Depends(get_document_store)
):
    """
    Retrieves the forensic metadata (hash, size, magic bytes) for a document.
    """
    # Try both doc types since we don't know which one it is
    for doc_type in ["my_documents", "opposition_documents"]:
        versions = store.list_document_versions(doc_type, case_id, doc_id)
        if versions:
            latest = versions[0]
            # Access internal method to get path - pragmatic for now
            path = store._get_storage_path(doc_type, case_id, doc_id, version=latest).with_suffix(".meta")
            if path.exists():
                with open(path, "r") as f:
                    data = json.load(f)
                    # Ensure we return the ID too
                    data["id"] = doc_id
                    return data
                    
    raise HTTPException(status_code=404, detail="Document not found")

@router.get("/{doc_id}/hex", summary="Get hex view of document head/tail")
async def get_hex_view(
    doc_id: str,
    case_id: str = "default_case",
    store: DocumentStore = Depends(get_document_store)
):
    """
    Returns the first 512 bytes and last 512 bytes of the document in hex format.
    Used for the Hex Viewer UI.
    """
    for doc_type in ["my_documents", "opposition_documents"]:
        try:
            content = store.get_document_content(doc_type, case_id, doc_id)
            if content:
                if isinstance(content, str):
                    content = content.encode('utf-8')
                # Return head and tail
                head = content[:512].hex()
                tail = content[-512:].hex() if len(content) > 512 else ""
                return {
                    "head": head, 
                    "tail": tail, 
                    "total_size": len(content),
                    "doc_id": doc_id
                }
        except Exception as e:
            print(f"Error reading document {doc_id}: {e}")
            continue
            

    raise HTTPException(status_code=404, detail="Document not found")

@router.post("/{doc_id}/analyze", summary="Trigger Deep Forensic Analysis")
async def trigger_deep_analysis(
    doc_id: str,
    case_id: str = "default_case",
    store: DocumentStore = Depends(get_document_store)
):
    """
    Triggers deep forensic analysis (Tampering Detection, Metadata Anomalies).
    """
    from backend.app.services.forensic_analyzer import ForensicAnalyzer
    
    analyzer = ForensicAnalyzer()
    
    # Find document content and metadata
    for doc_type in ["my_documents", "opposition_documents"]:
        try:
            # Get Content
            content = store.get_document_content(doc_type, case_id, doc_id)
            if not content:
                continue
                
            if isinstance(content, str):
                content = content.encode('utf-8')

            # Get Metadata
            versions = store.list_document_versions(doc_type, case_id, doc_id)
            if not versions:
                continue
            
            meta_path = store._get_storage_path(doc_type, case_id, doc_id, version=versions[0]).with_suffix(".meta")
            metadata = {}
            if meta_path.exists():
                with open(meta_path, "r") as f:
                    metadata = json.load(f)

            # Run Analysis
            result = analyzer.analyze_manipulation(metadata, content)
            return result
            
        except Exception as e:
            print(f"Error accessing doc {doc_id}: {e}")
            continue

    raise HTTPException(status_code=404, detail="Document not found")