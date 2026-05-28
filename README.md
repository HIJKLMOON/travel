# Doc Agent — 智能文档问答助手

上传 PDF、TXT 或 Markdown 文档，通过 AI 智能问答快速获取信息。支持多文档联合检索、流式输出（打字机效果），可一键 Docker 部署。

---

## 功能特性

- **📄 多格式支持** — 上传 PDF / TXT / Markdown，自动解析并分块索引
- **🔍 混合检索** — BM25 关键词 + 向量语义检索融合，兼顾精确匹配与语义理解
- **🤖 LangGraph Agent** — 智能路由：问候直接回复，复杂问题触发 RAG 检索
- **💬 多文档对话** — 同时选中多个文档，跨文档联合问答
- **⚡ 流式输出** — SSE 协议逐 token 推送，前端打字机效果实时渲染
- **🐳 Docker 部署** — 一键启动，数据持久化
- **🌐 国内友好** — HuggingFace 镜像加速，中文分词优化

---

## 架构概览

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│  Next.js  │────▶│   FastAPI    │────▶│   LangGraph      │
│  前端     │◀────│   后端       │◀────│   Agent 工作流    │
└──────────┘     └──────┬───────┘     └────────┬─────────┘
                        │                      │
                        ▼                      ▼
                  ┌──────────────┐     ┌──────────────────┐
                  │  BM25 检索    │     │  fastembed 向量   │
                  │  (关键词)     │     │  (语义检索)       │
                  └──────────────┘     └──────────────────┘
                        │                      │
                        └──────────┬───────────┘
                                   ▼
                          ┌──────────────────┐
                          │  DeepSeek Chat    │
                          │  (LLM 回答生成)   │
                          └──────────────────┘
```

### 数据流

1. 用户上传文档 → FastAPI 解析（PyPDF / 文本）→ 分块（500 字符 + 80 重叠）
2. 每块计算向量（BGE-small-zh）并存 BM25 索引 → 持久化到磁盘
3. 用户提问 → LangGraph Agent 路由 → 混合检索（BM25 + 向量）→ 取 Top-K
4. 检索结果 + 对话历史 → DeepSeek API → 流式逐 token 返回前端

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **前端** | Next.js 16 + React 19 + Tailwind CSS 4 | SPA 页面，流式渲染 |
| **后端** | FastAPI + Uvicorn | REST API + SSE 流式接口 |
| **AI 编排** | LangGraph 1.2 + LangChain | Agent 状态机、条件路由 |
| **LLM** | DeepSeek Chat API | 问答生成 |
| **检索** | BM25 (rank-bm25) + BGE-small-zh (fastembed) | 混合检索 |
| **分词** | jieba | 中文分词 |
| **部署** | Docker + docker-compose | 容器化一键部署 |

---

## 快速开始

### 前置条件

- Python >= 3.12
- Node.js >= 18 + pnpm（`npm i -g pnpm`）
- DeepSeek API Key（[官网获取](https://platform.deepseek.com)）

### 1. 克隆并配置

```bash
git clone <your-repo-url> doc-agent
cd doc-agent

# 填写 API Key
cp backend/.env backend/.env.local
# 编辑 backend/.env.local，填入 DEEPSEEK_API_KEY
```

### 2. 启动后端

```bash
cd backend
uv sync                  # 安装依赖
uv run uvicorn backend.main:app --reload --port 8000
```

后端启动在 `http://localhost:8000`，API 文档在 `http://localhost:8000/docs`。

### 3. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

前端启动在 `http://localhost:3000`。

---

## Docker 部署

```bash
# 确保已填写 backend/.env 中的 DEEPSEEK_API_KEY
docker compose up --build
```

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

数据持久化在 Docker volume `doc_data` 中。

---

## 项目结构

