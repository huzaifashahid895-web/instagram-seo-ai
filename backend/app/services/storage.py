# backend/app/services/storage.py — Local file storage abstraction
# Cost classification: LOCAL ONLY

import uuid
from dataclasses import dataclass
from pathlib import Path, PurePath

from fastapi import HTTPException, UploadFile, status

from app.config import settings


STORAGE_BUCKETS = ("raw", "processed", "generated", "published", "thumbnails", "audio")
ALLOWED_MEDIA_TYPES = {
    "image": {
        "mime_prefix": "image/",
        "extensions": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"},
    },
    "video": {
        "mime_prefix": "video/",
        "extensions": {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"},
    },
    "audio": {
        "mime_prefix": "audio/",
        "extensions": {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm"},
    },
}


@dataclass(frozen=True)
class StoredFile:
    original_filename: str
    relative_path: str
    absolute_path: Path
    file_size: int
    mime_type: str
    media_type: str


class LocalStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or settings.STORAGE_ROOT).resolve()

    def ensure_directories(self) -> None:
        for bucket in STORAGE_BUCKETS:
            (self.root / bucket).mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        resolved = (self.root / relative_path).resolve()
        if self.root != resolved and self.root not in resolved.parents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path")
        return resolved

    async def save_upload(self, upload: UploadFile, bucket: str = "raw") -> StoredFile:
        self.ensure_directories()
        if bucket not in STORAGE_BUCKETS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown storage bucket")

        original_filename = PurePath(upload.filename or "").name
        suffix = Path(original_filename).suffix.lower()
        mime_type = upload.content_type or "application/octet-stream"
        media_type = infer_media_type(mime_type, suffix)

        stored_name = f"{uuid.uuid4().hex}{suffix}"
        destination = (self.root / bucket / stored_name).resolve()
        if self.root not in destination.parents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path")

        file_size = 0
        with destination.open("wb") as output:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                file_size += len(chunk)
                output.write(chunk)

        if file_size == 0:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

        relative_path = destination.relative_to(self.root).as_posix()
        return StoredFile(
            original_filename=original_filename or stored_name,
            relative_path=relative_path,
            absolute_path=destination,
            file_size=file_size,
            mime_type=mime_type,
            media_type=media_type,
        )


def infer_media_type(mime_type: str, suffix: str) -> str:
    for media_type, config in ALLOWED_MEDIA_TYPES.items():
        if mime_type.startswith(config["mime_prefix"]) and suffix in config["extensions"]:
            return media_type

    for media_type, config in ALLOWED_MEDIA_TYPES.items():
        if suffix in config["extensions"]:
            return media_type

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Upload must be an image, video, or audio file",
    )


storage = LocalStorage()
