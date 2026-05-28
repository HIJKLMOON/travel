from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str = "sk-*"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-flash"
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    UPLOAD_DIR: str = "./uploads"

    RETRIEVER_TYPE: str = "hybrid"
    HF_ENDPOINT: str = "https://hf-mirror.com"


settings = Settings()
