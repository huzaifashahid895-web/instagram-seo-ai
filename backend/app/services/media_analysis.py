# backend/app/services/media_analysis.py — Deterministic FFmpeg media analysis
# Cost classification: LOCAL ONLY

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.config import settings
from app.models.content_asset import ContentAsset
from app.models.content_analysis import ContentAnalysis
from app.services.storage import storage


@dataclass(frozen=True)
class MediaProbe:
    duration: float | None
    width: int | None
    height: int | None
    orientation: str | None
    media_format: str
    duplicate_hash: str | None


class FFmpegMediaAnalyzer:
    def __init__(self, ffmpeg_path: str | None = None, ffprobe_path: str | None = None) -> None:
        self.ffmpeg_path = ffmpeg_path or settings.FFMPEG_PATH
        self.ffprobe_path = ffprobe_path or settings.FFPROBE_PATH

    def analyze_asset(self, asset: ContentAsset) -> MediaProbe:
        source_path = storage.resolve(asset.file_path)
        if not source_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored media file not found")

        self._require_executable(self.ffprobe_path, "FFprobe")
        metadata = self._probe(source_path)
        stream = self._select_stream(metadata, asset.media_type)
        duration = self._duration(metadata, stream)
        width = _safe_int(stream.get("width"))
        height = _safe_int(stream.get("height"))
        orientation = _orientation(width, height)

        duplicate_hash = None
        if asset.media_type in {"image", "video"}:
            self._require_executable(self.ffmpeg_path, "FFmpeg")
            duplicate_hash = self._visual_hash(source_path)
        elif asset.media_type == "audio":
            duplicate_hash = self._file_sample_hash(source_path)

        return MediaProbe(
            duration=duration,
            width=width,
            height=height,
            orientation=orientation,
            media_format=asset.media_type,
            duplicate_hash=duplicate_hash,
        )

    def populate_analysis(self, asset: ContentAsset, analysis: ContentAnalysis | None = None) -> ContentAnalysis:
        probe = self.analyze_asset(asset)
        analysis = analysis or ContentAnalysis(asset_id=asset.id)
        analysis.format = probe.media_format
        analysis.duration = probe.duration
        analysis.orientation = probe.orientation
        analysis.file_size = asset.file_size
        analysis.width = probe.width
        analysis.height = probe.height
        analysis.duplicate_hash = probe.duplicate_hash

        asset.duration = probe.duration
        asset.width = probe.width
        asset.height = probe.height
        return analysis

    def _probe(self, source_path: Path) -> dict[str, Any]:
        command = [
            self.ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(source_path),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Media analysis timed out") from exc
        except subprocess.CalledProcessError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.stderr or "Media probe failed") from exc
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Media probe returned invalid JSON") from exc

    def _select_stream(self, metadata: dict[str, Any], media_type: str) -> dict[str, Any]:
        desired_type = "video" if media_type in {"image", "video"} else "audio"
        for stream in metadata.get("streams", []):
            if stream.get("codec_type") == desired_type:
                return stream
        return {}

    def _duration(self, metadata: dict[str, Any], stream: dict[str, Any]) -> float | None:
        raw_duration = stream.get("duration") or metadata.get("format", {}).get("duration")
        try:
            return float(raw_duration) if raw_duration is not None else None
        except (TypeError, ValueError):
            return None

    def _visual_hash(self, source_path: Path) -> str:
        command = [
            self.ffmpeg_path,
            "-v",
            "error",
            "-i",
            str(source_path),
            "-vf",
            "scale=8:8,format=gray",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-",
        ]
        try:
            result = subprocess.run(command, capture_output=True, check=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Media hashing timed out") from exc
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else "Media hashing failed"
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message) from exc

        pixels = result.stdout[:64]
        if len(pixels) < 64:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Media hashing returned too few pixels")
        average = sum(pixels) / len(pixels)
        bits = "".join("1" if pixel >= average else "0" for pixel in pixels)
        return f"ahash:{int(bits, 2):016x}"

    def _file_sample_hash(self, source_path: Path) -> str:
        digest = hashlib.sha256()
        with source_path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"

    def _require_executable(self, executable: str, label: str) -> None:
        if Path(executable).is_file() or shutil.which(executable):
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{label} executable not found. Set {label.upper()}_PATH or install FFmpeg locally.",
        )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _orientation(width: int | None, height: int | None) -> str | None:
    if width is None or height is None:
        return None
    if width == height:
        return "square"
    if width > height:
        return "landscape"
    return "portrait"


media_analyzer = FFmpegMediaAnalyzer()
