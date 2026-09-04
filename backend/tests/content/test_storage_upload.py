# backend/tests/content/test_storage_upload.py — Phase 2 Step 1 storage/upload tests
# Cost classification: FREE + OPEN SOURCE

import shutil
import subprocess
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api import content
from app.core.db import Base
from app.models.content_analysis import ContentAnalysis
from app.models.brand_profile import BrandProfile
from app.models.content_asset import ContentAsset
from app.models.social_account import Platform, SocialAccount
from app.models.user import User
from app.services.media_analysis import FFmpegMediaAnalyzer, MediaProbe
from app.services.storage import STORAGE_BUCKETS, LocalStorage


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self._data = data
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""
        if size < 0:
            size = len(self._data) - self._offset
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class StorageUploadTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests") / "tmp" / uuid.uuid4().hex
        self.storage_root = self.temp_dir / "storage"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_dir / "test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.user = User(email="owner@example.com", hashed_password="hashed", is_superuser=True)
        self.db.add(self.user)
        self.db.flush()
        self.social_account = SocialAccount(
            user_id=self.user.id,
            platform=Platform.INSTAGRAM,
            platform_user_id="17841400000000000",
            username="owner",
            access_token_encrypted="encrypted-token",
        )
        self.db.add(self.social_account)
        self.db.flush()
        self.brand_profile = BrandProfile(
            user_id=self.user.id,
            social_account_id=self.social_account.id,
            niche="local business",
            tone="helpful",
        )
        self.db.add(self.brand_profile)
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.brand_profile)

        self.original_storage = content.storage
        self.original_media_analyzer = content.media_analyzer
        content.storage = LocalStorage(self.storage_root)

    def tearDown(self) -> None:
        content.storage = self.original_storage
        content.media_analyzer = self.original_media_analyzer
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    async def test_storage_creates_architecture_directories(self) -> None:
        local_storage = LocalStorage(self.storage_root)
        local_storage.ensure_directories()

        for bucket in STORAGE_BUCKETS:
            with self.subTest(bucket=bucket):
                self.assertTrue((self.storage_root / bucket).is_dir())

    async def test_upload_creates_content_asset_and_raw_file(self) -> None:
        upload = FakeUploadFile("clip.mp4", "video/mp4", b"fake-video-bytes")

        asset = await content.upload_content(
            brand_profile_id=self.brand_profile.id,
            file=upload,
            current_user=self.user,
            db=self.db,
        )

        self.assertEqual("clip.mp4", asset.filename)
        self.assertEqual("video", asset.media_type)
        self.assertEqual("video/mp4", asset.mime_type)
        self.assertEqual(len(b"fake-video-bytes"), asset.file_size)
        self.assertTrue((self.storage_root / asset.file_path).is_file())
        self.assertEqual(asset.id, self.db.scalar(select(ContentAsset.id)))

    async def test_upload_rejects_unsupported_file_type(self) -> None:
        upload = FakeUploadFile("notes.txt", "text/plain", b"not media")

        with self.assertRaises(HTTPException) as rejected:
            await content.upload_content(
                brand_profile_id=self.brand_profile.id,
                file=upload,
                current_user=self.user,
                db=self.db,
            )

        self.assertEqual(415, rejected.exception.status_code)

    async def test_analyze_content_populates_asset_and_analysis(self) -> None:
        upload = FakeUploadFile("frame.png", "image/png", b"fake-image-bytes")
        asset = await content.upload_content(
            brand_profile_id=self.brand_profile.id,
            file=upload,
            current_user=self.user,
            db=self.db,
        )

        class FakeAnalyzer:
            def populate_analysis(self, asset: ContentAsset, analysis: ContentAnalysis | None = None) -> ContentAnalysis:
                analysis = analysis or ContentAnalysis(asset_id=asset.id)
                analysis.format = "image"
                analysis.duration = None
                analysis.orientation = "landscape"
                analysis.file_size = asset.file_size
                analysis.width = 1200
                analysis.height = 800
                analysis.duplicate_hash = "ahash:ffffffff00000000"
                asset.width = 1200
                asset.height = 800
                return analysis

        content.media_analyzer = FakeAnalyzer()
        analysis = content.analyze_content_asset(asset.id, current_user=self.user, db=self.db)

        self.assertEqual("image", analysis.format)
        self.assertEqual("landscape", analysis.orientation)
        self.assertEqual(1200, analysis.width)
        self.assertEqual(800, self.db.get(ContentAsset, asset.id).height)
        self.assertEqual("ahash:ffffffff00000000", analysis.duplicate_hash)


class FFmpegMediaAnalyzerTest(unittest.TestCase):
    def test_populate_analysis_uses_ffprobe_and_visual_hash(self) -> None:
        temp_dir = Path("tests") / "tmp" / uuid.uuid4().hex
        temp_dir.mkdir(parents=True, exist_ok=True)
        source_path = temp_dir / "image.png"
        source_path.write_bytes(b"fake-image")
        try:
            asset = ContentAsset(
                brand_profile_id=uuid.uuid4(),
                filename="image.png",
                file_path=source_path.name,
                file_size=source_path.stat().st_size,
                mime_type="image/png",
                media_type="image",
            )
            analyzer = FFmpegMediaAnalyzer(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe")
            probe_json = '{"streams":[{"codec_type":"video","width":4,"height":2,"duration":"1.5"}],"format":{"duration":"1.5"}}'
            raw_pixels = bytes(range(64))

            with patch("app.services.media_analysis.storage") as fake_storage:
                fake_storage.resolve.return_value = source_path
                with patch("app.services.media_analysis.shutil.which", return_value="found"):
                    with patch("app.services.media_analysis.subprocess.run") as fake_run:
                        fake_run.side_effect = [
                            Mock(stdout=probe_json),
                            Mock(stdout=raw_pixels),
                        ]
                        analysis = analyzer.populate_analysis(asset)

            self.assertEqual("image", analysis.format)
            self.assertEqual(1.5, analysis.duration)
            self.assertEqual("landscape", analysis.orientation)
            self.assertEqual(4, analysis.width)
            self.assertEqual(2, analysis.height)
            self.assertTrue(analysis.duplicate_hash.startswith("ahash:"))
            self.assertEqual(4, asset.width)
        finally:
            if source_path.exists():
                source_path.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()

    def test_missing_ffprobe_reports_service_unavailable(self) -> None:
        temp_dir = Path("tests") / "tmp" / uuid.uuid4().hex
        temp_dir.mkdir(parents=True, exist_ok=True)
        source_path = temp_dir / "clip.mp4"
        source_path.write_bytes(b"fake-video")
        try:
            asset = ContentAsset(
                brand_profile_id=uuid.uuid4(),
                filename="clip.mp4",
                file_path=source_path.name,
                file_size=source_path.stat().st_size,
                mime_type="video/mp4",
                media_type="video",
            )
            analyzer = FFmpegMediaAnalyzer(ffmpeg_path="missing-ffmpeg", ffprobe_path="missing-ffprobe")
            with patch("app.services.media_analysis.storage") as fake_storage:
                fake_storage.resolve.return_value = source_path
                with patch("app.services.media_analysis.shutil.which", return_value=None):
                    with self.assertRaises(HTTPException) as missing:
                        analyzer.analyze_asset(asset)

            self.assertEqual(503, missing.exception.status_code)
        finally:
            if source_path.exists():
                source_path.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
