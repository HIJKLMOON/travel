FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml .python-version ./
RUN uv sync --frozen --no-dev

COPY . .

ENV HF_ENDPOINT=https://hf-mirror.com
ENV RETRIEVER_TYPE=hybrid

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
