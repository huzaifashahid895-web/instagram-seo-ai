# backend/app/services/generation/ffmpeg_pipeline.py
# Cost classification: FREE + OPEN SOURCE (LGPL/GPL), LOCAL ONLY
"""
FFmpeg editing pipeline for content creation.

FFmpeg is the industry standard for video/audio processing.
This service provides a Python wrapper for common operations:
- Combining audio + video
- Adding subtitles (burned-in)
- Trimming/cutting clips
- Adding background music
- Resizing/reformatting for social media

Install: Download from https://ffmpeg.org/download.html
Add to system PATH.
"""

import logging
import subprocess
import uuid
from pathlib import Path
from typing import List

from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class MediaFile(BaseModel):
    """Reference to a media file with metadata."""
    path: str
    type: str  # "video", "audio", "image", "subtitle"
    duration: float | None = None
    width: int | None = None
    height: int | None = None


class EditOperation(BaseModel):
    """A single edit operation in the pipeline."""
    operation: str  # "trim", "concat", "overlay_audio", "add_subtitles", "resize", "add_text"
    params: dict = {}


class PipelineResult(BaseModel):
    """Result of an FFmpeg pipeline execution."""
    output_path: str
    duration: float | None = None
    file_size: int
    operations_applied: List[str]
    success: bool
    error: str | None = None


