from fastapi import HTTPException
from ..services.errors import WorkflowException, http_status_for_error

def raise_workflow_exception(exc: WorkflowException) -> None:
    status_code = exc.status_code or http_status_for_error(exc.error)
    raise HTTPException(status_code=status_code, detail=exc.error.to_dict()) from exc
