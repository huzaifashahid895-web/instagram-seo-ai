# backend/app/services/generation/script_generator.py
# Cost classification: FREE + OPEN SOURCE
"""
Script generation service for social media content.
Topic → Research (RAG) → Outline → Full Script pipeline.
"""

import logging
from typing import List
from pydantic import BaseModel

from app.services.providers import LLMProvider, EmbeddingProvider
from app.services.vector_store.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class ScriptSection(BaseModel):
    """A single section of a script."""
    section_type: str  # "hook", "body", "cta", "transition", "closing"
    content: str
    duration_hint: str  # e.g. "3-5 seconds"
    visual_note: str = ""  # visual direction for this section


class ScriptOutline(BaseModel):
    """Outline for a script before full generation."""
    topic: str
    hook: str
    key_points: List[str]
    call_to_action: str
    estimated_duration: str
    format_type: str  # "reel", "carousel", "story", "post"


class GeneratedScript(BaseModel):
    """Complete generated script with sections and metadata."""
    topic: str
    title: str
    hook: str
    sections: List[ScriptSection]
    full_text: str
    caption: str
    hashtags: List[str]
    estimated_duration: str
    format_type: str
    word_count: int


class ScriptGenerator:
    """
    Multi-step script generation pipeline.
    
    Flow: Topic → Context (RAG) → Outline → Full Script → Caption + Hashtags
    
    Uses LLM for creative tasks (outline, script writing, caption).
    Uses deterministic code for structure and formatting.
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: ChromaVectorStore
    ):
        self.llm = llm_provider
        self.embeddings = embedding_provider
        self.vector_store = vector_store
    
    def _retrieve_context(self, topic: str, top_k: int = 5) -> str:
        """Retrieve relevant context from vector store for topic."""
        try:
            query_embedding = self.embeddings.embed_text(topic)
            results = self.vector_store.search(
                query_embedding=query_embedding,
                n_results=top_k
            )
            
            if results.get("documents"):
                context_parts = []
                for i, doc in enumerate(results["documents"]):
                    context_parts.append(f"[Reference {i+1}]: {doc[:300]}")
                return "\n".join(context_parts)
        except Exception as e:
            logger.warning(f"Failed to retrieve context: {e}")
        
        return ""
    
    def generate_outline(
        self,
        topic: str,
        format_type: str = "reel",
        target_audience: str | None = None,
        brand_voice: str | None = None,
        duration: str = "30-60 seconds"
    ) -> ScriptOutline:
        """
        Generate a script outline from a topic.
        
        Args:
            topic: Content topic
            format_type: Target format (reel, carousel, story, post)
            target_audience: Who the content is for
            brand_voice: Brand voice description
            duration: Target duration
        
        Returns:
            ScriptOutline with hook, key points, and CTA
        """
        # Retrieve context from RAG
        context = self._retrieve_context(topic)
        
        prompt = f"""Create a content outline for a {format_type} about: {topic}

Target duration: {duration}"""
        
        if target_audience:
            prompt += f"\nTarget audience: {target_audience}"
        if brand_voice:
            prompt += f"\nBrand voice: {brand_voice}"
        if context:
            prompt += f"\n\nRelevant context from content library:\n{context}"
        
        prompt += """

Provide:
1. HOOK: An attention-grabbing opening (first 2-3 seconds)
2. KEY POINTS: 3-5 main points to cover (brief bullets)
3. CALL TO ACTION: What you want the viewer to do

