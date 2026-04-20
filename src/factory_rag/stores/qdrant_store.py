from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from factory_rag.utils import normalize_search_text


class QdrantStore:
    def __init__(self, settings):
        self.settings = settings
        self.client = QdrantClient(url=settings.qdrant_url, timeout=3.0)

    def ping(self):
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def ensure_collection(self, vector_size):
        collections = self.client.get_collections().collections
        collection_names = []
        for item in collections:
            collection_names.append(item.name)

        if self.settings.qdrant_collection in collection_names:
            return

        self.client.create_collection(
            collection_name=self.settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert_chunks(self, chunks, vectors):
        if not chunks or not vectors:
            return False

        try:
            self.ensure_collection(len(vectors[0]))
            points = []

            for chunk, vector in zip(chunks, vectors):
                points.append(
                    PointStruct(
                        id=chunk["qdrant_point_id"],
                        vector=vector,
                        payload={
                            "chunk_id": chunk["id"],
                            "doc_id": chunk["doc_id"],
                            "doc_type": chunk.get("doc_type"),
                            "doc_number": chunk.get("doc_number"),
                            "supplier_name": chunk.get("supplier_name"),
                            "page_number": chunk["page_number"],
                            "section": chunk.get("section"),
                            "evidence_type": chunk.get("evidence_type", "text_chunk"),
                            "text": chunk["chunk_text"],
                            "search_text": chunk.get("search_text") or normalize_search_text(chunk["chunk_text"]),
                        },
                    )
                )

            self.client.upsert(collection_name=self.settings.qdrant_collection, points=points)
            return True
        except Exception:
            return False

    def delete_document_chunks(self, doc_id):
        try:
            self.client.delete(
                collection_name=self.settings.qdrant_collection,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
                wait=True,
            )
            return True
        except Exception:
            return False

    def search(self, query_vector, filters, allowed_doc_ids=None, limit=10):
        try:
            conditions = []

            if allowed_doc_ids:
                conditions.append(
                    FieldCondition(key="doc_id", match=MatchAny(any=allowed_doc_ids))
                )

            if filters.get("doc_type"):
                conditions.append(
                    FieldCondition(key="doc_type", match=MatchValue(value=filters["doc_type"]))
                )

            query_filter = None
            if conditions:
                query_filter = Filter(must=conditions)

            results = self.client.query_points(
                collection_name=self.settings.qdrant_collection,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
            )

            hits = []
            for item in results.points:
                hits.append(
                    {
                        "chunk_id": item.payload.get("chunk_id"),
                        "doc_id": item.payload.get("doc_id"),
                        "score": float(item.score),
                        "source": "vector",
                    }
                )
            return hits
        except Exception:
            return []
