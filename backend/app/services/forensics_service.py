import logging
from pathlib import Path
from typing import Optional
from backend.app.config import Settings
from backend.app.storage.document_store import DocumentStore
from backend.app.forensics.analyzer import ForensicAnalyzer
from backend.app.forensics.models import ForensicAnalysisResult

logger = logging.getLogger(__name__)

class ForensicsService:
    """
    Service for handling deep forensic analysis tasks.
    """
    def __init__(self, settings: Settings, document_store: DocumentStore):
        self.settings = settings
        self.document_store = document_store
        self.analyzer = ForensicAnalyzer()

    async def run_deep_forensics(self, doc_id: str, case_id: str) -> Optional[ForensicAnalysisResult]:
        """
        Runs deep forensic analysis on a document.
        """
        logger.info(f"Starting deep forensic analysis for doc_id={doc_id}")
        
        try:
            # 1. Retrieve Document Content
            # We need the raw file content. DocumentStore stores encrypted files.
            # We can use `get_document` to get decrypted content if available, 
            # or we might need to rely on the fact that `DocumentStore` handles decryption.
            
            # `get_document` returns a dictionary with 'content' (bytes) if load_content=True
            doc_data = self.document_store.get_document("opposition_documents", case_id, doc_id)
            if not doc_data:
                logger.error(f"Document {doc_id} not found for deep forensics.")
                return None
                
            content = doc_data.get("content")
            if not content:
                logger.error(f"Document content missing for {doc_id}.")
                return None
                
            metadata = doc_data.get("metadata", {})
            
            # 2. Run Analysis
            # We need a Path object for `analyze`, but `analyze` reads bytes.
            # Actually `analyze` takes `document_path: Path`.
            # We should probably refactor `analyze` to accept bytes directly, 
            # or write to a temp file.
            # Looking at `analyzer.py`, `analyze` does `document_path.read_bytes()`.
            # Let's write to a temp file.
            
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
                
            try:
                result = self.analyzer.analyze(tmp_path, metadata)
            finally:
                try:
                    tmp_path.unlink()
                except:
                    pass
            
            # 3. Save Results
            # We should update the document metadata with the forensic result.
            # The `ForensicAnalysisResult` is a Pydantic model.
            
            # Update metadata
            metadata["forensic_analysis"] = result.dict()
            self.document_store.update_document_metadata("opposition_documents", case_id, doc_id, metadata)
            
            logger.info(f"Deep forensic analysis completed for {doc_id}")
            return result
            
        except Exception as e:
            logger.error(f"Deep forensic analysis failed for {doc_id}: {e}", exc_info=True)
            raise e
