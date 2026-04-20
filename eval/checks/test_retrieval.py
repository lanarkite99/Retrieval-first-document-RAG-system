from eval.ground_truth import RETRIEVAL_CASES


def run_retrieval_checks(runtime):
    results = []

    for case in RETRIEVAL_CASES:
        response = runtime.query_service.run(case["query"], limit=3, use_cache=False)
        hits = response["hits"]
        passed = False

        if hits:
            top_hit = hits[0]
            if case.get("expected_doc_number"):
                passed = top_hit.get("doc_number") == case["expected_doc_number"]
            elif case.get("expected_supplier_name"):
                passed = top_hit.get("supplier_name") == case["expected_supplier_name"]

        results.append(
            {
                "query": case["query"],
                "passed": passed,
                "top_hit": hits[0] if hits else None,
            }
        )

    return results
