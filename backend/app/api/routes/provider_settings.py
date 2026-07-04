from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.provider_settings import (
    ProviderSettingsResponse,
    ProviderSettingsUpdate,
)
from app.services.provider_settings import (
    provider_settings_report,
    update_runtime_provider_settings,
)


router = APIRouter(prefix="/settings/providers", tags=["settings"])


@router.get("", response_model=ProviderSettingsResponse)
def get_provider_settings(
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return provider_settings_report()


@router.put("", response_model=ProviderSettingsResponse)
def update_provider_settings(
    payload: ProviderSettingsUpdate,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    try:
        return update_runtime_provider_settings(payload.values)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
