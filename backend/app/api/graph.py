from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..models.api import (
    GraphNeighborResponse,
    GraphQueryRequest,
    GraphQueryResponse,
)
from ..services.graph import GraphService, get_graph_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_graph_read,
)

router = APIRouter()

@router.get("/graph/neighbors/{node_id}", response_model=GraphNeighborResponse)
def get_graph_neighbors(
    node_id: str,
    _principal: Principal = Depends(authorize_graph_read),
    service: GraphService = Depends(get_graph_service),
) -> GraphNeighborResponse:
    nodes, edges = service.neighbors(node_id)
    return GraphNeighborResponse(
        nodes=[{"id": n.id, "type": n.type, "properties": n.properties} for n in nodes],
        edges=[{"source": e.source, "target": e.target, "type": e.type, "properties": e.properties} for e in edges]
    )


@router.post("/graph/query", response_model=GraphQueryResponse)
def execute_graph_query(
    request: GraphQueryRequest,
    _principal: Principal = Depends(authorize_graph_read),
    service: GraphService = Depends(get_graph_service),
) -> GraphQueryResponse:
    result = service.run_cypher(request.query)
    return GraphQueryResponse(
        records=result.get("records", []),
        summary=result.get("summary", {})
    )


class GraphAgentRequest(BaseModel):
    query: str
    case_id: str = "default_case"
    limit: int = 50

@router.post("/graph/agent", summary="Run a natural language graph query via agent")
def run_graph_agent(
    request: GraphAgentRequest,
    _principal: Principal = Depends(authorize_graph_read),
    service: GraphService = Depends(get_graph_service),
):
    """
    Executes a natural language query against the graph using the LLM to generate Cypher.
    """
    # We use execute_agent_cypher which handles text-to-cypher and execution
    # Note: execute_agent_cypher expects 'cypher' arg to be the *generated* cypher if we were passing it,
    # but here we want it to GENERATE it.
    # Wait, looking at GraphService.execute_agent_cypher signature:
    # def execute_agent_cypher(self, question: str, cypher: str, ...)
    # It takes BOTH question and cypher?
    # Let's re-read GraphService.execute_agent_cypher in Step 29.
    
    # It seems execute_agent_cypher validates the provided cypher against the question?
    # Or maybe it expects the caller to have already generated it?
    # Line 1185: prompt_info = self.text_to_cypher(question_text)
    # Line 1150: def execute_agent_cypher(self, question: str, cypher: str, ...)
    
    # If I want the SERVICE to generate it, I should call service.text_to_cypher first?
    # Or is there a method that does both?
    # text_to_cypher returns GraphTextToCypherResult which has .cypher
    
    # Let's implement the logic here:
    # 1. Generate Cypher from Question
    # 2. Execute Cypher
    
    generation = service.text_to_cypher(request.query)
    if not generation.cypher:
        # If generation failed or returned empty
        return {
            "question": request.query,
            "cypher": "",
            "records": [],
            "summary": {"error": "Could not generate valid Cypher query"},
            "warnings": generation.warnings
        }
        
    # Now execute
    result = service.execute_agent_cypher(
        question=request.query,
        cypher=generation.cypher,
        limit=request.limit
    )
    
    # Return a simplified response or the full GraphExecutionResult
    return result.to_dict()