```
doc-agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + CORS
│   │   ├── config.py            # 环境变量配置
│   │   ├── agent/
│   │   │   ├── graph.py         # LangGraph Agent 工作流
│   │   │   └── stream.py        # 流式输出生成器
│   │   ├── api/
│   │   │   ├── chat.py          # 对话接口 (POST + SSE)
│   │   │   ├── upload.py        # 文档上传接口
│   │   │   └── documents.py     # 文档管理接口
│   │   ├── rag/
│   │   │   ├── loader.py        # 文档解析 (PDF/TXT/MD)
│   │   │   └── vector_store.py  # BM25 + 向量检索引擎
│   │   └── models/
│   │       └── schemas.py       # Pydantic 数据模型
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env                     # 配置文件
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # 首页
│   │   │   ├── upload/page.tsx  # 上传页面
│   │   │   └── chat/page.tsx    # 对话页面 (含文档选择)
│   │   └── components/
│   │       ├── FileUploader.tsx  # 拖拽上传组件
│   │       └── ChatInterface.tsx # 对话流式组件
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## API 文档

### 上传文档

```http
POST /upload
Content-Type: multipart/form-data

file: <PDF/TXT/MD 文件>
```

```json
{
  "document_id": "a1b2c3d4e5f6",
  "filename": "report.pdf",
  "chunks": 12,
  "message": "Document uploaded and indexed successfully"
}
```

### 对话

```http
POST /chat
Content-Type: application/json

{
  "document_ids": ["a1b2c3d4e5f6"],
  "message": "文档的主要内容是什么？",
  "history": []
}
```

```json
{
  "answer": "根据文档内容...（来源：report.pdf）",
  "sources": [
    {
      "content": "原文段落...",
      "source": "./uploads/a1b2c3d4e5f6.pdf",
      "page": 3,
      "score": 0.64,
      "document_id": "a1b2c3d4e5f6"
    }
  ]
}
```

### 流式对话

```http
POST /chat/stream
Content-Type: application/json

{
  "document_ids": ["a1b2c3d4e5f6"],
  "message": "文档的主要内容是什么？",
  "history": []
}
```

响应为 SSE（Server-Sent Events）：

```
event: sources
data: [{"content": "...", "source": "...", ...}]

event: token
data: 根据

event: token
data: 文档

event: token
data: 内容

event: done
data: 根据文档内容...
```

### 管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/documents` | 列出所有文档 |
| `DELETE` | `/documents/{id}` | 删除文档 |
| `GET` | `/health` | 健康检查 |

---

## 配置说明

编辑 `backend/.env`：

```ini
DEEPSEEK_API_KEY=sk-xxx              # DeepSeek API Key（必填）
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1  # API 地址
LLM_MODEL=deepseek-chat              # LLM 模型名

# 检索配置
RETRIEVER_TYPE=hybrid                # bm25 / vector / hybrid
HF_ENDPOINT=https://hf-mirror.com    # HuggingFace 镜像（国内加速）

# 数据目录
CHROMA_PERSIST_DIR=./chroma_db       # 索引持久化目录
UPLOAD_DIR=./uploads                 # 上传文件目录
```

---

## 面试亮点

本项目可作为求职作品，以下是建议的面试话术：

### 检索系统
> "我实现了 BM25 关键词检索和 fastembed 向量语义检索的混合引擎，通过取最高分合并的策略，兼顾了精确匹配和语义理解。中文场景下使用 jieba 分词优化了 BM25 的 tokenize。"

### LangGraph Agent
> "用 LangGraph 构建了带条件路由的 Agent：问候语直接回复（省一次 LLM 调用），复杂问题触发 RAG 检索链路。展示了状态机编排、条件边、MemorySaver 持久化等工程实践。"

### 流式输出
> "基于 SSE 协议实现逐 token 流式输出。后端用 LangChain 的 `astream` 流式调用 LLM，前端通过 `ReadableStream` 解析 SSE 事件并实时渲染打字机效果，提升了用户体验。"

### 工程化
> "Docker 多阶段构建 + docker-compose 一键部署，生产镜像约 200MB。前端 Next.js 全静态生成，后端异步接口，CORS 跨域配置完整。"

---

## 许可

MIT License
