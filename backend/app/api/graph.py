from fastapi import APIRouter, Depends

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
