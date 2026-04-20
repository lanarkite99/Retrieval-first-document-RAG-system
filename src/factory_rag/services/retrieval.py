from factory_rag.utils import short_snippet


class RetrievalService:
    def __init__(self, db, embedder, qdrant_store, opensearch_store):
        self.db = db
        self.embedder = embedder
        self.qdrant_store = qdrant_store
        self.opensearch_store = opensearch_store

    def exact_lookup(self, identifier):
        documents = self.db.exact_lookup_candidates(identifier, limit=20)
        if not documents:
            return []

        doc_ids = []
        for document in documents:
            doc_ids.append(document["id"])
        chunks = self.db.get_first_chunks(doc_ids)
        return self._build_document_hits(chunks, "exact")

    def structured_search(self, filters, limit):
        documents = self.db.search_documents(filters, limit)
        doc_ids = []
        for document in documents:
            doc_ids.append(document["id"])
        chunks = self.db.get_first_chunks(doc_ids)
        return self._build_document_hits(chunks, "structured")

    def search_evidence(
        self,
        query,
        filters,
        limit,
        include_vector,
        vector_weight,
        keyword_weight,
        postgres_weight,
        allowed_doc_ids=None,
    ):
        if allowed_doc_ids is None:
            allowed_doc_ids = self._allowed_doc_ids(filters)
        if allowed_doc_ids == []:
            return []

        raw_hits = []

        if keyword_weight > 0:
            keyword_hits = self.opensearch_store.search(
                query,
                filters,
                allowed_doc_ids=allowed_doc_ids,
                limit=limit * 2,
            )
            raw_hits.append((keyword_hits, keyword_weight))

        if postgres_weight > 0:
            postgres_hits = self.db.keyword_search_chunks(
                query,
                allowed_doc_ids=allowed_doc_ids,
                limit=limit * 2,
            )
            for hit in postgres_hits:
                hit["source"] = "postgres_keyword"
            raw_hits.append((postgres_hits, postgres_weight))

        if include_vector and vector_weight > 0:
            query_vector = self.embedder.embed_query(query)
            vector_hits = self.qdrant_store.search(
                query_vector,
                filters,
                allowed_doc_ids=allowed_doc_ids,
                limit=limit * 2,
            )
            raw_hits.append((vector_hits, vector_weight))

        combined = self._fuse_hits(raw_hits)
        if not combined and filters:
            return self.structured_search(filters, limit)

        return self._build_ranked_results(combined, limit)

    def _allowed_doc_ids(self, filters):
        if not filters:
            return None

        documents = self.db.search_documents(filters, limit=200)
        if not documents:
            return []

        doc_ids = []
        for document in documents:
            doc_ids.append(document["id"])
        return doc_ids

    def _fuse_hits(self, weighted_hit_lists):
        scores = {}

        for hits, weight in weighted_hit_lists:
            for hit in self._normalize_hits(hits, weight):
                self._add_score(scores, hit)

        items = list(scores.values())
        items.sort(key=lambda item: item["score"], reverse=True)
        return items

    def _normalize_hits(self, hits, weight):
        if not hits:
            return []

        top_score = hits[0]["score"]
        if top_score == 0:
            top_score = 1.0

        normalized = []
        for hit in hits:
            normalized.append(
                {
                    "chunk_id": hit["chunk_id"],
                    "doc_id": hit["doc_id"],
                    "score": (float(hit["score"]) / float(top_score)) * weight,
                    "source": hit["source"],
                }
            )
        return normalized

    def _add_score(self, scores, hit):
        key = hit["chunk_id"]
        if key not in scores:
            scores[key] = {
                "chunk_id": hit["chunk_id"],
                "doc_id": hit["doc_id"],
                "score": 0.0,
                "sources": [],
            }

        scores[key]["score"] += hit["score"]
        if hit["source"] not in scores[key]["sources"]:
            scores[key]["sources"].append(hit["source"])

    def _build_ranked_results(self, combined, limit):
        chunk_ids = []
        for item in combined:
            chunk_ids.append(item["chunk_id"])

        chunks = self.db.get_chunks_by_ids(chunk_ids)
        chunk_map = {}
        for chunk in chunks:
            chunk_map[chunk["chunk_id"]] = chunk

        results = []
        seen = set()

        for item in combined:
            chunk = chunk_map.get(item["chunk_id"])
            if not chunk:
                continue

            result = self._chunk_to_result(chunk, round(item["score"], 4), item["sources"])
            key = self._result_key(result)
            if key in seen:
                continue

            seen.add(key)
            results.append(result)
            if len(results) >= limit:
                break

        return results

    def _build_document_hits(self, chunks, route_source):
        results = []
        seen = set()

        for chunk in chunks:
            result = self._chunk_to_result(chunk, 1.0, [route_source])
            key = self._result_key(result)
            if key in seen:
                continue

            seen.add(key)
            results.append(result)

        return results

    def _chunk_to_result(self, chunk, score, route_source):
        metadata = chunk.get("metadata") or {}
        extra_fields = metadata.get("extra_fields") or {}

        return {
            "doc_id": chunk["doc_id"],
            "chunk_id": chunk["chunk_id"],
            "score": score,
            "confidence": self._confidence(score, route_source),
            "match_reasons": self._match_reasons(route_source),
            "route_source": route_source,
            "evidence_type": chunk.get("evidence_type", "text_chunk"),
            "doc_type": chunk["doc_type"],
            "doc_number": chunk["doc_number"],
            "supplier_name": chunk.get("supplier_name"),
            "page_number": chunk["page_number"],
            "source_filename": chunk["source_filename"],
            "storage_path": chunk["storage_path"],
            "doc_date": chunk["doc_date"],
            "amount": chunk["amount"],
            "currency": chunk["currency"],
            "citation": {
                "file_name": chunk["source_filename"],
                "storage_path": chunk["storage_path"],
                "page": chunk["page_number"],
                "section": chunk.get("section"),
            },
            "snippet": short_snippet(chunk["chunk_text"]),
            "canonical_fields": {
                "doc_type": chunk["doc_type"],
                "doc_number": chunk["doc_number"],
                "supplier_name": chunk.get("supplier_name"),
                "doc_date": chunk["doc_date"],
                "amount": chunk["amount"],
                "currency": chunk["currency"],
                "buyer_name": metadata.get("buyer_name"),
                "po_number": metadata.get("po_number"),
                "part_number": metadata.get("part_number"),
                "revision": metadata.get("revision"),
            },
            "flex_fields": extra_fields,
        }

    def _confidence(self, score, route_source):
        if "exact" in route_source:
            return {"score": 1.0, "label": "high"}
        if score >= 0.9:
            return {"score": round(score, 4), "label": "high"}
        if score >= 0.55:
            return {"score": round(score, 4), "label": "medium"}
        return {"score": round(score, 4), "label": "low"}

    def _match_reasons(self, route_source):
        reasons = []
        for source in route_source:
            if source == "exact":
                reasons.append("exact identifier match")
            elif source == "structured":
                reasons.append("structured metadata filter")
            elif source == "vector":
                reasons.append("semantic similarity")
            elif source == "keyword":
                reasons.append("keyword match")
            elif source == "postgres_keyword":
                reasons.append("database text match")
        return reasons

    def _result_key(self, result):
        citation = result.get("citation") or {}
        return (
            citation.get("storage_path"),
            citation.get("page"),
            citation.get("section"),
            result.get("evidence_type"),
            result.get("snippet"),
        )
