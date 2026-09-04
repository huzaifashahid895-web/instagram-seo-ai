# backend/app/services/video_gen/__init__.py
"""Video generation provider implementations."""

from .stub_provider import StubVideoGenProvider

__all__ = ["StubVideoGenProvider"]
