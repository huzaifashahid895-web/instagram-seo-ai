# backend/app/services/stt/faster_whisper_provider.py — faster-whisper STT implementation
# Cost classification: FREE + OPEN SOURCE (MIT)

import logging
from pathlib import Path

from app.services.providers import STTProvider, TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)


class FasterWhisperProvider:
    """
    STT provider using faster-whisper (CTranslate2 backend).
    Model recommendation: 'base' or 'small' for CPU, 'medium'/'large-v3' for GPU.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: str | None = None,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self._model = None

    def _ensure_model(self):
        """Lazy-load the model on first use to avoid slowing down startup."""
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            ) from exc

        logger.info(
            f"Loading faster-whisper model '{self.model_size}' on {self.device} with {self.compute_type}"
        )
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            download_root=self.download_root,
        )
        logger.info("faster-whisper model loaded successfully")

    def transcribe(
        self, audio_path: str | Path, language: str | None = None
    ) -> TranscriptResult:
        """
        Transcribe audio file to text with word-level timestamps.

        Args:
            audio_path: Path to audio/video file (faster-whisper extracts audio automatically)
            language: ISO language code (e.g. 'en', 'es') or None for auto-detection

        Returns:
            TranscriptResult with full text, segments, and detected language
        """
        self._ensure_model()
        audio_path = Path(audio_path)

        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing {audio_path.name} (language={language or 'auto'})")

        # Run transcription
        segments_iter, info = self._model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            vad_filter=True,  # Voice activity detection to skip silence
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Collect segments
        segments = []
        full_text_parts = []

        for segment in segments_iter:
            segments.append(
                TranscriptSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                )
            )
            full_text_parts.append(segment.text.strip())

        full_text = " ".join(full_text_parts)
        detected_language = info.language if hasattr(info, "language") else language

        logger.info(
            f"Transcription complete: {len(segments)} segments, "
            f"{len(full_text)} chars, language={detected_language}"
        )

        return TranscriptResult(
            text=full_text,
            segments=segments,
            language=detected_language,
            duration=info.duration if hasattr(info, "duration") else None,
        )


# Default instance using 'base' model on CPU with int8 quantization (fastest for CPU)
default_stt_provider = FasterWhisperProvider(model_size="base", device="cpu", compute_type="int8")
