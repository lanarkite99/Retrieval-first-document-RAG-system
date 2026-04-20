from eval.test_extraction import run_extraction_checks
from eval.test_retrieval import run_retrieval_checks
from eval.test_routing import run_routing_checks


def run_validation(runtime, ingest_path=None):
    runtime.bootstrap()

    results = {
        "extraction": run_extraction_checks(),
        "routing": run_routing_checks(),
        "retrieval": [],
    }

    if ingest_path:
        results["ingest"] = runtime.ingestion_service.ingest_path(ingest_path)

    try:
        results["retrieval"] = run_retrieval_checks(runtime)
    except Exception as exc:
        results["retrieval"] = [{"passed": False, "error": str(exc)}]

    return results


if __name__ == "__main__":
    from factory_rag.runtime import get_runtime

    runtime = get_runtime()
    print(run_validation(runtime))
