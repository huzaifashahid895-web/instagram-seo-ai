# backend/app/services/platforms/instagram/oauth.py — Instagram OAuth helpers
# Cost classification: FREE, REQUIRES INTERNET

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status

from app.config import settings


AUTHORIZATION_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
LONG_LIVED_TOKEN_URL = "https://graph.instagram.com/access_token"
ME_URL = "https://graph.instagram.com/me"
DEFAULT_SCOPES = (
    "instagram_business_basic",
    "instagram_business_content_publish",
    "instagram_business_manage_comments",
    "instagram_business_manage_insights",
)


@dataclass(frozen=True)
class InstagramTokenPayload:
    access_token: str
    refresh_token: str | None
    platform_user_id: str
    username: str
    expires_at: datetime | None
    scopes: list[str]
    raw_payload: dict[str, Any]


def build_authorization_url(state: str) -> str:
    if not settings.INSTAGRAM_APP_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INSTAGRAM_APP_ID must be configured before starting Instagram OAuth",
        )

    query = urllib.parse.urlencode(
        {
            "client_id": settings.INSTAGRAM_APP_ID,
            "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
            "scope": ",".join(DEFAULT_SCOPES),
            "response_type": "code",
            "state": state,
        }
    )
    return f"{AUTHORIZATION_URL}?{query}"


def exchange_code_for_token(code: str) -> InstagramTokenPayload:
    if not settings.INSTAGRAM_APP_ID or not settings.INSTAGRAM_APP_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Instagram OAuth credentials must be configured before handling callbacks",
        )

    short_lived = _post_form(
        TOKEN_URL,
        {
            "client_id": settings.INSTAGRAM_APP_ID,
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
            "code": code,
        },
    )
    short_token = short_lived.get("access_token")
    if not short_token:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Instagram token response missing access_token")

    long_lived = _get_json(
        LONG_LIVED_TOKEN_URL,
        {
            "grant_type": "ig_exchange_token",
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "access_token": short_token,
        },
    )
    access_token = long_lived.get("access_token", short_token)
    expires_in = long_lived.get("expires_in")

    profile = _get_json(
        ME_URL,
        {
            "fields": "user_id,username",
            "access_token": access_token,
        },
    )

    platform_user_id = str(profile.get("user_id") or profile.get("id") or short_lived.get("user_id") or "")
    username = str(profile.get("username") or "")
    if not platform_user_id or not username:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Instagram profile response missing user identity")

    expires_at = None
    if isinstance(expires_in, int):
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    return InstagramTokenPayload(
        access_token=access_token,
        refresh_token=None,
        platform_user_id=platform_user_id,
        username=username,
        expires_at=expires_at,
        scopes=list(DEFAULT_SCOPES),
        raw_payload={"short_lived": short_lived, "long_lived": long_lived, "profile": profile},
    )


def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=encoded, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    return _open_json(request)


def _get_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    request_url = f"{url}?{urllib.parse.urlencode(params)}"
    return _open_json(urllib.request.Request(request_url, method="GET"))


def _open_json(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Instagram OAuth error: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Instagram OAuth request failed") from exc
