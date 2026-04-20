from factory_rag.utils import hash_embed


class EmbeddingService:
    def __init__(self, settings, gemini_client=None):
        self.settings = settings
        self.gemini_client = gemini_client
        self.model = None
        self.model_checked = False
        self.backend_name = "hash-embedding"
        self.vector_size = settings.vector_size

    def _load_model(self):
        if self.model_checked:
            return

        self.model_checked = True

        if self.settings.embedding_backend == "gemini":
            if self.gemini_client and self.gemini_client.is_configured():
                self.model = "gemini"
                self.backend_name = self.settings.gemini_embedding_model
            else:
                self.model = None
                self.backend_name = "hash-embedding"
            return

        if self.settings.embedding_backend != "sentence-transformer":
            self.model = None
            self.backend_name = "hash-embedding"
            return

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.settings.embedding_model)
            size = self.model.get_sentence_embedding_dimension()
            if size:
                self.vector_size = size
            self.backend_name = self.settings.embedding_model
        except Exception:
            self.model = None
            self.backend_name = "hash-embedding"

    def status_backend(self):
        if self.settings.embedding_backend == "gemini" and self.gemini_client and self.gemini_client.is_configured():
            return self.settings.gemini_embedding_model
        if self.settings.embedding_backend == "sentence-transformer":
            return self.settings.embedding_model
        return "hash-embedding"

    def embed_texts(self, texts):
        if not texts:
            return []

        self._load_model()

        if self.model == "gemini" and self.gemini_client:
            vectors = self.gemini_client.embed_documents(texts)
            if vectors:
                return vectors

        if self.model is not None and self.model != "gemini":
            vectors = self.model.encode(texts, normalize_embeddings=True)
            return vectors.tolist()

        vectors = []
        for text in texts:
            vectors.append(hash_embed(text, self.vector_size))
        return vectors

    def embed_query(self, text):
        self._load_model()

        if self.model == "gemini" and self.gemini_client:
            vector = self.gemini_client.embed_query(text)
            if vector:
                return vector

        vectors = self.embed_texts([text])
        return vectors[0]
