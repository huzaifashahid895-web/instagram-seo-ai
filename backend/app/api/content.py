# backend/app/api/content.py — Content library routes
# Cost classification: FREE + OPEN SOURCE

import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.brand_profile import BrandProfile
from app.models.content_analysis import ContentAnalysis
from app.models.content_asset import ContentAsset
from app.models.rag_chunk import RagChunk
from app.models.user import User
from app.schemas.content import ContentAnalysisResponse, ContentAssetResponse
from app.services.embeddings.sentence_transformers_provider import default_embedding_provider
from app.services.media_analysis import media_analyzer
from app.services.stt.faster_whisper_provider import default_stt_provider
from app.services.storage import storage
from app.services.thumbnail import thumbnail_generator
from app.services.vector_store.chroma_store import default_vector_store
from app.services.vision.clip_vision_provider import default_vision_provider

logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/upload", response_model=ContentAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_content(
    brand_profile_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAsset:
    brand_profile = db.get(BrandProfile, brand_profile_id)
    if brand_profile is None or brand_profile.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")

    stored_file = await storage.save_upload(file, bucket="raw")
    asset = ContentAsset(
        brand_profile_id=brand_profile.id,
        filename=stored_file.original_filename,
        file_path=stored_file.relative_path,
        file_size=stored_file.file_size,
        mime_type=stored_file.mime_type,
        media_type=stored_file.media_type,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.post("/{asset_id}/analyze", response_model=ContentAnalysisResponse)
def analyze_content_asset(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAnalysis:
    asset = db.get(ContentAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    brand_profile = db.get(BrandProfile, asset.brand_profile_id)
    if brand_profile is None or brand_profile.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    analysis = asset.analysis or ContentAnalysis(asset_id=asset.id)
    analysis = media_analyzer.populate_analysis(asset, analysis)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.post("/{asset_id}/transcribe")
def transcribe_content_asset(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Transcribe audio/video content using faster-whisper.
    Stores transcript as JSON in ContentAnalysis.transcript_data.
    """
    asset = db.get(ContentAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    brand_profile = db.get(BrandProfile, asset.brand_profile_id)
    if brand_profile is None or brand_profile.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    if asset.media_type not in {"video", "audio"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only video and audio files can be transcribed"
        )

    # Get or create analysis record
    analysis = asset.analysis or ContentAnalysis(asset_id=asset.id)

    # Transcribe using faster-whisper
    source_path = storage.resolve(asset.file_path)
    logger.info(f"Transcribing asset {asset_id}")
    transcript_result = default_stt_provider.transcribe(source_path)

    # Store transcript data as JSON
    analysis.transcript_data = transcript_result.model_dump()
    analysis.transcript_text = transcript_result.text
    analysis.language = transcript_result.language

    # Generate and store embedding for transcript
    if transcript_result.text:
        logger.info(f"Generating embedding for transcript")
        embedding = default_embedding_provider.embed_text(transcript_result.text)
        
        # Store in vector DB for RAG
        doc_id = f"asset_{asset_id}_transcript"
        default_vector_store.add_documents(
            texts=[transcript_result.text],
            embeddings=[embedding],
            metadatas=[{
                "asset_id": str(asset_id),
                "type": "transcript",
                "brand_profile_id": str(brand_profile.id),
            }],
            ids=[doc_id],
        )
        
        # Create RAG chunk record
        rag_chunk = RagChunk(
            brand_profile_id=brand_profile.id,
            asset_id=asset.id,
            chunk_text=transcript_result.text,
            chunk_index=0,
            vector_id=doc_id,
            metadata_={
                "type": "transcript",
                "language": transcript_result.language,
            },
        )
        db.add(rag_chunk)

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "asset_id": str(asset_id),
        "transcript": transcript_result.text,
        "language": transcript_result.language,
        "segments": len(transcript_result.segments),
        "duration": transcript_result.duration,
    }


@router.post("/{asset_id}/visual-analysis")
def visual_analyze_content_asset(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Perform visual analysis on images using CLIP for tags and embeddings.
    """
    asset = db.get(ContentAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    brand_profile = db.get(BrandProfile, asset.brand_profile_id)
    if brand_profile is None or brand_profile.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    if asset.media_type != "image":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files can be visually analyzed"
        )

    # Get or create analysis record
    analysis = asset.analysis or ContentAnalysis(asset_id=asset.id)

    # Analyze using CLIP vision provider
    source_path = storage.resolve(asset.file_path)
    logger.info(f"Performing visual analysis on asset {asset_id}")
    vision_result = default_vision_provider.analyze(source_path)

    # Store visual analysis data
    analysis.visual_tags = vision_result.tags
    analysis.scene_type = vision_result.scene_type
    analysis.caption = vision_result.caption

    # Store image embedding in vector DB
    if vision_result.embedding:
        logger.info(f"Storing image embedding in vector DB")
        doc_id = f"asset_{asset_id}_visual"
        
        # Create a text representation for searchability
        text_repr = f"Image: {vision_result.caption or 'visual content'}. Tags: {', '.join(vision_result.tags)}"
        
        default_vector_store.add_documents(
            texts=[text_repr],
            embeddings=[vision_result.embedding],
            metadatas=[{
                "asset_id": str(asset_id),
                "type": "visual",
                "brand_profile_id": str(brand_profile.id),
                "tags": json.dumps(vision_result.tags),
                "scene_type": vision_result.scene_type or "",
            }],
            ids=[doc_id],
        )
        
        # Create RAG chunk record
        rag_chunk = RagChunk(
            brand_profile_id=brand_profile.id,
            asset_id=asset.id,
            chunk_text=text_repr,
            chunk_index=0,
            vector_id=doc_id,
            metadata_={
                "type": "visual",
                "tags": vision_result.tags,
                "scene_type": vision_result.scene_type,
            },
        )
        db.add(rag_chunk)

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "asset_id": str(asset_id),
        "tags": vision_result.tags,
        "scene_type": vision_result.scene_type,
        "caption": vision_result.caption,
    }


@router.get("/", response_model=list[ContentAssetResponse])
def list_content_assets(
    brand_profile_id: uuid.UUID | None = Query(None),
    media_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ContentAsset]:
    """
    List content assets in the library with optional filtering.
    """
    # Build query
    query = select(ContentAsset).join(BrandProfile).where(BrandProfile.user_id == current_user.id)
    
    if brand_profile_id:
        query = query.where(ContentAsset.brand_profile_id == brand_profile_id)
    
    if media_type:
        query = query.where(ContentAsset.media_type == media_type)
    
    # Order by most recent first
    query = query.order_by(ContentAsset.created_at.desc()).limit(limit).offset(offset)
    
    assets = db.execute(query).scalars().all()
    return list(assets)


@router.get("/{asset_id}", response_model=ContentAssetResponse)
def get_content_asset(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContentAsset:
    """Get a single content asset by ID."""
    asset = db.get(ContentAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    brand_profile = db.get(BrandProfile, asset.brand_profile_id)
    if brand_profile is None or brand_profile.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content asset not found")

    return asset
