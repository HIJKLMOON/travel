import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.agent.graph import run_agent
from backend.agent.stream import stream_chat
from backend.models.schemas import ChatRequest, ChatResponse, SourceItem

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if not request.document_ids:
        raise HTTPException(
            status_code=400, detail="At least one document_id is required"
        )

    try:
        answer, sources = run_agent(
            document_ids=request.document_ids,
            message=request.message,
            history=request.history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return ChatResponse(
        answer=answer,
        sources=[
            SourceItem(
                content=s.get("content", ""),
                source=s.get("source", ""),
                page=s.get("page"),
                score=s.get("score", 0.0),
                document_id=s.get("document_id", ""),
            )
            for s in sources
        ],
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if not request.document_ids:
        raise HTTPException(
            status_code=400, detail="At least one document_id is required"
        )

    async def event_generator():
        try:
            async for event in stream_chat(
                document_ids=request.document_ids,
                message=request.message,
                history=request.history,
            ):
                if event["event"] == "sources":
                    yield {
                        "event": "sources",
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                elif event["event"] == "token":
                    yield {"event": "token", "data": event["data"]}
                elif event["event"] == "done":
                    yield {"event": "done", "data": event["data"]}
            yield {"event": "end", "data": ""}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
