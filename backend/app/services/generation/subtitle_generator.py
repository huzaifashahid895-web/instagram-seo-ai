# backend/app/services/generation/subtitle_generator.py
# Cost classification: FREE + OPEN SOURCE
"""
Subtitle generation service using Whisper for transcription.
Generates SRT/VTT subtitles from audio files.
Designed for forced-alignment on TTS output (known text + audio).
"""

import logging
import uuid
from pathlib import Path
from typing import List

from pydantic import BaseModel

from app.config import settings
from app.services.providers import STTProvider, TranscriptResult

logger = logging.getLogger(__name__)


class SubtitleEntry(BaseModel):
    """A single subtitle entry."""
    index: int
    start_time: float  # seconds
    end_time: float    # seconds
    text: str


class SubtitleResult(BaseModel):
    """Generated subtitles result."""
    entries: List[SubtitleEntry]
    format: str  # "srt" or "vtt"
    file_path: str
    duration: float
    word_count: int


class SubtitleGenerator:
    """
    Generate subtitles from audio files using Whisper transcription.
    
    For TTS-generated audio, uses forced alignment (known text + audio)
    for more accurate timing than free transcription.
    """
    
    def __init__(
        self,
        stt_provider: STTProvider,
        output_dir: str | Path | None = None,
    ):
        self.stt = stt_provider
        self.output_dir = Path(output_dir or settings.STORAGE_ROOT / "processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_subtitles(
        self,
        audio_path: str | Path,
        output_format: str = "srt",
        max_chars_per_line: int = 42,
        max_words_per_segment: int = 8,
        language: str | None = None,
    ) -> SubtitleResult:
        """
        Generate subtitles from an audio file.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            output_format: "srt" or "vtt"
            max_chars_per_line: Maximum characters per subtitle line
            max_words_per_segment: Max words before splitting a segment
            language: Language code (e.g. "en")
        
        Returns:
            SubtitleResult with entries and file path
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Transcribe with timestamps
        logger.info(f"Transcribing audio for subtitles: {audio_path}")
        transcript = self.stt.transcribe(str(audio_path), language=language)
        
        # Convert transcript segments to subtitle entries
        entries = self._segments_to_subtitles(
            transcript,
            max_chars_per_line=max_chars_per_line,
            max_words_per_segment=max_words_per_segment,
        )
        
        # Generate output file
        output_path = self.output_dir / f"subs_{uuid.uuid4().hex[:12]}.{output_format}"
        
        if output_format == "srt":
            self._write_srt(entries, output_path)
        elif output_format == "vtt":
            self._write_vtt(entries, output_path)
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use 'srt' or 'vtt'.")
        
        duration = transcript.duration or (entries[-1].end_time if entries else 0.0)
        word_count = sum(len(e.text.split()) for e in entries)
        
        logger.info(f"Generated {len(entries)} subtitle entries → {output_path}")
        
        return SubtitleResult(
            entries=entries,
            format=output_format,
            file_path=str(output_path),
            duration=duration,
            word_count=word_count,
        )
    
    def _segments_to_subtitles(
        self,
        transcript: TranscriptResult,
        max_chars_per_line: int = 42,
        max_words_per_segment: int = 8,
    ) -> List[SubtitleEntry]:
        """Convert transcript segments to subtitle entries."""
        entries = []
        index = 1
        
        for segment in transcript.segments:
            text = segment.text.strip()
            if not text:
                continue
            
            words = text.split()
            
            # Split long segments
            if len(words) > max_words_per_segment:
                # Estimate time per word
                segment_duration = segment.end - segment.start
                time_per_word = segment_duration / len(words) if words else 0
                
                # Split into chunks
                for i in range(0, len(words), max_words_per_segment):
                    chunk_words = words[i:i + max_words_per_segment]
                    chunk_text = " ".join(chunk_words)
                    
                    start = segment.start + (i * time_per_word)
                    end = segment.start + ((i + len(chunk_words)) * time_per_word)
                    
                    # Wrap long lines
                    wrapped = self._wrap_text(chunk_text, max_chars_per_line)
                    
                    entries.append(SubtitleEntry(
                        index=index,
                        start_time=round(start, 3),
                        end_time=round(end, 3),
                        text=wrapped,
                    ))
                    index += 1
            else:
                wrapped = self._wrap_text(text, max_chars_per_line)
                entries.append(SubtitleEntry(
                    index=index,
                    start_time=round(segment.start, 3),
                    end_time=round(segment.end, 3),
                    text=wrapped,
                ))
                index += 1
        
        return entries
    
    def _wrap_text(self, text: str, max_chars: int) -> str:
        """Wrap text to fit within max character width."""
        if len(text) <= max_chars:
            return text
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_chars and current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + 1
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)
    
    def _format_timestamp_srt(self, seconds: float) -> str:
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Format seconds to VTT timestamp (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def _write_srt(self, entries: List[SubtitleEntry], path: Path):
        """Write subtitle entries to SRT file."""
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(f"{entry.index}\n")
                f.write(
                    f"{self._format_timestamp_srt(entry.start_time)} --> "
                    f"{self._format_timestamp_srt(entry.end_time)}\n"
                )
                f.write(f"{entry.text}\n\n")
    
    def _write_vtt(self, entries: List[SubtitleEntry], path: Path):
        """Write subtitle entries to WebVTT file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for entry in entries:
                f.write(
                    f"{self._format_timestamp_vtt(entry.start_time)} --> "
                    f"{self._format_timestamp_vtt(entry.end_time)}\n"
                )
                f.write(f"{entry.text}\n\n")