Format your response exactly as:
HOOK: [your hook]
POINTS:
- [point 1]
- [point 2]
- [point 3]
CTA: [your call to action]"""
        
        system = "You are a viral content strategist who creates engaging social media scripts."
        
        response = self.llm.generate(prompt, system=system)
        
        # Parse the response deterministically
        hook = ""
        key_points = []
        cta = ""
        
        lines = response.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.upper().startswith("HOOK:"):
                hook = line[5:].strip()
                current_section = "hook"
            elif line.upper().startswith("POINTS:") or line.upper().startswith("KEY POINTS:"):
                current_section = "points"
            elif line.upper().startswith("CTA:") or line.upper().startswith("CALL TO ACTION:"):
                cta = line.split(":", 1)[1].strip() if ":" in line else line
                current_section = "cta"
            elif current_section == "points" and (line.startswith("-") or line.startswith("•") or line[0].isdigit()):
                point = line.lstrip("-•0123456789.) ").strip()
                if point:
                    key_points.append(point)
            elif current_section == "hook" and not hook:
                hook = line
            elif current_section == "cta" and not cta:
                cta = line
        
        # Fallbacks
        if not hook:
            hook = f"Did you know this about {topic}?"
        if not key_points:
            key_points = [f"Key insight about {topic}"]
        if not cta:
            cta = "Follow for more tips like this!"
        
        return ScriptOutline(
            topic=topic,
            hook=hook,
            key_points=key_points[:5],
            call_to_action=cta,
            estimated_duration=duration,
            format_type=format_type
        )
    
    def generate_script(
        self,
        outline: ScriptOutline | None = None,
        topic: str | None = None,
        format_type: str = "reel",
        target_audience: str | None = None,
        brand_voice: str | None = None,
        duration: str = "30-60 seconds",
        include_visual_notes: bool = True
    ) -> GeneratedScript:
        """
        Generate a full script, optionally from an outline.
        
        Args:
            outline: Pre-generated outline (if None, generates one)
            topic: Topic (required if outline is None)
            format_type: Target format
            target_audience: Target audience
            brand_voice: Brand voice
            duration: Target duration
            include_visual_notes: Include visual direction notes
        
        Returns:
            Complete GeneratedScript
        """
        # Generate outline if not provided
        if outline is None:
            if topic is None:
                raise ValueError("Either outline or topic must be provided")
            outline = self.generate_outline(
                topic=topic,
                format_type=format_type,
                target_audience=target_audience,
                brand_voice=brand_voice,
                duration=duration
            )
        
        # Build the full script generation prompt
        prompt = f"""Write a complete {outline.format_type} script about: {outline.topic}

Duration: {outline.estimated_duration}

Outline:
- Hook: {outline.hook}
- Key Points: {'; '.join(outline.key_points)}
- CTA: {outline.call_to_action}"""
        
        if target_audience:
            prompt += f"\nTarget audience: {target_audience}"
        if brand_voice:
            prompt += f"\nBrand voice: {brand_voice}"
        
        prompt += """

Write the full script with these sections:
1. HOOK (first 2-3 seconds - grab attention)
2. BODY (main content - cover key points)
3. CTA (call to action - what to do next)

For each section, write the spoken text."""
        
        if include_visual_notes:
            prompt += """
Also include brief visual notes in [brackets] for what should appear on screen."""
        
        prompt += """

