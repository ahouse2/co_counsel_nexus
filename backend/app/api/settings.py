from fastapi import APIRouter, Depends, HTTPException, status
from ..models.api import (
    ModelCatalogResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)
from ..services.settings import (
    SettingsService,
    SettingsValidationError,
    get_settings_service,
)
from ..security.dependencies import (
    authorize_settings_read,
    authorize_settings_write,
)
from ..security.authz import Principal
from ..storage.settings_store import SettingsStoreError

router = APIRouter()

@router.get("/settings", response_model=SettingsResponse)
def read_application_settings(
    _principal: Principal = Depends(authorize_settings_read),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    return service.snapshot()


@router.put("/settings", response_model=SettingsResponse)
def update_application_settings(
    request: SettingsUpdateRequest,
    _principal: Principal = Depends(authorize_settings_write),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    try:
        return service.update(request)
    except SettingsValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SettingsStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to persist settings",
        ) from exc


@router.get("/settings/models", response_model=ModelCatalogResponse)
def list_model_catalog(
    _principal: Principal = Depends(authorize_settings_read),
    service: SettingsService = Depends(get_settings_service),
) -> ModelCatalogResponse:
    return service.model_catalog()
