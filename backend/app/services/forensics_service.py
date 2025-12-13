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
        
        for doc_type in ["my_documents", "opposition_documents"]:
            try:
                # 1. Retrieve Document Content
                content = self.document_store.get_document_content(doc_type, case_id, doc_id)
                if not content:
                    continue
                
                if isinstance(content, str):
                    content = content.encode('utf-8')

                # Get metadata
                versions = self.document_store.list_document_versions(doc_type, case_id, doc_id)
                if not versions:
                    continue
                latest_version = versions[0]
                
                metadata = self.document_store.get_document_metadata(doc_type, case_id, doc_id, version=latest_version)
                if not metadata:
                    metadata = {}
                
                # 2. Run Analysis
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = Path(tmp.name)
                    
                try:
                    result = self.analyzer.analyze(tmp_path, metadata, doc_id=doc_id)
                finally:
                    try:
                        tmp_path.unlink()
                    except:
                        pass
                
                # 3. Save Results
                updates = {"forensic_analysis": result.dict()}
                self.document_store.update_document_metadata(doc_type, case_id, doc_id, updates)
                
                logger.info(f"Deep forensic analysis completed for {doc_id}")
                return result
                
            except Exception as e:
                logger.error(f"Deep forensic analysis failed for {doc_id} in {doc_type}: {e}", exc_info=True)
                continue

        logger.error(f"Document {doc_id} not found for deep forensics.")
        return None
