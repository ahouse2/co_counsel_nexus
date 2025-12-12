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
            content = store.get_document(doc_type, case_id, doc_id)
            if content:
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
    Triggers the ForensicAnalysisCrew to perform deep analysis (ELA, Splicing, etc.).
    """
    from backend.app.agents.swarms_runner import get_swarms_runner
    import asyncio
    
    runner = get_swarms_runner()
    
    # Check if document exists
    doc_path = None
    for doc_type in ["my_documents", "opposition_documents"]:
        versions = store.list_document_versions(doc_type, case_id, doc_id)
        if versions:
            # Get the actual file path
            # This is a bit hacky, accessing internal method, but needed for the tool
            doc_path = str(store._get_storage_path(doc_type, case_id, doc_id, version=versions[0]))
            break
            
    if not doc_path:
        raise HTTPException(status_code=404, detail="Document not found")
        
    prompt = f"""
    Context: Forensic Analysis for Document {doc_id}.
    File Path: {doc_path}
    Role: You are the Forensics Lead.
    
    Task:
    1. Analyze the document for authenticity (ELA, Metadata).
    2. Check for splicing or manipulation.
    3. Return a JSON report with:
       - authenticity_score: float (0.0-1.0)
       - flags: list of strings (Issues found)
       - details: str (Detailed findings)
    """
    
    loop = asyncio.get_event_loop()
    try:
        # Route to 'forensics'
        response_text = await loop.run_in_executor(None, runner.route_and_run, prompt)
        
        # Parse JSON
        import json
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
            
        return json.loads(response_text.strip())
        
    except Exception as e:
        print(f"Swarms Execution Failed: {e}")
        raise HTTPException(status_code=500, detail=f"Forensic Analysis Failed: {e}")