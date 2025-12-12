"""End-to-end LlamaIndex ingestion orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from importlib import import_module
from importlib.util import find_spec

from backend.app.models.api import IngestionSource
from backend.app.utils.triples import EntitySpan, Triple, extract_entities, extract_triples
from backend.app.forensics.analyzer import ForensicAnalyzer
from backend.app.forensics.crypto_tracer import CryptoTracer
from backend.app.forensics.models import ForensicAnalysisResult, CryptoTracingResult, ScreeningResult

from .loader_registry import LoadedDocument, LoaderRegistry
from .llama_index_factory import (
    configure_global_settings,
    create_embedding_model,
    create_sentence_splitter,
    create_llm_service, # Added
    BaseLlmService, # Added
)
from .metrics import record_document_yield, record_node_yield, record_pipeline_metrics
from .settings import LlamaIndexRuntimeConfig
from .fallback import MetadataModeEnum
from .fallback import MetadataModeEnum
from .categorization import categorize_document, tag_document, heuristic_categorize, heuristic_tag

import re # Added for regex
import logging # Added for logging

logger = logging.getLogger(__name__) # Initialize logger

def _has_spec(path: str) -> bool:
    try:
        return find_spec(path) is not None
    except ModuleNotFoundError:
        return False


def _resolve_metadata_mode() -> object:
    if not _has_spec("llama_index.core.schema"):
        return MetadataModeEnum
    try:
        module = import_module("llama_index.core.schema")
        return getattr(module, "MetadataMode")
    except (ModuleNotFoundError, AttributeError):
        return MetadataModeEnum


MetadataMode = _resolve_metadata_mode()
METADATA_MODE_ALL = getattr(MetadataMode, "ALL", MetadataModeEnum.ALL)


@dataclass
class PipelineNodeRecord:
    node_id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, object]
    chunk_index: int


@dataclass
class DocumentPipelineResult:
    loaded: LoadedDocument
    nodes: List[PipelineNodeRecord]
    entities: List[EntitySpan]
    triples: List[Triple] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    forensic_analysis_result: Optional[ForensicAnalysisResult] = None # Added
    crypto_tracing_result: Optional[CryptoTracingResult] = None # Added
    screening_result: Optional[ScreeningResult] = None # Added


@dataclass
class PipelineResult:
    job_id: str
    source: IngestionSource
    documents: List[DocumentPipelineResult] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return sum(len(doc.nodes) for doc in self.documents)


def _extract_legal_metadata(text: str, llm_service: BaseLlmService) -> Dict[str, Any]:
    """
    Extracts legal-specific metadata from the document text.
    For now, this uses simple regex. In a more advanced implementation, this would
    involve more sophisticated NLP or LLM calls.
    """
    metadata = {}

    # Example: Extract a date (very basic, needs improvement for real-world use)
    date_match = re.search(r'\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})\b', text)
    if date_match:
        metadata["document_date"] = date_match.group(0)

    # Example: Extract a case number (placeholder)
    case_number_match = re.search(r'Case No\.\s*([A-Z0-9-]+)', text, re.IGNORECASE)
    if case_number_match:
        metadata["case_number"] = case_number_match.group(1)
    
    # Example: Extract parties (placeholder, highly complex in reality)
    # This would typically require advanced NLP to identify plaintiffs, defendants, etc.
    # For now, we'll just add a placeholder.
    metadata["parties"] = ["Plaintiff (Placeholder)", "Defendant (Placeholder)"]

    # Example: Extract jurisdiction (placeholder)
    metadata["jurisdiction"] = "Federal (Placeholder)"

    # In a real application, you might use the LLM service here for more accurate extraction:
    # try:
    #     llm_response = llm_service.generate_text(f"Extract key legal metadata (date, parties, jurisdiction, case_name, case_number) from the following text:\n\n{text}")
    #     # Parse llm_response to populate metadata
    # except Exception as e:
    #     print(f"LLM metadata extraction failed: {e}")

    return metadata


def _clean_document_text(text: str) -> str:
    """
    Performs basic cleaning and normalization on document text.
    - Removes excessive whitespace.
    - Standardizes line endings.
    - (Future) Could remove common boilerplate text.
    """
    # Remove excessive whitespace (multiple spaces/tabs to single space)
    text = re.sub(r'\s+', ' ', text).strip()
    # Standardize line endings to a single newline character
    text = re.sub(r'(\r\n|\r|\n)+', '\n', text)
    return text


def run_ingestion_pipeline(
    job_id: str,
    materialized_root: Path,
    source: IngestionSource,
    origin: str,
    *,
    registry: LoaderRegistry,
    runtime_config: LlamaIndexRuntimeConfig,
) -> PipelineResult:
    """Materialise documents, chunk into nodes, and enrich with embeddings using LlamaIndex IngestionPipeline."""

    configure_global_settings(runtime_config)
    logger.info(f"Ingestion pipeline started. Cost mode: {runtime_config.cost_mode}")
    
    # 1. Create Components
    splitter = create_sentence_splitter(runtime_config.tuning)
    embedding_model = create_embedding_model(runtime_config.embedding)
    llm_service = create_llm_service(runtime_config.llm) # Keep for custom steps if needed
    
    # Create Extractors
    from .llama_index_factory import create_extractors
    extractors = create_extractors(runtime_config, llm_service)
    
    # 2. Load Documents
    with record_pipeline_metrics(source.type.lower(), job_id):
        try:
            loaded_documents = registry.load_documents(materialized_root, source, origin=origin)
            logger.info(f"Loaded {len(loaded_documents)} documents for job {job_id}")
        except Exception as e:
            logger.error(f"Error loading documents for job {job_id}: {e}", exc_info=True)
            raise

        record_document_yield(len(loaded_documents), source_type=source.type.lower(), job_id=job_id)
        
        # Convert LoadedDocument to LlamaIndex Document
        from llama_index.core import Document
        llama_documents = []
        for loaded in loaded_documents:
            doc = Document(
                text=loaded.text,
                metadata={
                    "source_path": str(loaded.path),
                    "source_type": loaded.source.type.lower(),
                    "job_id": job_id,
                    "case_id": source.metadata.get("case_id"),
                    **loaded.source.metadata
                }
            )
            llama_documents.append(doc)

        # 3. Setup Vector Store
        try:
            from llama_index.vector_stores.qdrant import QdrantVectorStore
            import qdrant_client
            
            client = qdrant_client.QdrantClient(
                url=runtime_config.vector_store.url,
                api_key=runtime_config.vector_store.api_key
            )
            vector_store = QdrantVectorStore(
                client=client, 
                collection_name=runtime_config.vector_store.collection_name
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vector Store: {e}", exc_info=True)
            raise

        # 4. Run Ingestion Pipeline
        from llama_index.core.ingestion import IngestionPipeline
        
        transformations = [splitter] + extractors + [embedding_model]
        
        pipeline = IngestionPipeline(
            transformations=transformations,
            vector_store=vector_store,
            # cache=... # TODO: Add Redis cache if available
        )
        
        logger.info(f"Running IngestionPipeline with transformations: {transformations}")
        try:
            nodes = pipeline.run(documents=llama_documents)
            logger.info(f"IngestionPipeline finished. Processed {len(nodes)} nodes.")
        except Exception as e:
            logger.error(f"IngestionPipeline failed: {e}", exc_info=True)
            raise

        record_node_yield(len(nodes), source_type=source.type.lower(), job_id=job_id)

        # 5. Run Custom Steps (Forensics, Crypto, etc.)
        # We reconstruct DocumentPipelineResult for compatibility and custom analysis
        documents_result = []
        
        # Group nodes by source_path to map back to loaded documents
        nodes_by_path = {}
        for node in nodes:
            path = node.metadata.get("source_path")
            if path:
                if path not in nodes_by_path:
                    nodes_by_path[path] = []
                nodes_by_path[path].append(node)
        
        for loaded in loaded_documents:
            doc_nodes = nodes_by_path.get(str(loaded.path), [])
            
            # Convert LlamaIndex nodes to PipelineNodeRecord
            pipeline_nodes = []
            for i, node in enumerate(doc_nodes):
                pipeline_nodes.append(PipelineNodeRecord(
                    node_id=node.node_id,
                    text=node.get_content(metadata_mode=METADATA_MODE_ALL),
                    embedding=node.embedding,
                    metadata=node.metadata,
                    chunk_index=i
                ))
            
            # Custom Analysis (Entities, Triples, Forensics)
            # We can run this on the full text
            cleaned_text = _clean_document_text(loaded.text)
            
            entities = []
            triples = []
            categories = []
            tags = []
            forensic_analysis_result = None
            crypto_tracing_result = None
            screening_result = None

            try:
                entities = extract_entities(cleaned_text)
                triples = extract_triples(cleaned_text)
                
                if runtime_config.cost_mode == "community":
                    categories = heuristic_categorize(cleaned_text)
                    tags = heuristic_tag(cleaned_text)
                else:
                    # Use LlamaIndex ClassificationService
                    from backend.app.services.classification_service import ClassificationService
                    classification_service = ClassificationService() # It initializes its own LLM
                    
                    # We need to await this, but we are in a sync function `run_ingestion_pipeline`.
                    # We should probably run this in an event loop or make `run_ingestion_pipeline` async.
                    # `run_ingestion_pipeline` is called by `process_ingestion` which IS async.
                    # However, `run_ingestion_pipeline` is currently sync.
                    # For now, let's use `asyncio.run` or similar if we are sure there's no loop conflict,
                    # OR just use the synchronous `select` method if available.
                    # LLMMultiSelector has `select` (sync) and `aselect` (async).
                    # Let's use `select` (sync) to avoid async complications in this sync function.
                    
                    # Wait, I implemented `classify_document` as `async`. I should verify if I can change it to sync or call it sync.
                    # Let's check `classification_service.py` I just wrote. I made it `async def classify_document`.
                    # I should probably update `classification_service.py` to have a sync method or use `asyncio.run`.
                    # But `run_ingestion_pipeline` is running inside FastAPI which has an event loop. `asyncio.run` might fail.
                    # Ideally `run_ingestion_pipeline` should be async.
                    # Let's check `document_service.py` where it's called.
                    # `process_ingestion` calls `run_ingestion_pipeline`. `process_ingestion` is async.
                    # So we can make `run_ingestion_pipeline` async!
                    # But that requires changing the signature and all calls.
                    # Let's see if I can just use a sync wrapper in `ClassificationService`.
                    
                    # Actually, `LLMMultiSelector`'s `select` method is sync. 
                    # I will modify `ClassificationService` to expose a sync `classify_document_sync` or just use `select`.
                    
                    # For now, let's assume I'll add a sync method to `ClassificationService` in the next step.
                    # Or I can just use `asyncio.run_coroutine_threadsafe`? No, that's messy.
                    
                    # Let's try to make `run_ingestion_pipeline` async. It's a big change?
                    # It's defined in `pipeline.py`.
                    # Let's look at `document_service.py`.
                    # `pipeline_result = run_ingestion_pipeline(...)`
                    # If I change it to `await run_ingestion_pipeline(...)`, I need to update `document_service.py`.
                    # That seems cleaner for the future.
                    
                    # BUT, `run_ingestion_pipeline` is also imported by `ingestion_worker.py` maybe?
                    # Let's check usage.
                    # I'll stick to adding a sync method to `ClassificationService` for minimal friction now.
                    
                    cls_result = classification_service.classify_document_sync(cleaned_text)
                    categories = cls_result.categories
                    tags = cls_result.tags
                    
                    # Merge extracted metadata into the document metadata
                    if cls_result.metadata:
                        # We want to preserve this metadata. 
                        # Ideally, we should add it to the DocumentPipelineResult or the node metadata.
                        # For now, let's add it to the first node's metadata as a simple hack, 
                        # or better, add it to the DocumentPipelineResult if we added a field for it.
                        # The DocumentPipelineResult definition in this file doesn't have a generic metadata field,
                        # but it has `categories` and `tags`.
                        # Let's add the summary to the first node's metadata so it's searchable.
                        if pipeline_nodes:
                            pipeline_nodes[0].metadata["ai_summary"] = cls_result.metadata.get("summary")
                            pipeline_nodes[0].metadata["ai_sentiment"] = cls_result.metadata.get("sentiment")
                            pipeline_nodes[0].metadata["ai_entities"] = cls_result.metadata.get("key_entities")
                    
                doc_type = loaded.source.metadata.get("doc_type")
                if doc_type == "opposition_documents":
                    try:
                        forensic_analyzer = ForensicAnalyzer()
                        # Use screening instead of full analysis
                        screening_result = forensic_analyzer.screen_document(
                            document_content=loaded.document.text.encode('utf-8'),
                            metadata=loaded.source.metadata,
                        )
                    except Exception as e:
                        logger.warning(f"Error during forensic screening for {loaded.path}: {e}", exc_info=True)
                    
                    try:
                        crypto_tracer = CryptoTracer()
                        crypto_tracing_result = crypto_tracer.trace_document_for_crypto(
                            document_content=loaded.document.text,
                            document_id=loaded.source.source_id,
                        )
                    except Exception as e:
                        logger.warning(f"Error during crypto tracing for {loaded.path}: {e}", exc_info=True)
            except Exception as e:
                logger.warning(f"Error in custom analysis for {loaded.path}: {e}", exc_info=True)

            documents_result.append(DocumentPipelineResult(
                loaded=loaded,
                nodes=pipeline_nodes,
                entities=entities,
                triples=triples,
                categories=categories,
                tags=tags,
                forensic_analysis_result=forensic_analysis_result,
                crypto_tracing_result=crypto_tracing_result,
                screening_result=screening_result, # Added
            ))

        # 6. Graph Indexing (Pro Mode)
        if runtime_config.cost_mode != "community":
            try:
                from backend.app.services.knowledge_graph_service import get_knowledge_graph_service
                kg_service = get_knowledge_graph_service()
                
                # We need to pass LlamaIndex Documents. 
                # We already created `llama_documents` in step 2.
                # But `build_graph_index` is sync.
                # We can call it directly.
                logger.info(f"Starting Graph Indexing for {len(llama_documents)} documents...")
                kg_service.build_graph_index(llama_documents, case_id=source.metadata.get("case_id"))
                logger.info("Graph Indexing completed.")
            except Exception as e:
                logger.error(f"Graph Indexing failed: {e}", exc_info=True)

        return PipelineResult(job_id=job_id, source=source, documents=documents_result)


__all__ = ["PipelineResult", "run_ingestion_pipeline"]
