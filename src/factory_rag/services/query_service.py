import copy
import hashlib
import re
import time

from factory_rag.utils import normalize_search_text


ROW_CONTEXT_STOPWORDS = {
    "amount",
    "code",
    "description",
    "gst",
    "hsn",
    "hr",
    "hrs",
    "item",
    "line",
    "material",
    "month",
    "nos",
    "part",
    "pcs",
    "price",
    "qty",
    "quantity",
    "rate",
    "sac",
    "tax",
    "taxable",
    "total",
    "unit",
    "uom",
}


class QueryService:
    def __init__(self, settings, db, router, retrieval_service, answer_service, cache, metrics):
        self.settings = settings
        self.db = db
        self.router = router
        self.retrieval_service = retrieval_service
        self.answer_service = answer_service
        self.cache = cache
        self.metrics = metrics

    def run(self, query, limit=5, use_cache=True):
        self.db.init_schema()
        started_at = time.perf_counter()
        cache_hit = False
        cache_key = self._cache_key(query, limit)

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                cache_hit = True
                cached["diagnostics"]["cache_hit"] = True
                self.metrics.record_query(cached["route"], 0.0, True)
                return cached

        plan = self.router.route(query)
        route_name = plan["route"]
        filters = plan["filters"]

        if route_name == "exact_match":
            hits = self._run_exact_candidate_search(query, plan, limit)
        else:
            hits = self._run_planned_search(query, plan, limit)

        answer = self.answer_service.build_answer(query, route_name, hits)
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        evidence = self._build_evidence(hits)

        response = {
            "query": query,
            "route": route_name,
            "filters": filters,
            "answer": answer,
            "evidence": evidence,
            "hits": hits,
            "diagnostics": {
                "cache_hit": cache_hit,
                "latency_ms": latency_ms,
                "result_count": len(hits),
                "answer_backend": self.answer_service.last_backend,
                "review_recommended": self._review_recommended(hits),
            },
        }

        self.db.log_query(query, route_name, filters, latency_ms, len(hits))
        self.metrics.record_query(route_name, latency_ms, cache_hit)

        if use_cache:
            self.cache.set(cache_key, response)

        return response

    def _run_exact_candidate_search(self, query, plan, limit):
        identifier = plan["identifier"]
        exact_hits = self.retrieval_service.exact_lookup(identifier)
        if not exact_hits:
            return []

        candidate_doc_ids = []
        for hit in exact_hits:
            doc_id = hit.get("doc_id")
            if doc_id and doc_id not in candidate_doc_ids:
                candidate_doc_ids.append(doc_id)

        search_plan = copy.deepcopy(plan)
        search_plan["filters"] = {}

        if plan.get("use_semantic"):
            search_plan["route"] = "hybrid"
        elif plan.get("text_terms"):
            search_plan["route"] = "mixed"
        else:
            search_plan["route"] = "lexical"

        search_hits = self._search_candidate_docs(query, search_plan, candidate_doc_ids, limit)
        merged_hits = self._merge_exact_hits(search_hits, exact_hits)
        reranked = self._rerank_hits(query, search_plan, merged_hits)
        return reranked[:limit]

    def _run_planned_search(self, query, plan, limit):
        route_name = plan["route"]
        filters = plan["filters"]

        if route_name == "lexical":
            hits = self.retrieval_service.search_evidence(
                query,
                filters,
                limit * 4,
                include_vector=False,
                vector_weight=0.0,
                keyword_weight=0.3,
                postgres_weight=0.7,
            )
        elif route_name == "mixed":
            hits = self.retrieval_service.search_evidence(
                query,
                filters,
                limit * 4,
                include_vector=True,
                vector_weight=0.2,
                keyword_weight=0.2,
                postgres_weight=0.6,
            )
        else:
            hits = self.retrieval_service.search_evidence(
                query,
                filters,
                limit * 4,
                include_vector=plan["use_semantic"],
                vector_weight=0.45,
                keyword_weight=0.2,
                postgres_weight=0.35,
            )

        if filters:
            structured_hits = self.retrieval_service.structured_search(filters, limit * 2)
            hits = self._merge_structured_hits(hits, structured_hits)

        reranked = self._rerank_hits(query, plan, hits)
        return reranked[:limit]

    def _search_candidate_docs(self, query, plan, candidate_doc_ids, limit):
        route_name = plan["route"]

        if route_name == "lexical":
            return self.retrieval_service.search_evidence(
                query,
                {},
                limit * 4,
                include_vector=False,
                vector_weight=0.0,
                keyword_weight=0.3,
                postgres_weight=0.7,
                allowed_doc_ids=candidate_doc_ids,
            )
        if route_name == "mixed":
            return self.retrieval_service.search_evidence(
                query,
                {},
                limit * 4,
                include_vector=True,
                vector_weight=0.2,
                keyword_weight=0.2,
                postgres_weight=0.6,
                allowed_doc_ids=candidate_doc_ids,
            )
        return self.retrieval_service.search_evidence(
            query,
            {},
            limit * 4,
            include_vector=plan.get("use_semantic", False),
            vector_weight=0.45,
            keyword_weight=0.2,
            postgres_weight=0.35,
            allowed_doc_ids=candidate_doc_ids,
        )

    def _merge_structured_hits(self, hits, structured_hits):
        merged = []
        seen = {}
        structured_doc_ids = set()

        for hit in structured_hits:
            structured_doc_ids.add(hit["doc_id"])
            boosted = self._boost_hit(hit, 0.18, "structured metadata filter")
            key = self._hit_key(boosted)
            seen[key] = boosted
            merged.append(boosted)

        for hit in hits:
            candidate = copy.deepcopy(hit)
            if candidate["doc_id"] in structured_doc_ids:
                candidate = self._boost_hit(candidate, 0.08, "structured metadata filter")

            key = self._hit_key(candidate)
            existing = seen.get(key)
            if existing is None:
                seen[key] = candidate
                merged.append(candidate)
                continue

            if candidate.get("score", 0) > existing.get("score", 0):
                existing["score"] = candidate["score"]
                existing["confidence"] = candidate["confidence"]
                existing["evidence_type"] = candidate.get("evidence_type")
            self._merge_lists(existing, candidate, "route_source")
            self._merge_lists(existing, candidate, "match_reasons")

        return merged

    def _merge_exact_hits(self, hits, exact_hits):
        merged = []
        seen = {}
        exact_doc_ids = set()

        for hit in exact_hits:
            exact_doc_ids.add(hit["doc_id"])
            key = self._hit_key(hit)
            seen[key] = copy.deepcopy(hit)
            merged.append(seen[key])

        for hit in hits:
            candidate = copy.deepcopy(hit)
            if candidate["doc_id"] in exact_doc_ids:
                candidate = self._boost_hit(candidate, 0.08, "exact identifier candidate")
                route_source = candidate.setdefault("route_source", [])
                if "exact" not in route_source:
                    route_source.append("exact")

            key = self._hit_key(candidate)
            existing = seen.get(key)
            if existing is None:
                seen[key] = candidate
                merged.append(candidate)
                continue

            if candidate.get("score", 0) > existing.get("score", 0):
                existing["score"] = candidate["score"]
                existing["confidence"] = candidate["confidence"]
                existing["evidence_type"] = candidate.get("evidence_type")
                existing["snippet"] = candidate.get("snippet")
                existing["citation"] = candidate.get("citation")
            self._merge_lists(existing, candidate, "route_source")
            self._merge_lists(existing, candidate, "match_reasons")

        return merged

    def _rerank_hits(self, query, plan, hits):
        reranked = []
        terms = plan.get("query_terms") or []
        numeric_terms = plan.get("numeric_terms") or []
        text_terms = plan.get("text_terms") or []
        row_query = plan.get("row_query")
        route_name = plan.get("route")

        for hit in hits:
            candidate = copy.deepcopy(hit)
            haystack = self._hit_haystack(candidate)
            evidence_type = candidate.get("evidence_type")
            numeric_match_count = self._term_match_count(haystack, numeric_terms)
            text_match_count = self._term_match_count(haystack, text_terms)
            overlap_boost = self._term_overlap_boost(numeric_match_count, text_match_count)
            boost = overlap_boost

            if route_name == "lexical":
                boost += numeric_match_count * 0.22
                boost += min(0.18, text_match_count * 0.06)
            elif route_name == "mixed":
                boost += numeric_match_count * 0.18
                boost += min(0.16, text_match_count * 0.05)
            else:
                boost += numeric_match_count * 0.08
                boost += min(0.12, text_match_count * 0.04)

            if row_query:
                if evidence_type == "table_row":
                    boost += 0.24
                    boost += self._row_context_boost(candidate)
                elif evidence_type == "line_chunk":
                    boost += 0.16
                elif evidence_type == "header_field":
                    boost -= 0.12
                else:
                    boost -= 0.08

                if numeric_match_count:
                    boost += 0.18

            if evidence_type == "line_chunk" and text_match_count:
                boost += min(0.18, text_match_count * 0.06)

            if evidence_type == "header_field" and text_match_count >= 2 and not row_query:
                boost += 0.08

            if boost:
                candidate["score"] = round(candidate.get("score", 0) + boost, 4)
                candidate["confidence"] = self._confidence(candidate["score"], candidate.get("route_source") or [])
                reasons = candidate.setdefault("match_reasons", [])
                if overlap_boost and "exact term overlap" not in reasons:
                    reasons.append("exact term overlap")
                if numeric_match_count and "exact numeric match" not in reasons:
                    reasons.append("exact numeric match")
                if row_query and evidence_type == "table_row" and "row-level evidence" not in reasons:
                    reasons.append("row-level evidence")
            reranked.append(candidate)

        if row_query:
            reranked.sort(
                key=lambda item: (self._row_sort_key(item, row_query), item.get("score", 0), self._source_sort_key(item)),
                reverse=True,
            )
        else:
            reranked.sort(
                key=lambda item: (item.get("score", 0), self._source_sort_key(item)),
                reverse=True,
            )
        return reranked

    def _hit_haystack(self, hit):
        parts = []
        parts.append(hit.get("snippet") or "")
        parts.append(hit.get("doc_number") or "")
        parts.append(hit.get("supplier_name") or "")
        parts.append(hit.get("evidence_type") or "")

        citation = hit.get("citation") or {}
        parts.append(citation.get("file_name") or "")
        parts.append(citation.get("section") or "")

        canonical = hit.get("canonical_fields") or {}
        for value in canonical.values():
            if value is not None:
                parts.append(str(value))

        return normalize_search_text(" ".join(parts)).lower()

    def _term_match_count(self, haystack, terms):
        count = 0
        for term in terms:
            if term in haystack:
                count += 1
        return count

    def _term_overlap_boost(self, numeric_match_count, text_match_count):
        boost = numeric_match_count * 0.14 + text_match_count * 0.05
        return round(boost, 4)

    def _row_context_boost(self, hit):
        snippet = normalize_search_text(hit.get("snippet") or "").lower()
        first_number = re.search(r"\d", snippet)
        prefix = snippet
        if first_number:
            prefix = snippet[: first_number.start()]

        words = re.findall(r"[a-z]+", prefix)
        meaningful_words = []
        for word in words:
            if word not in ROW_CONTEXT_STOPWORDS:
                meaningful_words.append(word)

        if len(meaningful_words) >= 2:
            return 0.28
        if len(meaningful_words) == 1:
            return 0.08
        if words:
            return -0.16
        return -0.2

    def _row_sort_key(self, hit, row_query):
        if not row_query:
            return 0.0
        if hit.get("evidence_type") != "table_row":
            return -1.0
        return self._row_context_boost(hit)

    def _source_sort_key(self, hit):
        route_source = hit.get("route_source") or []
        score = 0.0
        if "postgres_keyword" in route_source:
            score += 0.4
        if "keyword" in route_source:
            score += 0.2
        if "structured" in route_source:
            score += 0.1
        if "vector" in route_source:
            score += 0.05
        return score

    def _boost_hit(self, hit, boost, reason):
        boosted = copy.deepcopy(hit)
        score = round(boosted.get("score", 0) + boost, 4)
        boosted["score"] = score
        boosted["confidence"] = self._confidence(score, boosted.get("route_source") or [])
        match_reasons = boosted.setdefault("match_reasons", [])
        if reason not in match_reasons:
            match_reasons.append(reason)
        route_source = boosted.setdefault("route_source", [])
        if "structured" not in route_source:
            route_source.append("structured")
        return boosted

    def _merge_lists(self, target, source, key):
        target_items = target.setdefault(key, [])
        for item in source.get(key, []):
            if item not in target_items:
                target_items.append(item)

    def _hit_key(self, hit):
        citation = hit.get("citation") or {}
        return (
            hit.get("doc_id"),
            citation.get("page"),
            citation.get("section"),
            hit.get("evidence_type"),
            hit.get("snippet"),
        )

    def _confidence(self, score, route_source):
        if "exact" in route_source:
            return {"score": 1.0, "label": "high"}
        if score >= 0.9:
            return {"score": round(score, 4), "label": "high"}
        if score >= 0.55:
            return {"score": round(score, 4), "label": "medium"}
        return {"score": round(score, 4), "label": "low"}

    def _build_evidence(self, hits):
        evidence = []
        for hit in hits[:3]:
            evidence.append(
                {
                    "doc_number": hit.get("doc_number"),
                    "supplier_name": hit.get("supplier_name"),
                    "confidence": hit.get("confidence"),
                    "citation": hit.get("citation"),
                    "snippet": hit.get("snippet"),
                    "match_reasons": hit.get("match_reasons"),
                    "evidence_type": hit.get("evidence_type"),
                }
            )
        return evidence

    def _review_recommended(self, hits):
        if not hits:
            return False
        top_hit = hits[0]
        confidence = top_hit.get("confidence") or {}
        return confidence.get("label") == "low"

    def _cache_key(self, query, limit):
        key = f"{query.strip().lower()}::{limit}"
        return "query:" + hashlib.sha256(key.encode("utf-8")).hexdigest()
