
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from backend.app.config import get_settings
# Assuming an LLM service is available for embedding models
# from backend.app.services.llm_service import get_embedding_model

class IndexingEmbeddingService:
    """
    A service for indexing document content and generating embeddings using LlamaIndex.
    """

    def __init__(self):
        settings = get_settings()
        if settings.qdrant_url:
            self.qdrant_client = QdrantClient(url=settings.qdrant_url)
        else:
            self.qdrant_client = QdrantClient(path=str(settings.vector_dir)) # Local Qdrant instance
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=settings.qdrant_collection,
        )
        # Assuming OpenAIEmbedding for now, but should be configurable via settings
        self.embed_model = OpenAIEmbedding(api_key=settings.ingestion_openai_api_key)
        self.node_parser = SentenceSplitter(chunk_size=settings.ingestion_chunk_size, chunk_overlap=settings.ingestion_chunk_overlap)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store, embed_model=self.embed_model)

    async def index_document(self, document_id: str, text_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Indexes a document's text content and stores its embeddings.
        """
        document = Document(
            text=text_content,
            metadata={**metadata, "document_id": document_id}
        )
        nodes = self.node_parser.get_nodes_from_documents([document])
        
        # Add nodes to the index
        self.index.insert_nodes(nodes)
        
        return {"status": "success", "document_id": document_id, "nodes_indexed": len(nodes)}

    async def query_index(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Queries the vector store for relevant documents based on a query string.
        """
        query_engine = self.index.as_query_engine(similarity_top_k=top_k)
        response = await query_engine.aquery(query)
        
        results = []
        for node in response.source_nodes:
            results.append({
                "text": node.text,
                "score": node.score,
                "metadata": node.metadata
            })
        return results
