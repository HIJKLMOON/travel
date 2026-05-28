import json
import os
import re

import jieba
import numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

from backend.config import settings

_DATA_DIR = os.path.join(settings.CHROMA_PERSIST_DIR, "doc_data")

_embedding_model: TextEmbedding | None = None
_embedding_available: bool = True


def _get_embedder() -> TextEmbedding | None:
    global _embedding_model, _embedding_available
    if not _embedding_available:
        return None
    if _embedding_model is None:
        os.environ.setdefault("HF_ENDPOINT", settings.HF_ENDPOINT)
        # 强制设置下载超时（setdefault 可能不生效）
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "15"
        os.environ["HF_HUB_HTTP_TIMEOUT"] = "15"
        try:
            _embedding_model = _load_embedder_with_timeout()
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to load embedding model, falling back to BM25-only: {e}"
            )
            _embedding_available = False
            return None
    return _embedding_model


def _load_embedder_with_timeout(timeout: int = 20) -> TextEmbedding:
    """带超时的嵌入模型加载，避免网络问题阻塞主流程。"""
    import concurrent.futures

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(TextEmbedding, model_name="BAAI/bge-small-zh-v1.5")
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False)
        raise TimeoutError(f"Embedding model download timed out after {timeout}s")
    except Exception:
        executor.shutdown(wait=False)
        raise


def _doc_path(document_id: str) -> str:
    return os.path.join(_DATA_DIR, f"{document_id}.json")


def _vec_path(document_id: str) -> str:
    return os.path.join(_DATA_DIR, f"{document_id}.npy")


def preload_embedding_model():
    """预加载嵌入模型，避免在首次上传时临时下载导致超时。"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Preloading embedding model BAAI/bge-small-zh-v1.5...")
    try:
        _get_embedder()
        logger.info("Embedding model loaded successfully")
    except Exception as e:
        logger.warning(f"Failed to preload embedding model: {e}")
        logger.warning("Model will be downloaded on first upload request")


_STOP_WORDS = frozenset(
    {
        # Chinese common stop words
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "你",
        "会",
        "着",
        "没有",
        "看",
        "好",
        "自己",
        "这",
        "他",
        "她",
        "它",
        "们",
        "那",
        "些",
        "为",
        "所以",
        "但是",
        "可以",
        "这个",
        "那个",
        "什么",
        "怎么",
        "如何",
        "因为",
        "所以",
        "如果",
        "虽然",
        "而且",
        "或者",
        "还是",
        "只是",
        # English common stop words
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "because",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "i",
        "me",
        "my",
        "myself",
        "we",
        "our",
        "ours",
        "you",
        "your",
        "yours",
        "he",
        "him",
        "his",
        "she",
        "her",
        "hers",
        "they",
        "them",
        "their",
        "theirs",
        "what",
        "which",
        "who",
        "whom",
    }
)


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"[^\w\u4e00-\u9fff\s]", " ", text.lower())
    tokens = []
    for word in text.split():
        if re.search(r"[\u4e00-\u9fff]", word):
            tokens.extend(jieba.lcut(word))
        else:
            tokens.append(word)
    return [t for t in tokens if t not in _STOP_WORDS]


def add_documents(
    document_id: str, chunks: list[str], metadatas: list[dict] | None = None
):
    import logging

    logger = logging.getLogger(__name__)

    os.makedirs(_DATA_DIR, exist_ok=True)

    data = {
        "chunks": chunks,
        "metadatas": metadatas or [{} for _ in chunks],
    }
    with open(_doc_path(document_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=str)

    embedder = _get_embedder()
    if embedder is not None:
        try:
            vectors = np.array(list(embedder.embed(chunks)), dtype=np.float32)
            np.save(_vec_path(document_id), vectors)
        except Exception as e:
            logger.warning(f"Vector embedding failed, index will use BM25 only: {e}")
    else:
        logger.info("Vector model not available, index uses BM25 only")


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
        # hybrid: try vector search, fall back to BM25-only if unavailable
        vec_r = _vector_search(chunks, metadatas, query, k * 2, document_id)
        if not vec_r:
            return _bm25_search(chunks, metadatas, query, k)
        bm25_r = _bm25_search(chunks, metadatas, query, k * 2)
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
        if embedder is None:
            return []
        try:
            vectors = np.array(list(embedder.embed(chunks)), dtype=np.float32)
            np.save(vec_path, vectors)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Vector embedding failed during query, skipping vector search: {e}"
            )
            return []

    vectors = np.load(vec_path)
    embedder = _get_embedder()
    if embedder is None:
        return []
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
