# backend/app/api/settings.py — Runtime settings and model config routes
# Cost classification: FREE + OPEN SOURCE

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.model_config import ModelCapability, ModelConfig
from app.models.user import User
from app.schemas.settings import (
    ModelConfigCreate,
    ModelConfigResponse,
    ModelConfigUpdate,
    RuntimeSettingsResponse,
)


router = APIRouter()


@router.get("", response_model=RuntimeSettingsResponse)
def get_runtime_settings(_current_user: User = Depends(get_current_user)) -> RuntimeSettingsResponse:
    return RuntimeSettingsResponse(
        database_url=_redact_database_url(settings.DATABASE_URL),
        chroma_host=settings.CHROMA_HOST,
        chroma_port=settings.CHROMA_PORT,
        log_level=settings.LOG_LEVEL,
        cors_origins=settings.CORS_ORIGINS,
        jwt_configured=bool(settings.JWT_SECRET and not settings.JWT_SECRET.startswith("change-me")),
        encryption_configured=bool(settings.ENCRYPTION_KEY),
        instagram_app_configured=bool(settings.INSTAGRAM_APP_ID and settings.INSTAGRAM_APP_SECRET),
        instagram_redirect_uri=settings.INSTAGRAM_REDIRECT_URI,
    )


@router.get("/model-configs", response_model=list[ModelConfigResponse])
def list_model_configs(
    capability: ModelCapability | None = None,
    include_inactive: bool = True,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ModelConfig]:
    query = select(ModelConfig)
    if capability is not None:
        query = query.where(ModelConfig.capability == capability)
    if not include_inactive:
        query = query.where(ModelConfig.is_active.is_(True))
    return list(db.scalars(query.order_by(ModelConfig.capability, ModelConfig.provider_name, ModelConfig.model_name)).all())


@router.get("/model-configs/active/{capability}", response_model=ModelConfigResponse)
def get_active_model_config(
    capability: ModelCapability,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelConfig:
    model_config = db.scalar(
        select(ModelConfig).where(ModelConfig.capability == capability, ModelConfig.is_active.is_(True))
    )
    if model_config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active model config not found")
    return model_config


@router.post("/model-configs", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
def create_model_config(
    payload: ModelConfigCreate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelConfig:
    _validate_json_text(payload.parameters, "parameters")
    if payload.is_active:
        _deactivate_capability_configs(db, payload.capability)

    model_config = ModelConfig(**payload.model_dump())
    db.add(model_config)
    db.commit()
    db.refresh(model_config)
    return model_config


@router.get("/model-configs/{config_id}", response_model=ModelConfigResponse)
def get_model_config(
    config_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelConfig:
    return _get_model_config_or_404(db, config_id)


@router.patch("/model-configs/{config_id}", response_model=ModelConfigResponse)
def update_model_config(
    config_id: uuid.UUID,
    payload: ModelConfigUpdate,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelConfig:
    model_config = _get_model_config_or_404(db, config_id)
    updates = payload.model_dump(exclude_unset=True)
    _validate_json_text(updates.get("parameters"), "parameters")

    if updates.get("is_active") is True:
        _deactivate_capability_configs(db, model_config.capability, except_id=model_config.id)

    for field, value in updates.items():
        setattr(model_config, field, value)

    db.commit()
    db.refresh(model_config)
    return model_config


@router.post("/model-configs/{config_id}/activate", response_model=ModelConfigResponse)
def activate_model_config(
    config_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelConfig:
    model_config = _get_model_config_or_404(db, config_id)
    _deactivate_capability_configs(db, model_config.capability, except_id=model_config.id)
    model_config.is_active = True
    db.commit()
    db.refresh(model_config)
    return model_config


@router.delete("/model-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_config(
    config_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    model_config = _get_model_config_or_404(db, config_id)
    db.delete(model_config)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_model_config_or_404(db: Session, config_id: uuid.UUID) -> ModelConfig:
    model_config = db.get(ModelConfig, config_id)
    if model_config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model config not found")
    return model_config


def _deactivate_capability_configs(
    db: Session,
    capability: ModelCapability,
    except_id: uuid.UUID | None = None,
) -> None:
    query = select(ModelConfig).where(ModelConfig.capability == capability, ModelConfig.is_active.is_(True))
    for model_config in db.scalars(query):
        if except_id is None or model_config.id != except_id:
            model_config.is_active = False


def _validate_json_text(value: str | None, field_name: str) -> None:
    if value is None:
        return
    try:
        json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{field_name} must be valid JSON") from exc


def _redact_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    _credentials, host = rest.rsplit("@", 1)
    return f"{scheme}://***:***@{host}"
