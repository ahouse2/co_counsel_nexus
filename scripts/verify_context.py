import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.config import get_settings
from backend.app.services.document_service import DocumentService
from backend.app.services.context_service import ContextService
from backend.app.storage.document_store import DocumentStore
from backend.ingestion.loader_registry import LoaderRegistry
from backend.ingestion.settings import build_runtime_config, build_ocr_config
from backend.ingestion.ocr import OcrEngine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify():
    settings = get_settings()
    
    # 1. Setup Services
    document_store = DocumentStore(base_dir=settings.document_storage_path, encryption_key=settings.encryption_key)
    ocr_config = build_ocr_config(settings)
    ocr_engine = OcrEngine(config=ocr_config, logger=logger)
    runtime_config = build_runtime_config(settings)
    loader_registry = LoaderRegistry(runtime_config=runtime_config, ocr_engine=ocr_engine, logger=logger)
    materialized_root = settings.document_storage_path.parent / "materialized"
    materialized_root.mkdir(parents=True, exist_ok=True)
    
    document_service = DocumentService(
        document_store=document_store,
        loader_registry=loader_registry,
        runtime_config=runtime_config,
        materialized_root=materialized_root
    )
    
    context_service = ContextService(settings)
    
    # 2. Ingest a Test Document
    case_id = "test_case_context"
    doc_content = b"The suspect, John Doe, was seen at the scene of the crime on January 1st, 2024. He was wearing a red jacket."
    file_name = "suspect_report.txt"
    
    logger.info("Uploading and ingesting test document...")
    result = await document_service.upload_document(
        case_id=case_id,
        doc_type="my_documents",
        file_content=doc_content,
        file_name=file_name,
        run_pipeline=True # Run immediately
    )
    
    doc_id = result["doc_id"]
    logger.info(f"Document ingested with ID: {doc_id}")
    
    # 3. Verify Persistence in Qdrant
    logger.info("Verifying persistence in Qdrant...")
    # We can verify by querying
    
    # 4. Query Context
    query = "Who is the suspect?"
    logger.info(f"Querying context: '{query}'")
    
    query_result = await context_service.query_context(query, case_id)
    
    logger.info(f"Query Result: {query_result}")
    
    if query_result["count"] > 0:
        print("\nSUCCESS: Context found!")
        for res in query_result["results"]:
            print(f" - {res['text'][:100]}... (Score: {res['score']})")
            print(f"   Metadata: {res['metadata']}")
            
            # Verify new metadata fields
            if "document_title" in res['metadata']:
                print(f"   -> Title extracted: {res['metadata']['document_title']}")
            if "section_summary" in res['metadata']:
                print(f"   -> Summary extracted: {res['metadata']['section_summary']}")
            if "excerpt_keywords" in res['metadata']:
                print(f"   -> Keywords extracted: {res['metadata']['excerpt_keywords']}")
                
            if "John Doe" in res['text']:
                print("   -> Correctly identified suspect.")
    else:
        print("\nFAILURE: No context found.")

if __name__ == "__main__":
    asyncio.run(verify())
