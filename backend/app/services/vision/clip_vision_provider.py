# backend/app/services/vision/clip_vision_provider.py — CLIP-based vision analysis
# Cost classification: FREE + OPEN SOURCE (MIT)

import logging
from pathlib import Path

from PIL import Image

from app.services.providers import VisionAnalysis, VisionProvider

logger = logging.getLogger(__name__)


class CLIPVisionProvider:
    """
    Vision provider using OpenCLIP for image embeddings and zero-shot classification.
    Model recommendation: 'ViT-B-32' with 'openai' pretrained weights (best quality/speed tradeoff)
    """

    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "openai",
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.pretrained = pretrained
        self.device = device or "cpu"
        self._model = None
        self._preprocess = None
        self._tokenizer = None

    def _ensure_model(self):
        """Lazy-load the model on first use to avoid slowing down startup."""
        if self._model is not None:
            return

        try:
            import open_clip
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "open_clip_torch not installed. Install with: pip install open_clip_torch"
            ) from exc

        logger.info(f"Loading CLIP model '{self.model_name}' ({self.pretrained}) on {self.device}")
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            self.model_name, pretrained=self.pretrained, device=self.device
        )
        self._tokenizer = open_clip.get_tokenizer(self.model_name)
        self._model.eval()
        logger.info("CLIP model loaded successfully")

    def analyze(self, image_path: str | Path) -> VisionAnalysis:
        """
        Analyze an image using CLIP for tags and embeddings.

        Args:
            image_path: Path to image file

        Returns:
            VisionAnalysis with tags, scene type, and embedding
        """
        self._ensure_model()
        image_path = Path(image_path)

        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        logger.info(f"Analyzing image {image_path.name}")

        # Load and preprocess image
        image = Image.open(image_path).convert("RGB")
        image_tensor = self._preprocess(image).unsqueeze(0).to(self.device)

        # Generate image embedding
        import torch
        with torch.no_grad():
            image_features = self._model.encode_image(image_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            embedding = image_features.cpu().numpy()[0].tolist()

        # Extract tags using zero-shot classification
        tags = self.extract_tags(image_path)

        # Determine scene type
        scene_candidates = [
            "outdoor scene",
            "indoor scene",
            "portrait",
            "landscape",
            "product photo",
            "food photo",
            "text or graphics",
            "abstract art",
        ]
        scene_type = self._classify_zero_shot(image, scene_candidates)

        return VisionAnalysis(
            caption=None,  # CLIP doesn't generate captions natively
            tags=tags,
            scene_type=scene_type,
            embedding=embedding,
        )

    def caption(self, image_path: str | Path) -> str:
        """
        Generate a caption for an image. CLIP doesn't natively caption,
        so this returns a basic description based on tags.
        """
        analysis = self.analyze(image_path)
        if analysis.tags:
            return f"Image showing: {', '.join(analysis.tags[:5])}"
        return "Image content"

    def extract_tags(self, image_path: str | Path) -> list[str]:
        """
        Extract semantic tags from an image using zero-shot classification.

        Args:
            image_path: Path to image file

        Returns:
            List of detected tags
        """
        self._ensure_model()
        image_path = Path(image_path)

        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        image = Image.open(image_path).convert("RGB")

        # Common Instagram content tags
        candidate_tags = [
            "person",
            "people",
            "face",
            "smile",
            "fashion",
            "style",
            "food",
            "restaurant",
            "travel",
            "nature",
            "beach",
            "sunset",
            "city",
            "architecture",
            "product",
            "technology",
            "fitness",
            "workout",
            "pet",
            "dog",
            "cat",
            "art",
            "music",
            "text",
            "logo",
            "quote",
        ]

        # Classify and keep tags with high confidence
        tags = []
        import torch
        with torch.no_grad():
            image_tensor = self._preprocess(image).unsqueeze(0).to(self.device)
            text_tokens = self._tokenizer(candidate_tags).to(self.device)

            image_features = self._model.encode_image(image_tensor)
            text_features = self._model.encode_text(text_tokens)

            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).softmax(dim=-1)
            values, indices = similarity[0].topk(5)

            # Keep tags with confidence > 0.1 (10%)
            for value, idx in zip(values, indices):
                if value.item() > 0.1:
                    tags.append(candidate_tags[idx.item()])

        logger.info(f"Extracted {len(tags)} tags: {tags}")
        return tags

    def _classify_zero_shot(self, image: Image.Image, candidates: list[str]) -> str:
        """Helper to classify image against a list of text candidates."""
        import torch
        with torch.no_grad():
            image_tensor = self._preprocess(image).unsqueeze(0).to(self.device)
            text_tokens = self._tokenizer(candidates).to(self.device)

            image_features = self._model.encode_image(image_tensor)
            text_features = self._model.encode_text(text_tokens)

            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).softmax(dim=-1)
            best_idx = similarity.argmax().item()

            return candidates[best_idx]


# Default instance using ViT-B-32 on CPU
default_vision_provider = CLIPVisionProvider(
    model_name="ViT-B-32",
    pretrained="openai",
    device="cpu"
)
