import json
import os
import re

import jieba
import numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

from app.config import settings

_DATA_DIR = os.path.join(settings.CHROMA_PERSIST_DIR, "doc_data")

_embedding_model: TextEmbedding | None = None


def _get_embedder() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        os.environ.setdefault("HF_ENDPOINT", settings.HF_ENDPOINT)
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    return _embedding_model


def _doc_path(document_id: str) -> str:
    return os.path.join(_DATA_DIR, f"{document_id}.json")


def _vec_path(document_id: str) -> str:
    return os.path.join(_DATA_DIR, f"{document_id}.npy")


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"[^\w\u4e00-\u9fff\s]", " ", text.lower())
    tokens = []
    for word in text.split():
        if re.search(r"[\u4e00-\u9fff]", word):
            tokens.extend(jieba.lcut(word))
        else:
            tokens.append(word)
    return [t for t in tokens if len(t) > 1]


def add_documents(
    document_id: str, chunks: list[str], metadatas: list[dict] | None = None
):
    os.makedirs(_DATA_DIR, exist_ok=True)

    data = {
        "chunks": chunks,
        "metadatas": metadatas or [{} for _ in chunks],
    }
    with open(_doc_path(document_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)

    embedder = _get_embedder()
    vectors = np.array(list(embedder.embed(chunks)), dtype=np.float32)
    np.save(_vec_path(document_id), vectors)


def query_documents(
    document_id: str, query: str, k: int = 4, method: str = "hybrid"
) -> list[dict]:
    doc_path = _doc_path(document_id)
    if not os.path.exists(doc_path):
        return []

    with open(doc_path, encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]
    metadatas = data["metadatas"]

    if method == "bm25":
        return _bm25_search(chunks, metadatas, query, k)
    elif method == "vector":
        return _vector_search(chunks, metadatas, query, k, document_id)
    else:
        bm25_r = _bm25_search(chunks, metadatas, query, k * 2)
        vec_r = _vector_search(chunks, metadatas, query, k * 2, document_id)
        return _merge_hybrid(bm25_r, vec_r, k)


def query_multi_documents(
    document_ids: list[str], query: str, k_per_doc: int = 3, method: str = "hybrid"
) -> list[dict]:
    all_results = []
    for doc_id in document_ids:
        results = query_documents(doc_id, query, k=k_per_doc, method=method)
        for r in results:
            r["document_id"] = doc_id
        all_results.extend(results)

    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_results


def _merge_hybrid(bm25: list[dict], vec: list[dict], k: int) -> list[dict]:
    best = {}
    for r in bm25 + vec:
        idx = r.get("_index")
        if idx not in best or r.get("score", 0) > best[idx].get("score", 0):
            best[idx] = r
    merged = sorted(best.values(), key=lambda x: x.get("score", 0), reverse=True)
    return merged[:k]


def _bm25_search(
    chunks: list[str], metadatas: list[dict], query: str, k: int
) -> list[dict]:
    tokenized = [_tokenize(c) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(_tokenize(query))
    top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    results = []
    for idx in top:
        results.append(
            {
                "content": chunks[idx],
                "_index": idx,
                "score": float(scores[idx]),
                **metadatas[idx],
            }
        )
    return results


def _vector_search(
    chunks: list[str], metadatas: list[dict], query: str, k: int, document_id: str
) -> list[dict]:
    vec_path = _vec_path(document_id)

    if not os.path.exists(vec_path):
        embedder = _get_embedder()
        vectors = np.array(list(embedder.embed(chunks)), dtype=np.float32)
        np.save(vec_path, vectors)

    vectors = np.load(vec_path)
    embedder = _get_embedder()
    query_vec = np.array(list(embedder.embed([query])))[0]

    scores = np.dot(vectors, query_vec) / (
        np.linalg.norm(vectors, axis=1) * np.linalg.norm(query_vec) + 1e-8
    )
    top = np.argsort(scores)[::-1][:k]

    results = []
    for idx in top:
        results.append(
            {
                "content": chunks[idx],
                "_index": int(idx),
                "score": float(scores[idx]),
                **metadatas[idx],
            }
        )
    return results


def delete_collection(document_id: str):
    for p in [_doc_path(document_id), _vec_path(document_id)]:
        if os.path.exists(p):
            os.remove(p)


def list_collections() -> list[str]:
    if not os.path.exists(_DATA_DIR):
        return []
    return sorted(
        set(
            f.replace(".json", "").replace(".npy", "")
            for f in os.listdir(_DATA_DIR)
            if f.endswith(".json") or f.endswith(".npy")
        )
    )


def get_chunk_count(document_id: str) -> int:
    p = _doc_path(document_id)
    if not os.path.exists(p):
        return 0
    with open(p, encoding="utf-8") as f:
        return len(json.load(f)["chunks"])
