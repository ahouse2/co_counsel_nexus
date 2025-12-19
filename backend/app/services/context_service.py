import logging
from typing import List, Optional
from backend.app.config import Settings
from backend.ingestion.settings import build_runtime_config
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

logger = logging.getLogger(__name__)

class ContextService:
    """
    Service for querying document context using LlamaIndex + KG.
    Enhanced with Knowledge Graph integration for hybrid retrieval.
    """
    def __init__(self, settings: Settings, kg_service: Optional[KnowledgeGraphService] = None):
        self.settings = settings
        self.runtime_config = build_runtime_config(settings)
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        # Initialize Qdrant Client
        self.client = qdrant_client.QdrantClient(
            url=self.runtime_config.vector_store.url,
            api_key=self.runtime_config.vector_store.api_key
        )
        
        # Initialize Vector Store
        self.vector_store = QdrantVectorStore(
            client=self.client, 
            collection_name=self.runtime_config.vector_store.collection_name
        )
        
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    async def query_context(self, query: str, case_id: str, top_k: int = 5) -> dict:
        """
        Queries the vector store for relevant context.
        """
        try:
            # Create Index from Vector Store (no new nodes, just loading existing)
            index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                embed_model=None # We might need to load the embedding model here if not global
            )
            
            # We need to ensure the embedding model is configured globally or passed here
            # For now, let's assume global configuration or rely on the one in runtime_config
            from backend.ingestion.llama_index_factory import create_embedding_model, create_llm_service
            
            embed_model = create_embedding_model(self.runtime_config.embedding)
            llm_service = create_llm_service(self.runtime_config.llm)
            
            # Create Query Engine
            # We can use the low-level retriever or the high-level query engine
            # For "Context Engine", we probably want the retrieved nodes + a synthesized answer
            
            # Configure retriever with filters if needed (e.g., by case_id)
            # Qdrant supports filtering. LlamaIndex supports MetadataFilters.
            from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
            
            filters = MetadataFilters(
                filters=[
                    ExactMatchFilter(key="case_id", value=case_id)
                ]
            )
            
            # Note: We need to ensure 'case_id' is actually in the metadata of the nodes.
            # In document_service.py, we added it to the ingestion_source metadata.
            # In pipeline.py, we added source metadata to node metadata.
            # So it should be there.
            
            query_engine = index.as_query_engine(
                similarity_top_k=top_k,
                filters=filters,
                embed_model=embed_model,
                llm=None # We might want to just return nodes for now, or use LLM for answer
            )
            
            # If we want just the nodes (context), we can use the retriever
            retriever = index.as_retriever(
                similarity_top_k=top_k,
                filters=filters,
                embed_model=embed_model
            )
            
            nodes = retriever.retrieve(query)
            
            results = []
            for node in nodes:
                results.append({
                    "text": node.text,
                    "score": node.score,
                    "metadata": node.metadata,
                    "node_id": node.node_id
                })
                
            return {
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error querying context: {e}", exc_info=True)
            raise e