Also generate:
- A catchy TITLE for the content
- A social media CAPTION (100-300 chars)
- 5 relevant HASHTAGS (without #)

Format:
TITLE: [title]
---
[script sections]
---
CAPTION: [caption]
HASHTAGS: [comma-separated hashtags]"""
        
        system = "You are an expert social media script writer who creates viral, engaging content."
        
        response = self.llm.generate(prompt, system=system)
        
        # Parse the response
        title = ""
        script_text = ""
        caption = ""
        hashtags = []
        
        # Split into parts by ---
        parts = response.split("---")
        
        for part in parts:
            part = part.strip()
            if part.upper().startswith("TITLE:"):
                title = part[6:].strip()
            elif "CAPTION:" in part.upper():
                # Extract caption and hashtags
                for line in part.split('\n'):
                    line = line.strip()
                    if line.upper().startswith("CAPTION:"):
                        caption = line[8:].strip()
                    elif line.upper().startswith("HASHTAGS:"):
                        raw = line[9:].strip()
                        hashtags = [h.strip().lstrip('#') for h in raw.split(',') if h.strip()]
            else:
                # This is the script body
                if part and not part.upper().startswith("TITLE:"):
                    script_text = part
        
        # If title wasn't extracted properly, try first line
        if not title:
            for line in response.split('\n'):
                line = line.strip()
                if line.upper().startswith("TITLE:"):
                    title = line[6:].strip()
                    break
            if not title:
                title = f"Script: {outline.topic}"
        
        # If caption wasn't extracted
        if not caption:
            for line in response.split('\n'):
                line = line.strip()
                if line.upper().startswith("CAPTION:"):
                    caption = line[8:].strip()
                    break
            if not caption:
                caption = outline.hook
        
        # If hashtags weren't extracted
        if not hashtags:
            for line in response.split('\n'):
                line = line.strip()
                if line.upper().startswith("HASHTAGS:"):
                    raw = line[9:].strip()
                    hashtags = [h.strip().lstrip('#') for h in raw.split(',') if h.strip()]
                    break
        
        # Build sections from script text
        sections = self._parse_script_sections(script_text, outline)
        
        # Build full text from sections
        full_text = "\n\n".join(s.content for s in sections) if sections else script_text
        word_count = len(full_text.split())
        
        return GeneratedScript(
            topic=outline.topic,
            title=title,
            hook=outline.hook,
            sections=sections,
            full_text=full_text,
            caption=caption,
            hashtags=hashtags[:5],
            estimated_duration=outline.estimated_duration,
            format_type=outline.format_type,
            word_count=word_count
        )
    
    def _parse_script_sections(
        self,
        script_text: str,
        outline: ScriptOutline
    ) -> List[ScriptSection]:
        """Parse script text into structured sections."""
        sections = []
        
        if not script_text.strip():
            # Fallback: create basic sections from outline
            sections.append(ScriptSection(
                section_type="hook",
                content=outline.hook,
                duration_hint="2-3 seconds",
                visual_note="Opening shot"
            ))
            for i, point in enumerate(outline.key_points):
                sections.append(ScriptSection(
                    section_type="body",
                    content=point,
                    duration_hint="5-10 seconds",
                    visual_note=f"Visual for point {i+1}"
                ))
            sections.append(ScriptSection(
                section_type="cta",
                content=outline.call_to_action,
                duration_hint="3-5 seconds",
                visual_note="CTA card"
            ))
            return sections
        
        # Try to parse structured script
        current_type = "hook"
        current_content = []
        current_visual = ""
        
        lines = script_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers
            upper = line.upper()
            if "HOOK" in upper and (upper.startswith("HOOK") or upper.startswith("1.")):
                if current_content:
                    sections.append(ScriptSection(
                        section_type=current_type,
                        content="\n".join(current_content),
                        duration_hint=self._estimate_duration(current_type),
                        visual_note=current_visual
                    ))
                    current_content = []
                    current_visual = ""
                current_type = "hook"
            elif "BODY" in upper or "MAIN" in upper or (upper.startswith("2.") and "BODY" in upper.upper()):
                if current_content:
                    sections.append(ScriptSection(
                        section_type=current_type,
                        content="\n".join(current_content),
                        duration_hint=self._estimate_duration(current_type),
                        visual_note=current_visual
                    ))
                    current_content = []
                    current_visual = ""
                current_type = "body"
            elif "CTA" in upper or "CALL TO ACTION" in upper or upper.startswith("3."):
                if current_content:
                    sections.append(ScriptSection(
                        section_type=current_type,
                        content="\n".join(current_content),
                        duration_hint=self._estimate_duration(current_type),
                        visual_note=current_visual
                    ))
                    current_content = []
                    current_visual = ""
                current_type = "cta"
            elif line.startswith("[") and line.endswith("]"):
                # Visual note
                current_visual = line[1:-1]
            else:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections.append(ScriptSection(
                section_type=current_type,
                content="\n".join(current_content),
                duration_hint=self._estimate_duration(current_type),
                visual_note=current_visual
            ))
        
        # If no sections were parsed, create one from the full text
        if not sections:
            sections.append(ScriptSection(
                section_type="body",
                content=script_text,
                duration_hint=outline.estimated_duration,
                visual_note=""
            ))
        
        return sections
    
    def _estimate_duration(self, section_type: str) -> str:
        """Estimate duration for a section type."""
        durations = {
            "hook": "2-3 seconds",
            "body": "15-30 seconds",
            "cta": "3-5 seconds",
            "transition": "1-2 seconds",
            "closing": "3-5 seconds"
        }
        return durations.get(section_type, "5-10 seconds")
