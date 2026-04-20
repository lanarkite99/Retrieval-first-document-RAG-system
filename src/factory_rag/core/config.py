import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings:
    def __init__(self):
        self.app_name = os.getenv("RAG_APP_NAME", "factory-rag")
        self.postgres_dsn = os.getenv(
            "RAG_POSTGRES_DSN",
            "postgresql://rag:ragpass@localhost:5432/ragdb",
        )
        self.qdrant_url = os.getenv("RAG_QDRANT_URL", "http://localhost:6333")
        self.qdrant_collection = os.getenv("RAG_QDRANT_COLLECTION", "document_chunks")
        self.opensearch_url = os.getenv("RAG_OPENSEARCH_URL", "http://localhost:9200")
        self.opensearch_index = os.getenv("RAG_OPENSEARCH_INDEX", "document_chunks")
        self.redis_url = os.getenv("RAG_REDIS_URL", "redis://localhost:6379/0")

        self.embedding_backend = os.getenv("RAG_EMBEDDING_BACKEND", "sentence-transformer")
        self.embedding_model = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        self.gemini_embedding_model = os.getenv("RAG_GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
        self.vector_size = int(os.getenv("RAG_VECTOR_SIZE", "384"))

        self.llm_backend = os.getenv("RAG_LLM_BACKEND", "gemini")
        self.llm_model = os.getenv("RAG_LLM_MODEL", "gemini-2.5-flash")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_api_base = os.getenv(
            "RAG_GEMINI_API_BASE",
            "https://generativelanguage.googleapis.com/v1beta",
        )
        self.llm_temperature = float(os.getenv("RAG_LLM_TEMPERATURE", "0.2"))
        self.llm_max_output_tokens = int(os.getenv("RAG_LLM_MAX_OUTPUT_TOKENS", "700"))
        self.answer_context_hits = int(os.getenv("RAG_ANSWER_CONTEXT_HITS", "4"))

        self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "900"))
        self.chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
        self.enable_summary = os.getenv("RAG_ENABLE_SUMMARY", "1") == "1"
        self.cache_ttl_seconds = int(os.getenv("RAG_CACHE_TTL_SECONDS", "600"))
        self.storage_dir = Path(os.getenv("RAG_STORAGE_DIR", BASE_DIR / "storage"))
        self.data_dir = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))

    def ensure_dirs(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
