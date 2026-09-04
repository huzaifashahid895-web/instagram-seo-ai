# backend/app/services/thumbnail.py — Thumbnail generation for images and videos
# Cost classification: FREE + OPEN SOURCE (LOCAL ONLY)

import logging
import shutil
import subprocess
import uuid
from pathlib import Path

from PIL import Image
from fastapi import HTTPException, status

from app.config import settings
from app.services.storage import storage

logger = logging.getLogger(__name__)

# Thumbnail sizes (width x height)
THUMBNAIL_SIZE = (400, 400)
THUMBNAIL_QUALITY = 85


class ThumbnailGenerator:
    """Generate thumbnails for images and videos using PIL and FFmpeg."""

    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path or settings.FFMPEG_PATH

    def generate_thumbnail(
        self,
        source_path: str | Path,
        media_type: str,
        output_filename: str | None = None,
    ) -> Path:
        """
        Generate a thumbnail for an image or video.

        Args:
            source_path: Path to source media file
            media_type: 'image' or 'video'
            output_filename: Optional custom filename (will generate UUID if not provided)

        Returns:
            Path to generated thumbnail file
        """
        source_path = Path(source_path)

        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Generate output filename
        if output_filename is None:
            output_filename = f"{uuid.uuid4().hex}.jpg"

        # Ensure thumbnails directory exists
        thumbnail_dir = storage.root / "thumbnails"
        thumbnail_dir.mkdir(parents=True, exist_ok=True)

        output_path = thumbnail_dir / output_filename

        if media_type == "image":
            return self._generate_image_thumbnail(source_path, output_path)
        elif media_type == "video":
            return self._generate_video_thumbnail(source_path, output_path)
        else:
            raise ValueError(f"Unsupported media type: {media_type}")

    def _generate_image_thumbnail(self, source_path: Path, output_path: Path) -> Path:
        """Generate thumbnail for an image using PIL."""
        try:
            logger.info(f"Generating image thumbnail for {source_path.name}")
            
            with Image.open(source_path) as img:
                # Convert to RGB if necessary (handles RGBA, P, etc.)
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                # Calculate thumbnail size preserving aspect ratio
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Save as JPEG
                img.save(output_path, "JPEG", quality=THUMBNAIL_QUALITY, optimize=True)

            logger.info(f"Image thumbnail saved to {output_path}")
            return output_path

        except Exception as exc:
            logger.error(f"Failed to generate image thumbnail: {exc}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to generate image thumbnail: {str(exc)}"
            ) from exc

    def _generate_video_thumbnail(self, source_path: Path, output_path: Path) -> Path:
        """Generate thumbnail for a video using FFmpeg (frame at 1 second)."""
        if not (Path(self.ffmpeg_path).is_file() or shutil.which(self.ffmpeg_path)):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="FFmpeg not found. Set FFMPEG_PATH or install FFmpeg.",
            )

        try:
            logger.info(f"Generating video thumbnail for {source_path.name}")

            # Extract frame at 1 second (or first frame if video < 1s)
            command = [
                self.ffmpeg_path,
                "-y",  # Overwrite output file
                "-i", str(source_path),
                "-ss", "1",  # Seek to 1 second
                "-vframes", "1",  # Extract 1 frame
                "-vf", f"scale='min({THUMBNAIL_SIZE[0]},iw)':min'({THUMBNAIL_SIZE[1]},ih)':force_original_aspect_ratio=decrease",
                "-q:v", "2",  # JPEG quality (2-5 is good)
                str(output_path),
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            logger.info(f"Video thumbnail saved to {output_path}")
            return output_path

        except subprocess.TimeoutExpired as exc:
            logger.error(f"Video thumbnail generation timed out")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Video thumbnail generation timed out"
            ) from exc
        except subprocess.CalledProcessError as exc:
            logger.error(f"FFmpeg failed: {exc.stderr}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Video thumbnail generation failed: {exc.stderr}"
            ) from exc
        except Exception as exc:
            logger.error(f"Failed to generate video thumbnail: {exc}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to generate video thumbnail: {str(exc)}"
            ) from exc


# Default instance
thumbnail_generator = ThumbnailGenerator()
