import json
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import DeleteResponse, DocumentInfo
from app.rag.vector_store import delete_collection, get_chunk_count, list_collections

router = APIRouter()


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    if not os.path.exists(settings.UPLOAD_DIR):
        return []

    docs = []
    for fname in os.listdir(settings.UPLOAD_DIR):
        file_path = os.path.join(settings.UPLOAD_DIR, fname)
        doc_id = os.path.splitext(fname)[0]
        created = datetime.fromtimestamp(os.path.getctime(file_path))
        docs.append(
            DocumentInfo(
                document_id=doc_id,
                filename=fname,
                chunks=get_chunk_count(doc_id),
                created_at=created.isoformat(),
            )
        )
    return docs


@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    delete_collection(document_id)
    for fname in os.listdir(settings.UPLOAD_DIR):
        if fname.startswith(document_id):
            os.remove(os.path.join(settings.UPLOAD_DIR, fname))
            return DeleteResponse(message="Document deleted successfully")
    raise HTTPException(status_code=404, detail="Document not found")
