import re

from factory_rag.utils import extract_search_terms, normalize_search_text


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


class AnswerService:
    def __init__(self, settings, gemini_client):
        self.settings = settings
        self.gemini_client = gemini_client
        self.last_backend = "none"

    def build_answer(self, query, route_name, hits):
        self.last_backend = "none"

        if not hits:
            return None

        if route_name == "exact_match":
            self.last_backend = "deterministic"
            return self._build_exact_answer(hits[0])

        row_answer = self._build_row_answer(query, hits)
        if row_answer:
            self.last_backend = "extractive_row"
            return row_answer

        if self.settings.enable_summary and self.settings.llm_backend == "gemini":
            answer = self.gemini_client.generate_answer(query, hits[: self.settings.answer_context_hits])
            if answer:
                self.last_backend = self.settings.llm_model
                return answer

        answer = self._build_extractive_answer(hits)
        if answer:
            self.last_backend = "extractive"
        return answer

    def _build_exact_answer(self, hit):
        citation = hit.get("citation") or {}
        parts = []
        parts.append(f"Found {hit.get('doc_number') or citation.get('file_name')}.")

        if citation.get("file_name"):
            parts.append(f"File: {citation['file_name']}.")
        if citation.get("storage_path"):
            parts.append(f"Location: {citation['storage_path']}.")
        if hit.get("supplier_name"):
            parts.append(f"Supplier: {hit['supplier_name']}.")
        if hit.get("amount") is not None and hit.get("currency"):
            parts.append(f"Amount: {hit['amount']} {hit['currency']}.")
        if hit.get("doc_date"):
            parts.append(f"Date: {hit['doc_date']}.")
        if citation.get("page"):
            parts.append(f"Evidence: page {citation['page']}.")

        return " ".join(parts)

    def _build_row_answer(self, query, hits):
        lowered = (query or "").lower()
        row_words = ["item", "line", "rate", "qty", "quantity", "price", "part", "material", "code"]
        if not any(word in lowered for word in row_words):
            return None

        terms = extract_search_terms(query)
        numeric_terms = []
        text_terms = []

        for term in terms:
            if re.search(r"\d", term):
                numeric_terms.append(term)
            else:
                text_terms.append(term)

        best_hit = None
        best_rank = None

        for hit in hits:
            if hit.get("evidence_type") != "table_row":
                continue

            snippet = hit.get("snippet") or ""
            normalized_snippet = normalize_search_text(snippet).lower()
            score = hit.get("score", 0)
            numeric_match = 1 if self._contains_any_term(normalized_snippet, numeric_terms) else 0
            text_match_count = self._term_match_count(normalized_snippet, text_terms)
            score += numeric_match * 0.4
            score += min(0.2, text_match_count * 0.08)
            score += self._row_context_boost(normalized_snippet)
            specificity = self._row_specificity(normalized_snippet)
            rank = (text_match_count, numeric_match, specificity, score)

            if best_rank is None or rank > best_rank:
                best_rank = rank
                best_hit = hit

        if not best_hit:
            return None

        citation = best_hit.get("citation") or {}
        label = best_hit.get("doc_number") or citation.get("file_name")
        page = citation.get("page") or "?"
        snippet = best_hit.get("snippet") or ""

        material_code = self._extract_labeled_value(snippet, "Material Code")
        if not material_code and "material code" in lowered:
            material_code = self._extract_material_code(snippet)
        if material_code and "material code" in lowered:
            return f"The material code is {material_code} in {label}, page {page}."

        return f"Best matching row in {label}, page {page}: {snippet}"

    def _build_extractive_answer(self, hits):
        top_hits = hits[:3]
        lines = []

        for hit in top_hits:
            citation = hit.get("citation") or {}
            label = hit.get("doc_number") or citation.get("file_name")
            supplier = hit.get("supplier_name") or "unknown supplier"
            page = citation.get("page") or "?"
            lines.append(f"{label} from {supplier}, page {page}: {hit.get('snippet') or ''}")

        if not lines:
            return None

        return "\n".join(lines)

    def _contains_any_term(self, haystack, terms):
        for term in terms:
            if term in haystack:
                return True
        return False

    def _term_match_count(self, haystack, terms):
        count = 0
        for term in terms:
            if term in haystack:
                count += 1
        return count

    def _row_context_boost(self, snippet):
        first_number = re.search(r"\d", snippet)
        prefix = snippet
        if first_number:
            prefix = snippet[: first_number.start()]

        words = re.findall(r"[a-z]+", prefix.lower())
        meaningful_words = []
        for word in words:
            if word not in ROW_CONTEXT_STOPWORDS:
                meaningful_words.append(word)

        if len(meaningful_words) >= 2:
            return 0.3
        if len(meaningful_words) == 1:
            return 0.08
        if words:
            return -0.18
        return -0.22

    def _extract_labeled_value(self, snippet, label):
        pattern = rf"{re.escape(label)}:\s*([^|]+)"
        match = re.search(pattern, snippet)
        if not match:
            return None
        return match.group(1).strip()


    def _extract_material_code(self, snippet):
        match = re.search(r"^\s*\d+\s+([A-Z]{1,5}-\d{2,}[A-Z0-9-]*)\b", snippet)
        if match:
            return match.group(1).strip()
        match = re.search(r"\b([A-Z]{1,5}-\d{2,}[A-Z0-9-]*)\b", snippet)
        if match:
            return match.group(1).strip()
        return None

    def _row_specificity(self, snippet):
        score = 0.0
        if "material code description" in snippet:
            score -= 1.0
        if "process route" in snippet:
            score -= 0.6
        if len(re.findall(r"\b\d+\s+[A-Z]{1,5}-\d{2,}", snippet)) > 1:
            score -= 0.8
        score -= len(snippet) / 1000.0
        return score
