from fastapi import APIRouter, Depends

from ..models.api import (
    GraphNeighborResponse,
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
    return service.get_neighbors(node_id)
