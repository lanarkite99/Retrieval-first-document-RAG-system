from opensearchpy import OpenSearch, helpers

from factory_rag.utils import build_search_text, extract_search_terms, normalize_search_text


class OpenSearchStore:
    def __init__(self, settings):
        self.settings = settings
        self.client = OpenSearch(
            hosts=[settings.opensearch_url],
            http_compress=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=10,
            max_retries=2,
            retry_on_timeout=True,
        )

    def ping(self):
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def ensure_index(self):
        if self.client.indices.exists(index=self.settings.opensearch_index):
            return

        mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "doc_type": {"type": "keyword"},
                    "doc_number": {"type": "keyword"},
                    "supplier_name": {"type": "keyword"},
                    "page_number": {"type": "integer"},
                    "section": {"type": "text"},
                    "evidence_type": {"type": "keyword"},
                    "chunk_text": {"type": "text"},
                    "search_text": {"type": "text"},
                }
            },
        }

        self.client.indices.create(index=self.settings.opensearch_index, body=mapping)

    def index_chunks(self, chunks):
        if not chunks:
            return False

        try:
            self.ensure_index()
            actions = []

            for chunk in chunks:
                actions.append(
                    {
                        "_index": self.settings.opensearch_index,
                        "_id": chunk["id"],
                        "_source": {
                            "chunk_id": chunk["id"],
                            "doc_id": chunk["doc_id"],
                            "doc_type": chunk.get("doc_type"),
                            "doc_number": chunk.get("doc_number"),
                            "supplier_name": chunk.get("supplier_name"),
                            "page_number": chunk["page_number"],
                            "section": chunk.get("section"),
                            "evidence_type": chunk.get("evidence_type", "text_chunk"),
                            "chunk_text": chunk["chunk_text"],
                            "search_text": chunk.get("search_text") or build_search_text(chunk["chunk_text"]),
                        },
                    }
                )

            helpers.bulk(self.client, actions, refresh=True, request_timeout=10)
            return True
        except Exception:
            return False

    def delete_document_chunks(self, doc_id):
        try:
            self.ensure_index()
            self.client.delete_by_query(
                index=self.settings.opensearch_index,
                body={"query": {"term": {"doc_id": doc_id}}},
                refresh=True,
                conflicts="proceed",
            )
            return True
        except Exception:
            return False

    def search(self, query, filters, allowed_doc_ids=None, limit=10):
        try:
            terms = extract_search_terms(query)
            query_text = " ".join(terms)
            if not query_text:
                query_text = normalize_search_text(query)

            must = [
                {
                    "multi_match": {
                        "query": query_text,
                        "fields": ["search_text^4", "chunk_text^3", "section^1.5", "doc_number^2", "supplier_name^2"],
                    }
                }
            ]
            filter_clauses = []

            if allowed_doc_ids:
                filter_clauses.append({"terms": {"doc_id": allowed_doc_ids}})

            if filters.get("doc_type"):
                filter_clauses.append({"term": {"doc_type": filters["doc_type"]}})

            body = {"size": limit, "query": {"bool": {"must": must, "filter": filter_clauses}}}
            response = self.client.search(index=self.settings.opensearch_index, body=body, request_timeout=10)

            hits = []
            for item in response["hits"]["hits"]:
                source = item["_source"]
                hits.append(
                    {
                        "chunk_id": source["chunk_id"],
                        "doc_id": source["doc_id"],
                        "score": float(item["_score"]),
                        "source": "keyword",
                    }
                )
            return hits
        except Exception:
            return []
