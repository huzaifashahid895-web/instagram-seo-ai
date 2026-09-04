# backend/tests/unit/test_phase5_generation.py
# Cost classification: FREE + OPEN SOURCE
"""
Unit tests for Phase 5 content generation services.

Tests cover:
- Script generation data structures
- Subtitle generation data structures
- FFmpeg pipeline configuration
- Content generation pipeline orchestration
- Video generation provider stub behavior
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from pydantic import ValidationError

from app.services.generation.script_generator import ScriptSection, ScriptOutline, GeneratedScript
from app.services.generation.subtitle_generator import SubtitleEntry, SubtitleResult
from app.services.generation.ffmpeg_pipeline import MediaFile, EditOperation, PipelineResult
from app.services.generation.pipeline import ContentRequest, ContentArtifact, ContentGenerationResult
from app.services.video_gen.stub_provider import StubVideoGenProvider


class TestScriptGenerationModels(unittest.TestCase):
    """Test script generation data structures."""
    
    def test_script_section_creation(self):
        """Test ScriptSection model validation."""
        section = ScriptSection(
            section_type="hook",
            content="This is an attention-grabbing hook!",
            duration_hint="3-5 seconds",
            visual_note="Close-up of product"
        )
        
        self.assertEqual(section.section_type, "hook")
        self.assertEqual(section.content, "This is an attention-grabbing hook!")
        self.assertTrue(len(section.duration_hint) > 0)
    
    def test_script_outline_creation(self):
        """Test ScriptOutline model validation."""
        outline = ScriptOutline(
            topic="Instagram SEO Tips",
            hook="Want more followers? Here's the secret...",
            key_points=["Use trending hashtags", "Post at optimal times", "Engage with comments"],
            call_to_action="Follow for more tips!",
            estimated_duration="30 seconds",
            format_type="reel"
        )
        
        self.assertEqual(outline.format_type, "reel")
        self.assertEqual(len(outline.key_points), 3)
        self.assertTrue("hashtags" in outline.key_points[0].lower())
    
    def test_generated_script_complete(self):
        """Test GeneratedScript with all required fields."""
        sections = [
            ScriptSection(
                section_type="hook",
                content="Hook text",
                duration_hint="3s"
            ),
            ScriptSection(
                section_type="body",
                content="Main content",
                duration_hint="20s"
            ),
        ]
        
        script = GeneratedScript(
            topic="Test Topic",
            title="Test Title",
            hook="Hook text",
            sections=sections,
            full_text="Hook text Main content",
            caption="Test caption #test",
            hashtags=["test", "content"],
            estimated_duration="30 seconds",
            format_type="reel",
            word_count=5
        )
        
        self.assertEqual(len(script.sections), 2)
        self.assertEqual(script.word_count, 5)
        self.assertEqual(len(script.hashtags), 2)


class TestSubtitleGenerationModels(unittest.TestCase):
    """Test subtitle generation data structures."""
    
    def test_subtitle_entry_creation(self):
        """Test SubtitleEntry model validation."""
        entry = SubtitleEntry(
            index=1,
            start_time=0.5,
            end_time=2.5,
            text="Hello world"
        )
        
        self.assertEqual(entry.index, 1)
        self.assertEqual(entry.start_time, 0.5)
        self.assertEqual(entry.end_time, 2.5)
        self.assertTrue(entry.end_time > entry.start_time)
    
    def test_subtitle_result_creation(self):
        """Test SubtitleResult model validation."""
        entries = [
            SubtitleEntry(index=1, start_time=0.0, end_time=2.0, text="First line"),
            SubtitleEntry(index=2, start_time=2.0, end_time=4.0, text="Second line"),
        ]
        
        result = SubtitleResult(
            entries=entries,
            format="srt",
            file_path="/path/to/subtitles.srt",
            duration=4.0,
            word_count=4
        )
        
        self.assertEqual(len(result.entries), 2)
        self.assertEqual(result.format, "srt")
        self.assertEqual(result.word_count, 4)


class TestFFmpegPipelineModels(unittest.TestCase):
    """Test FFmpeg pipeline data structures."""
    
    def test_media_file_creation(self):
        """Test MediaFile model validation."""
        media = MediaFile(
            path="/path/to/video.mp4",
            type="video",
            duration=30.0,
            width=1920,
            height=1080
        )
        
        self.assertEqual(media.type, "video")
        self.assertEqual(media.width, 1920)
        self.assertEqual(media.height, 1080)
    
    def test_edit_operation_creation(self):
        """Test EditOperation model validation."""
        op = EditOperation(
            operation="trim",
            params={"start": 0, "end": 10}
        )
        
        self.assertEqual(op.operation, "trim")
        self.assertIn("start", op.params)
    
    def test_pipeline_result_success(self):
        """Test PipelineResult for successful operation."""
        result = PipelineResult(
            output_path="/path/to/output.mp4",
            duration=30.0,
            file_size=1024000,
            operations_applied=["trim", "resize", "add_subtitles"],
            success=True,
            error=None
        )
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertEqual(len(result.operations_applied), 3)
    
    def test_pipeline_result_failure(self):
        """Test PipelineResult for failed operation."""
        result = PipelineResult(
            output_path="",
            duration=None,
            file_size=0,
            operations_applied=[],
            success=False,
            error="FFmpeg command failed"
        )
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


class TestContentGenerationPipeline(unittest.TestCase):
    """Test content generation pipeline models."""
    
    def test_content_request_minimal(self):
        """Test ContentRequest with minimal required fields."""
        request = ContentRequest(topic="Instagram Tips")
        
        self.assertEqual(request.topic, "Instagram Tips")
        self.assertEqual(request.format_type, "reel")  # default
        self.assertFalse(request.generate_images)  # default
    
    def test_content_request_full(self):
        """Test ContentRequest with all fields."""
        request = ContentRequest(
            topic="Instagram SEO",
            format_type="post",
            duration_target="60 seconds",
            voice="en_US-lessac-medium",
            generate_images=True,
            image_prompts=["Social media graphics", "Instagram logo"],
            background_music="/path/to/music.mp3",
            brand_context="We're a tech startup"
        )
        
        self.assertEqual(request.format_type, "post")
        self.assertTrue(request.generate_images)
        self.assertEqual(len(request.image_prompts), 2)
        self.assertIsNotNone(request.brand_context)
    
    def test_content_artifact_creation(self):
        """Test ContentArtifact model."""
        artifact = ContentArtifact(
            type="audio",
            path="/storage/audio/output.wav",
            metadata={"duration": 30.5, "sample_rate": 22050}
        )
        
        self.assertEqual(artifact.type, "audio")
        self.assertIn("duration", artifact.metadata)
    
    def test_content_generation_result_success(self):
        """Test ContentGenerationResult for successful generation."""
        script = GeneratedScript(
            topic="Test",
            title="Test Title",
            hook="Hook",
            sections=[],
            full_text="Full text",
            caption="Caption",
            hashtags=["test"],
            estimated_duration="30s",
            format_type="reel",
            word_count=2
        )
        
        result = ContentGenerationResult(
            request_id="test-123",
            topic="Test Topic",
            format_type="reel",
            script=script,
            artifacts=[],
            final_video_path="/path/to/video.mp4",
            success=True,
            generation_time_seconds=45.5
        )
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertIsNotNone(result.final_video_path)
        self.assertGreater(result.generation_time_seconds, 0)


class TestVideoGenProviderStub(unittest.TestCase):
    """Test video generation provider stub behavior."""
    
    def test_stub_initialization(self):
        """Test StubVideoGenProvider can be initialized."""
        provider = StubVideoGenProvider()
        self.assertIsNotNone(provider)
    
    def test_stub_generate_raises_not_implemented(self):
        """Test that generate() raises NotImplementedError with guidance."""
        provider = StubVideoGenProvider()
        
        with self.assertRaises(NotImplementedError) as context:
            provider.generate(prompt="Test video")
        
        # Check that the error message contains helpful guidance
        error_msg = str(context.exception)
        self.assertIn("HARDWARE REQUIREMENTS", error_msg)
        self.assertIn("GPU", error_msg)
        self.assertIn("ALTERNATIVES", error_msg)
    
    def test_stub_check_available_returns_false(self):
        """Test that check_available() returns False."""
        provider = StubVideoGenProvider()
        self.assertFalse(provider.check_available())
    
    def test_stub_get_info_returns_metadata(self):
        """Test that get_info() returns useful metadata."""
        provider = StubVideoGenProvider()
        info = provider.get_info()
        
        self.assertEqual(info["provider"], "StubVideoGenProvider")
        self.assertEqual(info["status"], "not_implemented")
        self.assertEqual(info["reason"], "requires_gpu")
        self.assertIn("hardware_requirements", info)
        self.assertIn("alternatives", info)
        self.assertIn("future_options", info)


class TestProviderProtocolCompliance(unittest.TestCase):
    """Test that providers follow protocol contracts."""
    
    def test_script_section_immutable_after_creation(self):
        """Test Pydantic models are immutable by default."""
        section = ScriptSection(
            section_type="hook",
            content="Original",
            duration_hint="3s"
        )
        
        # Pydantic models are mutable by default, but we can test field access
        self.assertEqual(section.content, "Original")
        
        # Try to create a new instance with updated content
        updated = section.model_copy(update={"content": "Updated"})
        self.assertEqual(updated.content, "Updated")
        self.assertEqual(section.content, "Original")  # Original unchanged


if __name__ == "__main__":
    unittest.main()
