import os
import uuid
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def load_document(file_path: str) -> list[dict]:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return _load_pdf(file_path)
    elif ext in (".txt", ".md"):
        return _load_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _load_pdf(file_path: str) -> list[dict]:
    reader = PdfReader(file_path)
    items = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text.strip():
            items.append(
                {
                    "content": text,
                    "metadata": {"source": file_path, "page": i + 1},
                }
            )
    return items


def _load_text(file_path: str) -> list[dict]:
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
    return [{"content": content, "metadata": {"source": file_path}}]


def split_items(items: list[dict]) -> tuple[list[str], list[dict]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )

    texts = [item["content"] for item in items]
    metadatas = [item["metadata"] for item in items]
    all_docs = splitter.create_documents(texts, metadatas=metadatas)

    chunks = [doc.page_content for doc in all_docs]
    chunk_metadatas = [doc.metadata for doc in all_docs]
    return chunks, chunk_metadatas


def generate_document_id() -> str:
    return uuid.uuid4().hex[:12]


def save_upload(file_bytes: bytes, filename: str, upload_dir: str) -> tuple[str, str]:
    os.makedirs(upload_dir, exist_ok=True)
    doc_id = generate_document_id()
    ext = Path(filename).suffix
    save_path = os.path.join(upload_dir, f"{doc_id}{ext}")
    with open(save_path, "wb") as f:
        f.write(file_bytes)
    return save_path, doc_id
