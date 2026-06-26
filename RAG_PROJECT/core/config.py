from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DeepSeek LLM
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"
    deepseek_temperature: float = 0.0
    deepseek_thinking_enabled: bool = False  # 启用 DeepSeek thinking 推理模式

    # OpenAI (kept for optional embeddings proxy)
    openai_api_key: str = ""
    openai_base_url: str = "https://xiaoai.plus/v1"

    # Tavily web search
    tavily_api_key: str = ""

    # Milvus vector database
    milvus_uri: str = "http://localhost:19530"
    milvus_collection: str = "t_collection01"

    # BGE local embeddings
    bge_model_name: str = "BAAI/bge-small-zh-v1.5"
    bge_device: str = "cpu"

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    log_format: str = "json"  # "json" | "text"

    # 🌐 CORS — 生产环境请改为前端实际域名
    cors_origins: str = "*"

    # Session management
    session_ttl_seconds: int = 3600
    max_history_turns: int = 10

    # Auth — 生产环境必须更换为随机字符串
    auth_secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_32_CHARS_MIN"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()