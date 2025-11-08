from fastapi import APIRouter, Depends, Response, WebSocket, Request, status
from ..telemetry.billing import (
    BillingEventType,
    record_billing_event,
)
from ..graphql import graphql_app
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_timeline,
)

router = APIRouter()

def _apply_graphql_cors_headers(request: Request, response: Response) -> None:
    """Ensure GraphQL HTTP responses include negotiated CORS headers."""

    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers.setdefault("Access-Control-Allow-Credentials", "true")
        vary_header = response.headers.get("Vary")
        if vary_header:
            vary_values = {value.strip() for value in vary_header.split(",") if value}
            vary_values.add("Origin")
            response.headers["Vary"] = ", ".join(sorted(vary_values))
        else:
            response.headers["Vary"] = "Origin"

    allow_headers = request.headers.get(
        "access-control-request-headers", "authorization,content-type"
    )
    requested_method = request.headers.get("access-control-request-method")
    allow_methods_list = ["GET", "POST", "OPTIONS"]
    if requested_method:
        requested_method_upper = requested_method.upper()
        if requested_method_upper not in allow_methods_list:
            allow_methods_list.insert(0, requested_method_upper)
    allow_methods = ", ".join(dict.fromkeys(allow_methods_list))

    response.headers.setdefault("Access-Control-Allow-Headers", allow_headers)
    response.headers.setdefault("Access-Control-Allow-Methods", allow_methods)


@router.options("/graphql", include_in_schema=False)
async def graphql_http_options(request: Request) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    requested_method = request.headers.get("access-control-request-method")
    allow_methods_list = ["GET", "POST", "OPTIONS"]
    if requested_method:
        requested_method_upper = requested_method.upper()
        if requested_method_upper not in allow_methods_list:
            allow_methods_list.insert(0, requested_method_upper)
    allow_methods = ", ".join(dict.fromkeys(allow_methods_list))
    response.headers["Allow"] = allow_methods
    _apply_graphql_cors_headers(request, response)
    return response
    """Handle GraphQL CORS preflight with explicit allow headers."""

    origin = request.headers.get("origin") or "*"
    requested_headers = request.headers.get("access-control-request-headers")
    allow_headers = requested_headers or "Authorization, Content-Type"

    headers: dict[str, str] = {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "OPTIONS, GET, POST",
        "Access-Control-Allow-Headers": allow_headers,
        "Access-Control-Max-Age": "86400",
    }

    vary_headers: list[str] = ["Origin"]
    if requested_headers:
        vary_headers.append("Access-Control-Request-Headers")
    headers["Vary"] = ", ".join(dict.fromkeys(vary_headers))

    # Only advertise credential support when responding to a specific origin.
    if origin != "*":
        headers["Access-Control-Allow-Credentials"] = "true"

    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=headers)


@router.api_route("/graphql", methods=["GET", "POST"])
async def graphql_http(
    request: Request,
    principal: Principal = Depends(authorize_timeline),
) -> Response:
    request.state.principal = principal
    record_billing_event(
        principal,
        BillingEventType.TIMELINE,
        attributes={
            "endpoint": "/graphql",
            "method": request.method,
        },
    )
    response = await graphql_app.handle_request(request)
    _apply_graphql_cors_headers(request, response)
    return response


@router.websocket("/graphql")
async def graphql_websocket(
    websocket: WebSocket,
    principal: Principal = Depends(authorize_timeline),
) -> None:
    websocket.state.principal = principal
    record_billing_event(
        principal,
        BillingEventType.TIMELINE,
        attributes={
            "endpoint": "/graphql",
            "method": "WEBSOCKET",
        },
    )
    await graphql_app.handle_websocket(websocket)
