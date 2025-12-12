from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
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

# New endpoints for KnowledgeGraphManager methods

@router.post("/cypher-query", summary="Run a raw Cypher query", response_model=List[Dict[str, Any]])
async def run_cypher_query(
    query: str = Body(..., embed=True),
    params: Optional[Dict[str, Any]] = Body(None, embed=True),
    cache: bool = Query(True),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        result = await kg_service.run_cypher_query(query, params, cache)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cypher query failed: {e}")

@router.get("/legal-references/search", summary="Search legal references", response_model=List[Dict[str, Any]])
async def search_legal_references(
    query: str = Query(...),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        results = await kg_service.search_legal_references(query)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

@router.get("/node/{node_id}", summary="Retrieve a node by ID", response_model=Optional[Dict[str, Any]])
async def get_node_by_id(
    node_id: int,
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        node = await kg_service.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        return node
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve node: {e}")

@router.get("/node/{node_id}/relationships", summary="Retrieve relationships for a node", response_model=List[Dict[str, Any]])
async def get_node_relationships(
    node_id: int,
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        relationships = await kg_service.get_relationships(node_id)
        return relationships
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve relationships: {e}")

@router.get("/export-graph", summary="Export the entire graph as an interactive HTML file", response_model=str)
async def export_graph(
    output_path: str = Query("graph.json"),
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        # Assuming export_graph returns the path or content
        html_path = await kg_service.export_graph(output_path)
        return html_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export graph: {e}")

@router.get("/cause-subgraph/{cause}", summary="Retrieve subgraph for a cause of action", response_model=Dict[str, List[Dict[str, Any]]])
async def get_cause_subgraph(
    cause: str,
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        nodes, edges = await kg_service.get_cause_subgraph(cause)
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cause subgraph: {e}")

@router.get("/cause-support-scores", summary="Return satisfaction counts and confidence for each cause of action", response_model=List[Dict[str, Any]])
async def get_cause_support_scores(
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        scores = await kg_service.cause_support_scores()
        return scores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cause support scores: {e}")

@router.get("/subgraph/{label}", summary="Retrieve a subgraph for nodes with a given label", response_model=Dict[str, List[Dict[str, Any]]])
async def get_subgraph_by_label(
    label: str,
    kg_service: KnowledgeGraphService = Depends(get_knowledge_graph_service)
):
    try:
        nodes, edges = await kg_service.get_subgraph(label)
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve subgraph by label: {e}")
