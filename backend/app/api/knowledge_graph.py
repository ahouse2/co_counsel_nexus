from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional

from backend.app.knowledge_graph.schema import KnowledgeGraphData, BaseNode, BaseRelationship
from backend.app.services.knowledge_graph_service import KnowledgeGraphService, get_knowledge_graph_service

router = APIRouter()

@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest nodes and relationships into the knowledge graph"
)
async def ingest_knowledge_graph_data(
    graph_data: KnowledgeGraphData,
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        kg_service.ingest_data(graph_data)
        return {"message": "Knowledge graph data ingested successfully."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to ingest data: {e}")

@router.post(
    "/query",
    response_model=KnowledgeGraphData,
    summary="Query the knowledge graph with a Cypher query and return structured data"
)
async def query_knowledge_graph_data(
    cypher_query: str,
    parameters: Optional[Dict[str, Any]] = None,
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        graph_data = kg_service.get_graph_data(cypher_query, parameters)
        return graph_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to query data: {e}")

@router.post(
    "/query-mermaid",
    response_model=Optional[str],
    summary="Query the knowledge graph with a Cypher query and return a Mermaid graph definition"
)
async def query_knowledge_graph_mermaid(
    cypher_query: str,
    parameters: Optional[Dict[str, Any]] = None,
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        mermaid_definition = kg_service.get_mermaid_graph(cypher_query, parameters)
        return mermaid_definition
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate Mermaid graph: {e}")
