from pydantic import BaseModel


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks: int
    message: str


class ChatRequest(BaseModel):
    document_ids: list[str] = []
    message: str
    history: list[dict[str, str]] = []


class SourceItem(BaseModel):
    content: str
    source: str = ""
    page: int | None = None
    score: float = 0.0
    document_id: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunks: int
    created_at: str


class DeleteResponse(BaseModel):
    message: str