class FFmpegPipeline:
    """
    FFmpeg-based media editing pipeline.
    
    Wraps FFmpeg CLI for common video editing operations.
    All processing is local — no cloud services.
    """
    
    def __init__(
        self,
        output_dir: str | Path | None = None,
    ):
        self.output_dir = Path(output_dir or settings.STORAGE_ROOT / "generated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._ffmpeg_available = None
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed."""
        if self._ffmpeg_available is not None:
            return self._ffmpeg_available
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=10
            )
            self._ffmpeg_available = result.returncode == 0
            if self._ffmpeg_available:
                # Extract version
                version_line = result.stdout.decode("utf-8").split('\n')[0]
                logger.info(f"FFmpeg available: {version_line}")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._ffmpeg_available = False
            logger.warning("FFmpeg not found. Install from: https://ffmpeg.org/download.html")
        
        return self._ffmpeg_available
    
    def _run_ffmpeg(self, args: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """Run FFmpeg command with logging."""
        cmd = ["ffmpeg", "-y"] + args  # -y = overwrite without asking
        logger.info(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            logger.error(f"FFmpeg failed: {stderr[-500:]}")  # Last 500 chars
            raise RuntimeError(f"FFmpeg failed: {stderr[-200:]}")
        
        return result
    
    def get_media_info(self, file_path: str | Path) -> MediaFile:
        """
        Get media file information using ffprobe.
        
        Args:
            file_path: Path to media file
        
        Returns:
            MediaFile with metadata
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Determine type from extension
        ext = path.suffix.lower()
        if ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
            media_type = "video"
        elif ext in (".wav", ".mp3", ".ogg", ".flac", ".m4a"):
            media_type = "audio"
        elif ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            media_type = "image"
        elif ext in (".srt", ".vtt", ".ass"):
            media_type = "subtitle"
        else:
            media_type = "unknown"
        
        duration = None
        width = None
        height = None
        
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format", "-show_streams",
                    str(path)
                ],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout.decode("utf-8"))
                
                # Get duration
                if "format" in info and "duration" in info["format"]:
                    duration = float(info["format"]["duration"])
                
                # Get dimensions from video stream
                for stream in info.get("streams", []):
                    if stream.get("codec_type") == "video":
                        width = stream.get("width")
                        height = stream.get("height")
                        break
        except Exception as e:
            logger.warning(f"Could not get media info: {e}")
        
        return MediaFile(
            path=str(path),
            type=media_type,
            duration=duration,
            width=width,
            height=height,
        )
    
    def combine_audio_video(
        self,
        video_path: str | Path,
        audio_path: str | Path,
        output_path: str | Path | None = None,
    ) -> PipelineResult:
        """
        Combine a video file with an audio track.
        
        Args:
            video_path: Path to video file
            audio_path: Path to audio file
            output_path: Optional output path
        
        Returns:
            PipelineResult with output file info
        """
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg is not installed")
        
        output = Path(output_path) if output_path else (
            self.output_dir / f"combined_{uuid.uuid4().hex[:12]}.mp4"
        )
        
        self._run_ffmpeg([
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output)
        ])
        
        return self._build_result(output, ["combine_audio_video"])
    
    def add_subtitles(
        self,
        video_path: str | Path,
        subtitle_path: str | Path,
        output_path: str | Path | None = None,
        font_size: int = 24,
        font_color: str = "white",
        outline_color: str = "black",
        position: str = "bottom",
    ) -> PipelineResult:
        """
        Burn subtitles into video.
        
        Args:
            video_path: Path to video file
            subtitle_path: Path to SRT/VTT file
            output_path: Optional output path
            font_size: Subtitle font size
            font_color: Font color
            outline_color: Outline color for readability
            position: "bottom", "center", or "top"
        
        Returns:
            PipelineResult
        """
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg is not installed")
        
        output = Path(output_path) if output_path else (
            self.output_dir / f"subtitled_{uuid.uuid4().hex[:12]}.mp4"
        )
        
        # Calculate vertical alignment
        alignment = {"bottom": 2, "center": 10, "top": 6}.get(position, 2)
        
        # Escape the subtitle path for FFmpeg filter
        sub_path_escaped = str(subtitle_path).replace("\\", "/").replace(":", "\\\\:")
        
        subtitle_filter = (
            f"subtitles='{sub_path_escaped}'"
            f":force_style='FontSize={font_size},"
            f"PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,"
            f"Outline=2,"
            f"Alignment={alignment}'"
        )
        
        self._run_ffmpeg([
            "-i", str(video_path),
            "-vf", subtitle_filter,
            "-c:a", "copy",
            str(output)
        ])
        
        return self._build_result(output, ["add_subtitles"])
    
    def trim_video(
        self,
        video_path: str | Path,
        start_time: float,
        end_time: float,
        output_path: str | Path | None = None,
    ) -> PipelineResult:
        """
        Trim a video to a specific time range.
        
        Args:
            video_path: Path to video
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Optional output path
        
        Returns:
            PipelineResult
        """
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg is not installed")
        
        output = Path(output_path) if output_path else (
            self.output_dir / f"trimmed_{uuid.uuid4().hex[:12]}.mp4"
        )
        
        duration = end_time - start_time
        
        self._run_ffmpeg([
            "-i", str(video_path),
            "-ss", str(start_time),
            "-t", str(duration),
            "-c", "copy",
            str(output)
        ])
        
        return self._build_result(output, ["trim_video"])
    
    def resize_for_platform(
        self,
        video_path: str | Path,
        platform: str = "instagram_reel",
        output_path: str | Path | None = None,
    ) -> PipelineResult:
        """
        Resize video for a specific platform.
        
        Args:
            video_path: Path to video
            platform: Target format
            output_path: Optional output path
        
        Returns:
            PipelineResult
        """
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg is not installed")
        
        # Platform dimensions
        sizes = {
            "instagram_reel": (1080, 1920),   # 9:16
            "instagram_post": (1080, 1080),   # 1:1
            "instagram_story": (1080, 1920),  # 9:16
            "youtube_short": (1080, 1920),    # 9:16
            "youtube": (1920, 1080),          # 16:9
            "tiktok": (1080, 1920),           # 9:16
        }
        
        if platform not in sizes:
            raise ValueError(f"Unknown platform: {platform}. Choose from: {list(sizes.keys())}")
        
        width, height = sizes[platform]
        
        output = Path(output_path) if output_path else (
            self.output_dir / f"resized_{platform}_{uuid.uuid4().hex[:12]}.mp4"
        )
        
        # Scale and pad to fit target dimensions
        scale_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
        )
        
        self._run_ffmpeg([
            "-i", str(video_path),
            "-vf", scale_filter,
            "-c:a", "copy",
            str(output)
        ])
        
        return self._build_result(output, [f"resize_{platform}"])
    
    def create_slideshow(
        self,
        image_paths: List[str | Path],
        audio_path: str | Path | None = None,
        duration_per_image: float = 3.0,
        transition: str = "fade",
        output_path: str | Path | None = None,
    ) -> PipelineResult:
        """
        Create a slideshow video from images.
        
        Args:
            image_paths: List of image file paths
            audio_path: Optional background audio
            duration_per_image: Seconds per image
            transition: Transition type ("fade", "none")
            output_path: Optional output path
        
        Returns:
            PipelineResult
        """
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg is not installed")
        
        if not image_paths:
            raise ValueError("At least one image is required")
        
        output = Path(output_path) if output_path else (
            self.output_dir / f"slideshow_{uuid.uuid4().hex[:12]}.mp4"
        )
        
        # Build concat file
        concat_file = self.output_dir / f"concat_{uuid.uuid4().hex[:8]}.txt"
        with open(concat_file, "w") as f:
            for img in image_paths:
                img_path = str(Path(img).resolve()).replace("\\", "/")
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration_per_image}\n")
            # Repeat last image to prevent cut
            last = str(Path(image_paths[-1]).resolve()).replace("\\", "/")
            f.write(f"file '{last}'\n")
        
        args = [
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            "-pix_fmt", "yuv420p",
        ]
        
        if audio_path:
            args.extend(["-i", str(audio_path), "-c:a", "aac", "-shortest"])
        
        args.append(str(output))
        
        try:
            self._run_ffmpeg(args)
        finally:
            # Clean up concat file
            concat_file.unlink(missing_ok=True)
        
        return self._build_result(output, ["create_slideshow"])
    
    def _build_result(
        self,
        output_path: Path,
        operations: List[str],
    ) -> PipelineResult:
        """Build PipelineResult from output file."""
        if not output_path.exists():
            return PipelineResult(
                output_path=str(output_path),
                file_size=0,
                operations_applied=operations,
                success=False,
                error="Output file was not created"
            )
        
        # Get duration if it's a video/audio
        duration = None
        try:
            info = self.get_media_info(output_path)
            duration = info.duration
        except Exception:
            pass
        
        return PipelineResult(
            output_path=str(output_path),
            duration=duration,
            file_size=output_path.stat().st_size,
            operations_applied=operations,
            success=True,
        )
    
    def get_info(self) -> dict:
        """Get FFmpeg availability and version info."""
        info = {
            "available": self._check_ffmpeg(),
            "output_dir": str(self.output_dir),
            "cost": "FREE + OPEN SOURCE (LGPL/GPL)",
        }
        
        if self._check_ffmpeg():
            try:
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    timeout=10
                )
                info["version"] = result.stdout.decode("utf-8").split('\n')[0]
            except Exception:
                pass
        
        return info
