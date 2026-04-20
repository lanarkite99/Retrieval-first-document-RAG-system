from factory_rag.answer_service import AnswerService
from factory_rag.cache import QueryCache
from factory_rag.config import settings
from factory_rag.embeddings import EmbeddingService
from factory_rag.gemini_client import GeminiClient
from factory_rag.ingestion_service import IngestionService
from factory_rag.metrics import Metrics
from factory_rag.opensearch_store import OpenSearchStore
from factory_rag.postgres import PostgresStore
from factory_rag.qdrant_store import QdrantStore
from factory_rag.query_service import QueryService
from factory_rag.retrieval import RetrievalService
from factory_rag.router import QueryRouter
from factory_rag.storage import DocumentStore


class Runtime:
    def __init__(self):
        self.settings = settings
        self.metrics = Metrics()
        self.db = PostgresStore(self.settings)
        self.gemini_client = GeminiClient(self.settings)
        self.embedder = EmbeddingService(self.settings, gemini_client=self.gemini_client)
        self.qdrant_store = QdrantStore(self.settings)
        self.opensearch_store = OpenSearchStore(self.settings)
        self.cache = QueryCache(self.settings.redis_url, self.settings.cache_ttl_seconds)
        self.document_store = DocumentStore(self.settings)
        self.router = QueryRouter()
        self.retrieval_service = RetrievalService(
            self.db,
            self.embedder,
            self.qdrant_store,
            self.opensearch_store,
        )
        self.ingestion_service = IngestionService(
            self.settings,
            self.db,
            self.embedder,
            self.qdrant_store,
            self.opensearch_store,
            self.document_store,
            self.metrics,
        )
        self.answer_service = AnswerService(self.settings, self.gemini_client)
        self.query_service = QueryService(
            self.settings,
            self.db,
            self.router,
            self.retrieval_service,
            self.answer_service,
            self.cache,
            self.metrics,
        )

    def bootstrap(self):
        self.ingestion_service.bootstrap()

    def health(self):
        return {
            "app_name": self.settings.app_name,
            "postgres": self.db.ping(),
            "qdrant": self.qdrant_store.ping(),
            "opensearch": self.opensearch_store.ping(),
            "redis": self.cache.ping(),
            "embedding_backend": self.embedder.status_backend(),
            "llm_backend": self.settings.llm_backend,
            "llm_model": self.settings.llm_model,
            "gemini_configured": self.gemini_client.is_configured(),
        }


_runtime = None


def get_runtime():
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
    return _runtime
