"""
Test file for folder ingestion functionality.
This test creates a simple test to upload a folder with multiple files.
"""
import pytest
import io
import zipfile
from pathlib import Path

@pytest.mark.asyncio
async def test_upload_directory():
    """Test folder upload with multiple files."""
    from backend.app.services.document_service import DocumentService
    from backend.app.storage.document_store import DocumentStore
    from backend.ingestion.loader_registry import LoaderRegistry
    from backend.ingestion.settings import build_runtime_config, build_ocr_config
    from backend.ingestion.ocr import OcrEngine
    from backend.app.config import get_settings
    import logging
    import tempfile
    
    # Setup
    settings = get_settings()
    document_store = DocumentStore(
        base_dir=Path(tempfile.mkdtemp()), 
        encryption_key=settings.encryption_key
    )
    
    logger = logging.getLogger(__name__)
    ocr_config = build_ocr_config(settings)
    ocr_engine = OcrEngine(config=ocr_config, logger=logger)
    runtime_config = build_runtime_config(settings)
    loader_registry = LoaderRegistry(
        runtime_config=runtime_config, 
        ocr_engine=ocr_engine, 
        logger=logger
    )
    
    materialized_root = Path(tempfile.mkdtemp())
    
    service = DocumentService(
        document_store=document_store,
        loader_registry=loader_registry,
        runtime_config=runtime_config,
        materialized_root=materialized_root
    )
    
    # Create a test zip file with multiple files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        zipf.writestr('test_folder/file1.txt', b'This is test file 1')
        zipf.writestr('test_folder/file2.txt', b'This is test file 2')
        zipf.writestr('test_folder/subfolder/file3.txt', b'This is test file 3')
    
    zip_content = zip_buffer.getvalue()
    
    # Test upload_directory
    results = await service.upload_directory(
        case_id='test_case',
        zip_content=zip_content,
        api_keys=None
    )
    
    # Verify results
    assert len(results) == 3, f"Expected 3 files, got {len(results)}"
    
    # Check that all files were queued
    for result in results:
        assert result['ingestion_status'] == 'queued'
        assert result['case_id'] == 'test_case'
        assert result['doc_type'] == 'my_documents'
        assert result['origin'] == 'folder_upload'
        
    print(f"✅ Test passed: Successfully uploaded {len(results)} files from folder")
    return results


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_upload_directory())
