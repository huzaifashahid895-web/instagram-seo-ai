# backend/app/services/tts/piper_provider.py
# Cost classification: FREE + OPEN SOURCE (MIT), LOCAL ONLY
"""
Piper TTS provider for text-to-speech synthesis.

Piper is a fast, local neural TTS engine that runs well on CPU.
Quality is "good, not ElevenLabs-good" per ARCHITECTURE.md.

Install: pip install piper-tts
Models: Downloaded automatically on first use (~20-80MB per voice)

Hardware: Runs fast on CPU, no GPU needed.
"""

import logging
import subprocess
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Default Piper model — small, fast, decent quality
DEFAULT_MODEL = "en_US-lessac-medium"


class PiperTTSProvider:
    """
    Text-to-speech using Piper TTS.
    
    Implements TTSProvider protocol.
    Uses piper-tts command-line tool or Python API.
    Models are downloaded on first use and cached locally.
    """
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        output_dir: str | Path | None = None,
        sample_rate: int = 22050,
    ):
        self.model = model
        self.output_dir = Path(output_dir or settings.STORAGE_ROOT / "audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self._piper_available = None
    
    def _check_piper(self) -> bool:
        """Check if piper-tts is installed and available."""
        if self._piper_available is not None:
            return self._piper_available
        
        try:
            result = subprocess.run(
                ["piper", "--help"],
                capture_output=True,
                timeout=10
            )
            self._piper_available = True
            logger.info("Piper TTS is available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            try:
                # Try Python module
                import piper
                self._piper_available = True
                logger.info("Piper TTS available via Python module")
            except ImportError:
                self._piper_available = False
                logger.warning(
                    "Piper TTS not installed. Install with: pip install piper-tts"
                )
        
        return self._piper_available
    
    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        output_path: str | Path | None = None,
        **kwargs
    ) -> Path:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to speak
            voice: Voice/model name (e.g. "en_US-lessac-medium")
            output_path: Optional output file path
            **kwargs: Additional options (speed, volume, etc.)
        
        Returns:
            Path to generated WAV audio file
        
        Raises:
            RuntimeError: If Piper is not installed
        """
        if not self._check_piper():
            raise RuntimeError(
                "Piper TTS is not installed. Install with: pip install piper-tts\n"
                "Cost classification: FREE + OPEN SOURCE (MIT), LOCAL ONLY"
            )
        
        model = voice or self.model
        
        # Generate output path
        if output_path:
            output = Path(output_path)
        else:
            output = self.output_dir / f"tts_{uuid.uuid4().hex[:12]}.wav"
        
        output.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Synthesizing {len(text)} chars with model '{model}' → {output}")
        
        # Try CLI first (more reliable across platforms)
        try:
            return self._synthesize_cli(text, model, output, **kwargs)
        except Exception as cli_err:
            logger.warning(f"CLI synthesis failed: {cli_err}, trying Python API")
            try:
                return self._synthesize_python(text, model, output, **kwargs)
            except Exception as py_err:
                raise RuntimeError(
                    f"TTS synthesis failed. CLI error: {cli_err}. Python error: {py_err}"
                )
    
    def _synthesize_cli(
        self,
        text: str,
        model: str,
        output: Path,
        **kwargs
    ) -> Path:
        """Synthesize using piper CLI."""
        cmd = [
            "piper",
            "--model", model,
            "--output_file", str(output),
        ]
        
        # Optional: speed adjustment
        speed = kwargs.get("speed")
        if speed:
            cmd.extend(["--length_scale", str(1.0 / speed)])
        
        # Pipe text to stdin
        result = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=120  # 2 min timeout
        )
        
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"Piper CLI failed: {stderr}")
        
        if not output.exists():
            raise RuntimeError(f"Output file not created: {output}")
        
        logger.info(f"TTS complete: {output} ({output.stat().st_size} bytes)")
        return output
    
    def _synthesize_python(
        self,
        text: str,
        model: str,
        output: Path,
        **kwargs
    ) -> Path:
        """Synthesize using piper Python API."""
        import wave
        
        try:
            from piper import PiperVoice
        except ImportError:
            raise RuntimeError("piper-tts Python package not installed")
        
        # Load voice model
        voice = PiperVoice.load(model)
        
        # Synthesize to WAV
        with wave.open(str(output), "wb") as wav_file:
            voice.synthesize(text, wav_file)
        
        logger.info(f"TTS complete (Python API): {output}")
        return output
    
    def list_voices(self) -> list[str]:
        """List available Piper voice models."""
        try:
            result = subprocess.run(
                ["piper", "--list-voices"],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.decode("utf-8").strip().split('\n')
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Return known good models as fallback
        return [
            "en_US-lessac-medium",
            "en_US-lessac-high",
            "en_US-ryan-medium",
            "en_US-ryan-high",
            "en_US-amy-medium",
            "en_GB-alan-medium",
        ]
    
    def get_info(self) -> dict:
        """Get provider info and status."""
        return {
            "provider": "piper-tts",
            "available": self._check_piper(),
            "model": self.model,
            "output_dir": str(self.output_dir),
            "cost": "FREE + OPEN SOURCE (MIT)",
            "hardware": "CPU only, fast",
        }
