from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from backend.config import settings
from backend.rag.vector_store import query_multi_documents

_llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    api_key=SecretStr(settings.DEEPSEEK_API_KEY),
    base_url=settings.DEEPSEEK_BASE_URL,
    temperature=0.3,
    streaming=True,
)


async def stream_chat(
    document_ids: list[str],
    message: str,
    history: list[dict[str, str]] | None = None,
):
    query = message.strip()
    chunks = query_multi_documents(document_ids, query, k_per_doc=3)

    if chunks:
        context = "\n\n---\n\n".join(
            f"[文档] {c.get('document_id', c.get('source', 'unknown'))}"
            + (f" | {c['source'].split('/')[-1]}" if c.get("source") else "")
            + (f" (第{c['page']}页)" if c.get("page") else "")
            + f"\n{c['content']}"
            for c in chunks
        )
        system_prompt = f"""你是一个文档问答助手。根据提供的文档内容回答用户问题。

回答规则：
1. 只基于给定的文档内容回答，不要编造信息
2. 在答案末尾标注来源（文档ID和文件名）
3. 如果文档内容不足以回答问题，请明确告知
4. 用中文回答

以下是文档内容：
{context}"""
    else:
        system_prompt = "文档库中没有找到相关内容。请如实告知用户。"

    yield {"event": "sources", "data": chunks}

    messages = []
    if history:
        for h in history:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                messages.append(AIMessage(content=h["content"]))
    messages.append(HumanMessage(content=message))

    full_content = ""
    async for chunk in _llm.astream(
        [
            SystemMessage(content=system_prompt),
            *messages,
        ]
    ):
        if chunk.content:
            full_content += chunk.content
            yield {"event": "token", "data": chunk.content}

    yield {"event": "done", "data": full_content}
