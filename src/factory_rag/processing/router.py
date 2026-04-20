import re

from factory_rag.metadata import extract_query_filters
from factory_rag.utils import extract_search_terms


ROW_QUERY_WORDS = {
    "item",
    "line",
    "line item",
    "rate",
    "qty",
    "quantity",
    "price",
    "part",
    "material",
    "hsn",
    "code",
}

TOTAL_QUERY_WORDS = {
    "amount",
    "amount payable",
    "final amount",
    "grand total",
    "invoice total",
    "net amount",
    "subtotal",
    "total",
}


class QueryRouter:
    def route(self, query):
        query = query or ""
        lowered = query.lower()
        filters = extract_query_filters(query)
        identifier = filters.get("doc_number")
        terms = extract_search_terms(query)
        numeric_terms = []
        text_terms = []

        for term in terms:
            if re.search(r"\d", term):
                numeric_terms.append(term)
            else:
                text_terms.append(term)

        row_query = self._contains_any(lowered, ROW_QUERY_WORDS)
        total_query = self._contains_any(lowered, TOTAL_QUERY_WORDS)
        exact_identifier = bool(identifier)
        gstin_query = bool(filters.get("gstin"))
        specific_filter = any(
            filters.get(key) is not None
            for key in ["supplier_name", "month", "year", "amount", "gstin"]
        )
        numeric_heavy = bool(numeric_terms) and (row_query or total_query or gstin_query or len(numeric_terms) >= 2)
        use_semantic = len(text_terms) >= 2 and not numeric_heavy and not specific_filter and not row_query

        route_name = "lexical"
        if exact_identifier and len(query.split()) <= 8:
            route_name = "exact_match"
            use_semantic = False
        elif row_query:
            route_name = "lexical"
            use_semantic = False
        elif numeric_heavy:
            route_name = "lexical"
            use_semantic = False
        elif specific_filter:
            route_name = "lexical"
            use_semantic = False
        elif filters and len(text_terms) <= 2:
            route_name = "lexical"
            use_semantic = False
        elif use_semantic and numeric_terms:
            route_name = "mixed"
        elif use_semantic:
            route_name = "hybrid"

        return {
            "route": route_name,
            "filters": filters,
            "identifier": identifier,
            "query_terms": terms,
            "numeric_terms": numeric_terms,
            "text_terms": text_terms,
            "row_query": row_query,
            "total_query": total_query,
            "use_semantic": use_semantic,
        }

    def _contains_any(self, lowered_query, phrases):
        for phrase in phrases:
            if phrase in lowered_query:
                return True
        return False
