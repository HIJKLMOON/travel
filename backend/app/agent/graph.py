from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import SecretStr

from app.config import settings
from app.rag.vector_store import query_multi_documents

_llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    api_key=SecretStr(settings.DEEPSEEK_API_KEY),
    base_url=settings.DEEPSEEK_BASE_URL,
    temperature=0.3,
)


class AgentState(MessagesState):
    document_ids: list[str]
    retrieved_chunks: list[dict]


def route_question(state: AgentState) -> Literal["retrieve", "respond_direct"]:
    messages = state["messages"]
    last = messages[-1]
    content = last.content.lower() if isinstance(last, HumanMessage) else ""

    greeting_keywords = ["hi", "hello", "hey", "你好", "您好", "嗨"]
    if any(g in content for g in greeting_keywords) and len(content) < 20:
        return "respond_direct"

    if "?" not in content and "？" not in content and len(content) < 5:
        return "respond_direct"

    return "retrieve"


def retrieve_node(state: AgentState, config: RunnableConfig):
    document_ids = state["document_ids"]
    last_message = state["messages"][-1]
    query = last_message.content if isinstance(last_message, HumanMessage) else ""

    chunks = query_multi_documents(document_ids, query, k_per_doc=3)

    if not chunks:
        system_prompt = "文档库中没有找到相关内容。请如实告知用户。"
    else:
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

    response = _llm.invoke(
        [
            SystemMessage(content=system_prompt),
            *state["messages"],
        ]
    )

    return {
        "messages": [AIMessage(content=response.content)],
        "retrieved_chunks": chunks,
    }


def respond_direct(state: AgentState):
    response = _llm.invoke(
        [
            SystemMessage(
                content="你是一个友好的文档问答助手。回答用户问候或简单问题，回答简洁自然。"
            ),
            *state["messages"],
        ]
    )
    return {
        "messages": [AIMessage(content=response.content)],
        "retrieved_chunks": [],
    }


def build_agent():
    builder = StateGraph(AgentState)

    builder.add_node("retrieve", retrieve_node)
    builder.add_node("respond_direct", respond_direct)

    builder.add_conditional_edges(START, route_question)
    builder.add_edge("retrieve", END)
    builder.add_edge("respond_direct", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


agent = build_agent()


def run_agent(
    document_ids: list[str],
    message: str,
    history: list[dict[str, str]] | None = None,
) -> tuple[str, list[dict]]:
    messages = []
    if history:
        for h in history:
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                messages.append(AIMessage(content=h["content"]))
    messages.append(HumanMessage(content=message))

    thread_id = "_".join(document_ids) if document_ids else "default"

    config = RunnableConfig(
        recursion_limit=20,
        configurable={"thread_id": thread_id},
    )
    result = agent.invoke(
        AgentState(
            document_ids=document_ids,
            messages=messages,
            retrieved_chunks=[],
        ),
        config=config,
    )

    answer = ""
    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and msg.content:
            answer = msg.content
    retrieved = result.get("retrieved_chunks", [])

    return answer, retrieved
