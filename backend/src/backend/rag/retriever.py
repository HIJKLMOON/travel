from backend.rag.vector_store import query_documents


def retrieve(document_id: str, query: str, k: int = 4) -> list[dict]:
    return query_documents(document_id, query, k=k)
