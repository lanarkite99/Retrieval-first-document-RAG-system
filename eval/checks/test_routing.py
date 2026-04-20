from factory_rag.router import QueryRouter
from eval.ground_truth import ROUTING_CASES


def run_routing_checks():
    router = QueryRouter()
    results = []

    for case in ROUTING_CASES:
        route = router.route(case["query"])
        results.append(
            {
                "query": case["query"],
                "expected": case["route"],
                "actual": route["route"],
                "passed": route["route"] == case["route"],
            }
        )

    return results
