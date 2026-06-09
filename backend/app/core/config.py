from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal Health Copilot API"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./health_copilot.db"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    ocr_language: str = "eng"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_local_path: str = "./qdrant_data"
    qdrant_prefer_local: bool = True
    rag_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def get_qdrant_url() -> str:
    """Normalize Qdrant URL (Render internal hostport omits http://)."""
    url = settings.qdrant_url.strip()
    if url and not url.startswith("http"):
        return f"http://{url}"
    return url


def get_cors_origins() -> list[str]:
    origins: list[str] = []
    for origin in settings.cors_origins.split(","):
        cleaned = origin.strip()
        if not cleaned:
            continue
        if not cleaned.startswith("http"):
            cleaned = f"https://{cleaned}"
        origins.append(cleaned)
    return origins
