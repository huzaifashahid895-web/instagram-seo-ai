# backend/app/api/social_accounts.py — Social account OAuth and token storage
# Cost classification: FREE + OPEN SOURCE

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_oauth_state, decode_oauth_state, encrypt_secret, get_current_user
from app.models.social_account import Platform, SocialAccount
from app.models.user import User
from app.schemas.social_account import InstagramCallbackResponse, InstagramConnectResponse, SocialAccountResponse
from app.services.platforms.instagram.oauth import build_authorization_url, exchange_code_for_token


router = APIRouter()


@router.get("", response_model=list[SocialAccountResponse])
def list_social_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SocialAccount]:
    return list(db.scalars(select(SocialAccount).where(SocialAccount.user_id == current_user.id)).all())


@router.get("/instagram/connect", response_model=InstagramConnectResponse)
def connect_instagram(current_user: User = Depends(get_current_user)) -> InstagramConnectResponse:
    state = create_oauth_state(current_user.id)
    return InstagramConnectResponse(authorization_url=build_authorization_url(state), state=state)


@router.get("/callback", response_model=InstagramCallbackResponse)
def instagram_callback(
    code: str = Query(min_length=1),
    state: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> InstagramCallbackResponse:
    user_id = decode_oauth_state(state)
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OAuth state user is invalid")

    token_payload = exchange_code_for_token(code)
    account = db.scalar(
        select(SocialAccount).where(
            SocialAccount.user_id == user.id,
            SocialAccount.platform == Platform.INSTAGRAM,
            SocialAccount.platform_user_id == token_payload.platform_user_id,
        )
    )
    if account is None:
        account = SocialAccount(
            user_id=user.id,
            platform=Platform.INSTAGRAM,
            platform_user_id=token_payload.platform_user_id,
            username=token_payload.username,
            access_token_encrypted=encrypt_secret(token_payload.access_token),
        )
        db.add(account)
    else:
        account.username = token_payload.username
        account.access_token_encrypted = encrypt_secret(token_payload.access_token)

    account.refresh_token_encrypted = encrypt_secret(token_payload.refresh_token) if token_payload.refresh_token else None
    account.token_expires_at = token_payload.expires_at
    account.scopes = json.dumps(token_payload.scopes)
    account.is_active = True
    db.commit()
    db.refresh(account)
    return InstagramCallbackResponse(social_account=account)


@router.get("/{account_id}", response_model=SocialAccountResponse)
def get_social_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SocialAccount:
    account = db.get(SocialAccount, account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found")
    return account
