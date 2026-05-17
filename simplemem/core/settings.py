"""
SimpleMem runtime settings.
Reads from environment variables with sensible defaults.
"""
import os


class Settings:
    API_KEY = os.getenv("OPENAI_API_KEY", "")
    MODEL = os.getenv("SIMPLEMEM_MODEL", "gpt-4o")
    BASE_URL = os.getenv("OPENAI_BASE_URL", None)
    DB_PATH = os.getenv("SIMPLEMEM_DB_PATH", "simplemem.db")
    TABLE_NAME = os.getenv("SIMPLEMEM_TABLE", "memories")
    EMBEDDING_MODEL = os.getenv("SIMPLEMEM_EMBEDDING", "text-embedding-3-small")
    ENABLE_THINKING = False
    USE_STREAMING = False
    ENABLE_PLANNING = True
    ENABLE_REFLECTION = False
    MAX_REFLECTION_ROUNDS = 1
    ENABLE_PARALLEL_PROCESSING = False
    MAX_PARALLEL_WORKERS = 3
    ENABLE_PARALLEL_RETRIEVAL = False
    MAX_RETRIEVAL_WORKERS = 3


settings = Settings()
