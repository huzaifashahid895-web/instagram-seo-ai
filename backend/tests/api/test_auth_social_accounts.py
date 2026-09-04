# backend/tests/api/test_auth_social_accounts.py — Step 4 auth and social account tests
# Cost classification: FREE + OPEN SOURCE

import unittest
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api import auth, social_accounts
from app.config import settings
from app.core.db import Base
from app.core.security import decrypt_secret, get_current_user
from app.models.social_account import Platform, SocialAccount
from app.services.platforms.instagram.oauth import InstagramTokenPayload


class AuthSocialAccountsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / "tmp" / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_dir / "test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        self.original_jwt_secret = settings.JWT_SECRET
        self.original_encryption_key = settings.ENCRYPTION_KEY
        self.original_instagram_app_id = settings.INSTAGRAM_APP_ID
        self.original_instagram_app_secret = settings.INSTAGRAM_APP_SECRET
        settings.JWT_SECRET = "test-jwt-secret"
        settings.ENCRYPTION_KEY = "test-encryption-key"
        settings.INSTAGRAM_APP_ID = "test-instagram-app-id"
        settings.INSTAGRAM_APP_SECRET = "test-instagram-app-secret"

        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        settings.JWT_SECRET = self.original_jwt_secret
        settings.ENCRYPTION_KEY = self.original_encryption_key
        settings.INSTAGRAM_APP_ID = self.original_instagram_app_id
        settings.INSTAGRAM_APP_SECRET = self.original_instagram_app_secret
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()
        self.temp_dir.rmdir()

    def _register_and_login(self):
        registered_user = auth.register(
            auth.RegisterRequest(email="Owner@Example.com", password="local-password", full_name="Owner"),
            db=self.db,
        )
        self.assertEqual("owner@example.com", registered_user.email)

        token_response = auth.login(
            auth.LoginRequest(email="owner@example.com", password="local-password"),
            db=self.db,
        )
        token = token_response.access_token
        current_user = get_current_user(authorization=f"Bearer {token}", db=self.db)
        return token, current_user

    def test_single_operator_auth_flow(self) -> None:
        token, current_user = self._register_and_login()

        with self.assertRaises(HTTPException) as duplicate:
            auth.register(auth.RegisterRequest(email="other@example.com", password="local-password"), db=self.db)
        self.assertEqual(409, duplicate.exception.status_code)

        me_response = auth.me(current_user=current_user)
        self.assertEqual("owner@example.com", me_response.email)

        with self.assertRaises(HTTPException) as bad_login:
            auth.login(auth.LoginRequest(email="owner@example.com", password="wrong-password"), db=self.db)
        self.assertEqual(401, bad_login.exception.status_code)

    def test_instagram_oauth_callback_stores_encrypted_token(self) -> None:
        _token, current_user = self._register_and_login()

        connect_response = social_accounts.connect_instagram(current_user=current_user)
        state = connect_response.state
        self.assertIn("instagram.com/oauth/authorize", connect_response.authorization_url)

        token_payload = InstagramTokenPayload(
            access_token="ig-access-token",
            refresh_token=None,
            platform_user_id="17841400000000000",
            username="local_operator",
            expires_at=datetime.utcnow() + timedelta(days=60),
            scopes=["instagram_business_basic"],
            raw_payload={"test": True},
        )

        with patch("app.api.social_accounts.exchange_code_for_token", return_value=token_payload):
            callback_response = social_accounts.instagram_callback(code="test-code", state=state, db=self.db)

        social_account = callback_response.social_account
        self.assertEqual(Platform.INSTAGRAM, social_account.platform)
        self.assertEqual("local_operator", social_account.username)

        stored_account = self.db.scalar(select(SocialAccount))
        self.assertIsNotNone(stored_account)
        assert stored_account is not None
        self.assertNotEqual("ig-access-token", stored_account.access_token_encrypted)
        self.assertEqual("ig-access-token", decrypt_secret(stored_account.access_token_encrypted))


if __name__ == "__main__":
    unittest.main()
