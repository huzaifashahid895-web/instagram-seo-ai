# backend/tests/api/test_settings_model_configs.py — Step 5 settings/model config tests
# Cost classification: FREE + OPEN SOURCE

import unittest
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import auth, settings as settings_api
from app.config import settings
from app.core.db import Base
from app.core.security import get_current_user
from app.models.model_config import ModelCapability
from app.schemas.settings import ModelConfigCreate, ModelConfigUpdate


class SettingsModelConfigsTest(unittest.TestCase):
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
        auth.register(
            auth.RegisterRequest(email="owner@example.com", password="local-password", full_name="Owner"),
            db=self.db,
        )
        token = auth.login(auth.LoginRequest(email="owner@example.com", password="local-password"), db=self.db).access_token
        self.current_user = get_current_user(authorization=f"Bearer {token}", db=self.db)

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

    def test_runtime_settings_exposes_safe_summary(self) -> None:
        response = settings_api.get_runtime_settings(_current_user=self.current_user)

        self.assertTrue(response.jwt_configured)
        self.assertTrue(response.encryption_configured)
        self.assertTrue(response.instagram_app_configured)
        self.assertNotIn("test-jwt-secret", response.model_dump_json())
        self.assertNotIn("test-encryption-key", response.model_dump_json())

    def test_model_config_crud_and_active_switching(self) -> None:
        first = settings_api.create_model_config(
            ModelConfigCreate(
                capability=ModelCapability.LLM,
                provider_name="ollama",
                model_name="qwen2.5:3b-instruct-q4_K_M",
                endpoint_url="http://localhost:11434",
                parameters='{"context_window":4096}',
                is_active=True,
                is_local=True,
            ),
            _current_user=self.current_user,
            db=self.db,
        )

        second = settings_api.create_model_config(
            ModelConfigCreate(
                capability=ModelCapability.LLM,
                provider_name="ollama",
                model_name="qwen2.5:7b-instruct-q4_K_M",
                is_active=True,
                is_local=True,
            ),
            _current_user=self.current_user,
            db=self.db,
        )

        listed = settings_api.list_model_configs(_current_user=self.current_user, db=self.db)
        self.assertEqual(2, len(listed))

        refreshed_first = settings_api.get_model_config(first.id, _current_user=self.current_user, db=self.db)
        self.assertFalse(refreshed_first.is_active)

        active = settings_api.get_active_model_config(ModelCapability.LLM, _current_user=self.current_user, db=self.db)
        self.assertEqual(second.id, active.id)

        updated = settings_api.update_model_config(
            second.id,
            ModelConfigUpdate(temperature=0.4, max_tokens=800),
            _current_user=self.current_user,
            db=self.db,
        )
        self.assertEqual(0.4, updated.temperature)
        self.assertEqual(800, updated.max_tokens)

        reactivated_first = settings_api.activate_model_config(first.id, _current_user=self.current_user, db=self.db)
        self.assertTrue(reactivated_first.is_active)
        self.assertFalse(settings_api.get_model_config(second.id, _current_user=self.current_user, db=self.db).is_active)

        delete_response = settings_api.delete_model_config(second.id, _current_user=self.current_user, db=self.db)
        self.assertEqual(204, delete_response.status_code)

    def test_model_config_parameters_must_be_json(self) -> None:
        with self.assertRaises(HTTPException) as invalid_json:
            settings_api.create_model_config(
                ModelConfigCreate(
                    capability=ModelCapability.EMBEDDINGS,
                    provider_name="sentence-transformers",
                    model_name="BAAI/bge-small-en-v1.5",
                    parameters="{not-json}",
                ),
                _current_user=self.current_user,
                db=self.db,
            )

        self.assertEqual(422, invalid_json.exception.status_code)


if __name__ == "__main__":
    unittest.main()
