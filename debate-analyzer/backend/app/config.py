from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379"
    HF_TOKEN: str
    LLM_PROVIDER: str = "ollama"        # "openai" | "anthropic" | "ollama"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.2"
    AUDIO_DIR: Path = Path("/audio_files")
    WHISPER_MODEL: str = "base"          # "base" | "small" | "medium" | "large-v2"
    WHISPER_DEVICE: str = "cpu"          # "cpu" | "cuda"
    SILENCE_THRESHOLD_SECONDS: int = 600 # 10 minutes
    MAX_NODES_IN_GRAPH: int = 25
    PROMPT_VERSION: str = "v1"

    class Config:
        env_file = ".env"

settings = Settings()
