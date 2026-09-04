# backend/tests/api/test_dashboard.py — Step 6 dashboard summary tests
# Cost classification: FREE + OPEN SOURCE

import unittest
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import auth, dashboard
from app.config import settings
from app.core.db import Base
from app.core.security import get_current_user


class DashboardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / "tmp" / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_dir / "test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        self.original_jwt_secret = settings.JWT_SECRET
        self.original_encryption_key = settings.ENCRYPTION_KEY
        settings.JWT_SECRET = "test-jwt-secret"
        settings.ENCRYPTION_KEY = "test-encryption-key"

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
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        if self.db_path.exists():
            self.db_path.unlink()
        self.temp_dir.rmdir()

    def test_dashboard_summary_returns_zero_state_counts(self) -> None:
        summary = dashboard.get_dashboard_summary(_current_user=self.current_user, db=self.db)

        self.assertEqual(0, summary.social_accounts)
        self.assertEqual(0, summary.content_assets)
        self.assertEqual(0, summary.posts)
        self.assertEqual(0, summary.pending_approvals)
        self.assertEqual(0, summary.active_model_configs)


if __name__ == "__main__":
    unittest.main()
