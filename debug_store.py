import sys
from pathlib import Path
from backend.app.storage.document_store import DocumentStore
from backend.app.config import get_settings

def debug_store():
    settings = get_settings()
    store = DocumentStore(base_dir=settings.document_storage_path, encryption_key=settings.encryption_key)
    case_id = "default_case"
    
    print(f"--- Debugging list_all_documents logic ---")
    
    doc_type_dir = store.my_docs_dir
    case_path = doc_type_dir / case_id
    print(f"Case path: {case_path}")
    
    if not case_path.exists():
        print("Case path does not exist!")
        return

    doc_ids = set()
    files = list(case_path.glob("*.encrypted"))
    print(f"Found {len(files)} encrypted files via glob.")
    
    for doc_file in files[:5]:
        print(f"  File: {doc_file.name}")
        doc_id = doc_file.name.split("_v")[0]
        print(f"  Extracted doc_id: {doc_id}")
        doc_ids.add(doc_id)
        
    print(f"Total unique doc_ids found: {len(doc_ids)}")
    
    for doc_id in list(doc_ids)[:1]:
        print(f"--- Checking doc_id: {doc_id} ---")
        versions = store.list_document_versions(doc_type_dir.name, case_id, doc_id)
        print(f"  Versions found: {versions}")
        
        if not versions:
            print("  No versions found via store method.")
            # Debug list_document_versions logic manually
            pattern = f"{doc_id}_v*.encrypted"
            print(f"  Manual glob pattern: {pattern}")
            manual_versions = list(case_path.glob(pattern))
            print(f"  Manual glob results: {[f.name for f in manual_versions]}")
        else:
            print(f"  Latest version: {versions[0]}")
            meta_path = store._get_storage_path(doc_type_dir.name, case_id, doc_id, version=versions[0]).with_suffix(".meta")
            print(f"  Meta path: {meta_path}")
            print(f"  Meta exists: {meta_path.exists()}")

if __name__ == "__main__":
    sys.path.append("/src")
    debug_store()
