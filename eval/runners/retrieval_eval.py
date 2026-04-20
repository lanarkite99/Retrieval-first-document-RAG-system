import json
from collections import defaultdict


TOP_K_VALUES = [1, 3, 5]


def normalize(text):
    if text is None:
        return ""
    return str(text).strip().lower()


def file_match(hit, expected_file):
    citation = hit.get("citation") or {}
    actual = citation.get("file_name") or hit.get("source_filename")
    return normalize(actual) == normalize(expected_file)


def doc_match(hit, expected_doc_truth):
    if not expected_doc_truth:
        return False
    return normalize(hit.get("doc_number")) == normalize(expected_doc_truth)


def page_match(hit, expected_page):
    if expected_page is None:
        return True
    citation = hit.get("citation") or {}
    actual_page = citation.get("page") or hit.get("page_number")
    return actual_page == expected_page


def snippet_match(hit, expected_snippets):
    if not expected_snippets:
        return True

    snippet = normalize(hit.get("snippet"))
    if not snippet:
        return False

    for expected in expected_snippets:
        if normalize(expected) not in snippet:
            return False
    return True


def hit_matches(hit, case):
    expected_file = case.get("expected_source_filename")
    expected_doc_truth = case.get("expected_doc_truth")
    expected_page = case.get("expected_page")

    file_ok = True
    if expected_file:
        file_ok = file_match(hit, expected_file)

    doc_ok = True
    if expected_doc_truth:
        doc_ok = doc_match(hit, expected_doc_truth)

    return file_ok and doc_ok and page_match(hit, expected_page)


def reciprocal_rank(hits, case):
    for index, hit in enumerate(hits, start=1):
        if hit_matches(hit, case):
            return 1.0 / index
    return 0.0


def recall_at_k(hits, case, k):
    for hit in hits[:k]:
        if hit_matches(hit, case):
            return True
    return False


def snippet_at_k(hits, case, k):
    expected_snippets = case.get("expected_snippet_contains", [])
    if not expected_snippets:
        return True

    for hit in hits[:k]:
        if hit_matches(hit, case) and snippet_match(hit, expected_snippets):
            return True
    return False


def _safe_div(value, total):
    if total <= 0:
        return 0.0
    return round(value / total, 4)


def evaluate_retrieval(golden_path, query_service, limit=5):
    with open(golden_path, "r", encoding="utf-8") as handle:
        golden_cases = json.load(handle)

    overall = {
        "total": 0,
        "recall": {k: 0 for k in TOP_K_VALUES},
        "snippet": {k: 0 for k in TOP_K_VALUES},
        "mrr": 0.0,
    }
    per_type = defaultdict(
        lambda: {
            "total": 0,
            "recall": {k: 0 for k in TOP_K_VALUES},
            "snippet": {k: 0 for k in TOP_K_VALUES},
            "mrr": 0.0,
        }
    )
    queries = []

    for case in golden_cases:
        response = query_service.run(case["query"], limit=limit, use_cache=False)
        hits = response.get("hits", [])
        query_type = case.get("query_type", "unknown")

        overall["total"] += 1
        per_type[query_type]["total"] += 1

        query_result = {
            "name": case.get("name"),
            "query": case["query"],
            "query_type": query_type,
            "route": response.get("route"),
            "passed": False,
            "top_hit": hits[0] if hits else None,
            "checks": [],
        }

        for k in TOP_K_VALUES:
            recall_hit = recall_at_k(hits, case, k)
            snippet_hit = snippet_at_k(hits, case, k)
            if recall_hit:
                overall["recall"][k] += 1
                per_type[query_type]["recall"][k] += 1
            if snippet_hit:
                overall["snippet"][k] += 1
                per_type[query_type]["snippet"][k] += 1

        rr = reciprocal_rank(hits, case)
        overall["mrr"] += rr
        per_type[query_type]["mrr"] += rr

        top1_ok = recall_at_k(hits, case, 1)
        snippet1_ok = snippet_at_k(hits, case, 1)
        query_result["passed"] = top1_ok and snippet1_ok

        query_result["checks"].append(
            {
                "field": "recall@1",
                "passed": top1_ok,
                "expected": {
                    "source_filename": case.get("expected_source_filename"),
                    "doc_truth": case.get("expected_doc_truth"),
                    "page": case.get("expected_page"),
                },
                "actual": hits[0] if hits else None,
            }
        )
        query_result["checks"].append(
            {
                "field": "snippet@1",
                "passed": snippet1_ok,
                "expected": case.get("expected_snippet_contains", []),
                "actual": (hits[0] or {}).get("snippet") if hits else None,
            }
        )

        queries.append(query_result)

    summary = {
        "dataset": golden_path,
        "queries": overall["total"],
        "recall_at_1": _safe_div(overall["recall"][1], overall["total"]),
        "recall_at_3": _safe_div(overall["recall"][3], overall["total"]),
        "recall_at_5": _safe_div(overall["recall"][5], overall["total"]),
        "snippet_at_1": _safe_div(overall["snippet"][1], overall["total"]),
        "snippet_at_3": _safe_div(overall["snippet"][3], overall["total"]),
        "snippet_at_5": _safe_div(overall["snippet"][5], overall["total"]),
        "mrr": _safe_div(overall["mrr"], overall["total"]),
        "query_types": {},
    }

    for query_type, stats in per_type.items():
        total = stats["total"]
        summary["query_types"][query_type] = {
            "queries": total,
            "recall_at_1": _safe_div(stats["recall"][1], total),
            "recall_at_3": _safe_div(stats["recall"][3], total),
            "recall_at_5": _safe_div(stats["recall"][5], total),
            "snippet_at_1": _safe_div(stats["snippet"][1], total),
            "snippet_at_3": _safe_div(stats["snippet"][3], total),
            "snippet_at_5": _safe_div(stats["snippet"][5], total),
            "mrr": _safe_div(stats["mrr"], total),
        }

    return {
        "summary": summary,
        "queries": queries,
    }
