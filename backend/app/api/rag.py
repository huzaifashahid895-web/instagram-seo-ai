# backend/app/api/rag.py — RAG/Knowledge Base document management
# Cost classification: FREE + OPEN SOURCE

from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.rag_document import RagDocument
from app.models.rag_chunk import RagChunk

router = APIRouter()


@router.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all RAG documents for the current user."""
    documents = db.query(RagDocument).filter(
        RagDocument.brand_profile_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "source_type": doc.source_type,
                "content": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }
            for doc in documents
        ],
        "total": db.query(RagDocument).filter(RagDocument.brand_profile_id == current_user.id).count()
    }


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document for RAG knowledge base."""
    # Read file content
    content = await file.read()
    
    # Create document record
    document = RagDocument(
        brand_profile_id=current_user.id,
        source_type="note",
        title=file.filename,
        content=content.decode('utf-8', errors='ignore'),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # TODO: Process document asynchronously (extract text, chunk, embed)
    # For now, just mark as pending
    
    return {
        "id": document.id,
        "title": document.title,
        "message": "Document uploaded. Processing will begin shortly."
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document by ID."""
    document = db.query(RagDocument).filter(
        RagDocument.id == document_id,
        RagDocument.brand_profile_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get chunks
    chunks = db.query(RagChunk).filter(RagChunk.document_id == document_id).all()
    
    return {
        "id": document.id,
        "title": document.title,
        "source_type": document.source_type,
        "content": document.content,
        "chunks": [
            {
                "id": chunk.id,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ],
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its chunks."""
    document = db.query(RagDocument).filter(
        RagDocument.id == document_id,
        RagDocument.brand_profile_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete chunks first
    db.query(RagChunk).filter(RagChunk.document_id == document_id).delete()
    
    # Delete document
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.post("/search")
async def search_knowledge_base(
    query: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search the knowledge base using semantic search."""
    # TODO: Implement vector search with embeddings
    # For now, return empty results
    
    return {
        "query": query,
        "results": [],
        "message": "Semantic search requires embeddings to be configured. See SETUP_AI_MODELS.md"
    }
