# backend/app/core/security.py — Local auth, signed tokens, and token encryption
# Cost classification: LOCAL ONLY

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.db import get_db
from app.models.user import User


PBKDF2_ITERATIONS = 260_000
TOKEN_VERSION = "aism1"
ENCRYPTION_VERSION = "v1"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _secret_bytes(secret: str, setting_name: str) -> bytes:
    if not secret or secret.startswith("change-me"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{setting_name} must be configured before using this endpoint",
        )
    return secret.encode("utf-8")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = hashed_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = _b64decode(salt_b64)
        expected = _b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: uuid.UUID, expires_delta: timedelta | None = None) -> str:
    now = int(time.time())
    expiry = now + int((expires_delta or timedelta(hours=settings.JWT_EXPIRY_HOURS)).total_seconds())
    payload = {"sub": str(user_id), "iat": now, "exp": expiry, "typ": "access"}
    payload_b64 = _b64encode(_json_dumps(payload).encode("utf-8"))
    signature = hmac.new(_secret_bytes(settings.JWT_SECRET, "JWT_SECRET"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{TOKEN_VERSION}.{payload_b64}.{_b64encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        version, payload_b64, signature_b64 = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    if version != TOKEN_VERSION:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    expected = hmac.new(_secret_bytes(settings.JWT_SECRET, "JWT_SECRET"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    try:
        provided = _b64decode(signature_b64)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired")
    return payload


def create_oauth_state(user_id: uuid.UUID) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + 600, "nonce": _b64encode(os.urandom(12))}
    payload_b64 = _b64encode(_json_dumps(payload).encode("utf-8"))
    signature = hmac.new(_secret_bytes(settings.JWT_SECRET, "JWT_SECRET"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{TOKEN_VERSION}.{payload_b64}.{_b64encode(signature)}"


def decode_oauth_state(state: str) -> uuid.UUID:
    payload = decode_access_token(state)
    return uuid.UUID(payload["sub"])


def _encryption_keys() -> tuple[bytes, bytes]:
    key_material = _secret_bytes(settings.ENCRYPTION_KEY, "ENCRYPTION_KEY")
    enc_key = hmac.new(key_material, b"aism-token-encryption", hashlib.sha256).digest()
    mac_key = hmac.new(key_material, b"aism-token-authentication", hashlib.sha256).digest()
    return enc_key, mac_key


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        counter_bytes = counter.to_bytes(4, "big")
        blocks.append(hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_secret(plaintext: str) -> str:
    enc_key, mac_key = _encryption_keys()
    nonce = os.urandom(16)
    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext = bytes(a ^ b for a, b in zip(plaintext_bytes, _keystream(enc_key, nonce, len(plaintext_bytes))))
    signed = nonce + ciphertext
    tag = hmac.new(mac_key, signed, hashlib.sha256).digest()
    return f"{ENCRYPTION_VERSION}.{_b64encode(signed + tag)}"


def decrypt_secret(encrypted_value: str) -> str:
    try:
        version, payload_b64 = encrypted_value.split(".", 1)
        payload = _b64decode(payload_b64)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid encrypted value") from exc

    if version != ENCRYPTION_VERSION or len(payload) < 49:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid encrypted value")

    enc_key, mac_key = _encryption_keys()
    signed = payload[:-32]
    tag = payload[-32:]
    expected = hmac.new(mac_key, signed, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, tag):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encrypted value authentication failed")

    nonce = signed[:16]
    ciphertext = signed[16:]
    plaintext = bytes(a ^ b for a, b in zip(ciphertext, _keystream(enc_key, nonce, len(ciphertext))))
    return plaintext.decode("utf-8")


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user
