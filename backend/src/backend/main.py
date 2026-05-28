import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import chat, documents, upload
from backend.rag.vector_store import preload_embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 后台线程预加载嵌入模型，不阻塞服务器启动
    thread = threading.Thread(target=preload_embedding_model, daemon=True)
    thread.start()
    yield


app = FastAPI(title="Doc Agent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, tags=["Upload"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(documents.router, tags=["Documents"])


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
    )
