import os

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import settings
from backend.models.schemas import UploadResponse
from backend.rag.loader import load_document, save_upload, split_items
from backend.rag.vector_store import add_documents, get_chunk_count

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("pdf", "txt", "md"):
        raise HTTPException(
            status_code=400, detail="Only PDF, TXT, MD files are supported"
        )

    content = await file.read()
    file_path, doc_id = save_upload(content, file.filename, settings.UPLOAD_DIR)

    try:
        items = load_document(file_path)
        chunks, metadatas = split_items(items)
        add_documents(doc_id, chunks, metadatas)
    except Exception as e:
        # 索引构建失败时清理已保存的文件，避免产生"死文档"
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500, detail=f"Failed to process document: {str(e)}"
        )

    return UploadResponse(
        document_id=doc_id,
        filename=file.filename,
        chunks=get_chunk_count(doc_id),
        message="Document uploaded and indexed successfully",
    )
