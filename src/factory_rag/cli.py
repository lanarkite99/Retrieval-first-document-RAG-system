import argparse
import json

from factory_rag.runtime import get_runtime
from eval.evaluate import evaluate_dataset
from eval.retrieval_eval import evaluate_retrieval
from eval.runall import run_validation


def _print_json(value):
    print(json.dumps(value, indent=2, default=str))


def _print_ingest(results):
    print(f"Processed {len(results)} file(s)")
    print()

    for index, item in enumerate(results, start=1):
        print(f"{index}. {item.get('source_filename') or item.get('doc_number') or item.get('doc_id')}")
        print(f"   status: {item.get('status')}")
        if item.get('doc_number'):
            print(f"   doc number: {item['doc_number']}")
        if item.get('doc_type'):
            print(f"   doc type: {item['doc_type']}")
        if item.get('chunks') is not None:
            print(f"   chunks: {item['chunks']}")
        if item.get('index_status'):
            vector_status = item['index_status'].get('vector')
            keyword_status = item['index_status'].get('keyword')
            print(f"   indexes: vector={vector_status}, keyword={keyword_status}")
        if item.get('error'):
            print(f"   error: {item['error']}")
        print()


def _print_query(response):
    print(f"Query: {response['query']}")
    print(f"Route: {response['route']}")
    print(f"Results: {response['diagnostics']['result_count']}")
    print(f"Latency: {response['diagnostics']['latency_ms']} ms")
    print(f"Cache hit: {response['diagnostics']['cache_hit']}")
    print(f"Answer backend: {response['diagnostics'].get('answer_backend')}")
    print(f"Review recommended: {response['diagnostics'].get('review_recommended')}")
    print()

    if response.get('answer'):
        print("Answer")
        print(response['answer'])
        print()

    evidence = response.get('evidence', [])
    if evidence:
        print("Top Evidence")
        print()
        for index, item in enumerate(evidence, start=1):
            citation = item.get('citation') or {}
            confidence = item.get('confidence') or {}
            print(f"{index}. {item.get('doc_number') or citation.get('file_name')}")
            print(f"   file: {citation.get('file_name')}")
            print(f"   location: {citation.get('storage_path')}")
            print(f"   page: {citation.get('page')}  section: {citation.get('section')}")
            print(f"   supplier: {item.get('supplier_name')}")
            print(f"   evidence type: {item.get('evidence_type')}")
            print(f"   confidence: {confidence.get('label')} ({confidence.get('score')})")
            print(f"   why matched: {', '.join(item.get('match_reasons', []))}")
            print(f"   snippet: {item.get('snippet')}")
            print()

    hits = response.get('hits', [])
    if not hits:
        print("No matching documents found.")
        return

    print("Hits")
    print()
    for index, hit in enumerate(hits, start=1):
        citation = hit.get('citation') or {}
        confidence = hit.get('confidence') or {}
        print(f"{index}. {hit.get('doc_number') or citation.get('file_name')}")
        print(f"   file: {citation.get('file_name')}")
        print(f"   location: {citation.get('storage_path')}")
        print(f"   supplier: {hit.get('supplier_name')}")
        print(f"   amount: {hit.get('amount')} {hit.get('currency')}")
        print(f"   date: {hit.get('doc_date')}")
        print(f"   page: {citation.get('page')}  section: {citation.get('section')}")
        print(f"   evidence type: {hit.get('evidence_type')}")
        print(f"   confidence: {confidence.get('label')} ({confidence.get('score')})")
        print(f"   why matched: {', '.join(hit.get('match_reasons', []))}")
        print(f"   snippet: {hit.get('snippet')}")
        print()


def _print_find(response):
    hits = response.get("hits", [])
    print(f"Find: {response['query']}")
    print(f"Matches: {response['diagnostics']['result_count']}")
    print()

    if not hits:
        print("No matching documents found.")
        return

    top_hit = hits[0]
    citation = top_hit.get("citation") or {}
    print("Best Match")
    print(f"  document: {top_hit.get('doc_number') or citation.get('file_name')}")
    print(f"  file: {citation.get('file_name')}")
    print(f"  location: {citation.get('storage_path')}")
    print(f"  page: {citation.get('page')}")
    if top_hit.get("supplier_name"):
        print(f"  supplier: {top_hit.get('supplier_name')}")
    if top_hit.get("doc_date"):
        print(f"  date: {top_hit.get('doc_date')}")
    if top_hit.get("amount") is not None and top_hit.get("currency"):
        print(f"  amount: {top_hit.get('amount')} {top_hit.get('currency')}")
    print(f"  snippet: {top_hit.get('snippet')}")
    print()

    if len(hits) == 1:
        return

    print("More Matches")
    print()
    for index, hit in enumerate(hits[1:], start=2):
        citation = hit.get("citation") or {}
        print(f"{index}. {hit.get('doc_number') or citation.get('file_name')}")
        print(f"   file: {citation.get('file_name')}")
        print(f"   location: {citation.get('storage_path')}")
        print(f"   page: {citation.get('page')}")
        if hit.get("supplier_name"):
            print(f"   supplier: {hit.get('supplier_name')}")
        print(f"   snippet: {hit.get('snippet')}")
        print()


def _print_validation(results):
    print("Validation Summary")
    print()
    for area in ["extraction", "routing", "retrieval"]:
        items = results.get(area, [])
        passed = sum(1 for item in items if item.get('passed'))
        total = len(items)
        print(f"{area}: {passed}/{total} passed")
    if results.get('ingest'):
        print(f"ingest runs: {len(results['ingest'])}")
    print()
    _print_json(results)


def _print_retrieval_evaluation(results):
    summary = results["summary"]
    print("Retrieval Evaluation Summary")
    print()
    print(f"Dataset: {summary['dataset']}")
    print(f"Queries: {summary['queries']}")
    print(f"Recall@1: {summary['recall_at_1']}")
    print(f"Recall@3: {summary['recall_at_3']}")
    print(f"Recall@5: {summary['recall_at_5']}")
    print(f"Snippet@1: {summary['snippet_at_1']}")
    print(f"Snippet@3: {summary['snippet_at_3']}")
    print(f"Snippet@5: {summary['snippet_at_5']}")
    print(f"MRR: {summary['mrr']}")
    print()
    print("By Query Type")
    for query_type, item in summary["query_types"].items():
        print(
            f"- {query_type}: queries={item['queries']}, "
            f"R@1={item['recall_at_1']}, R@3={item['recall_at_3']}, R@5={item['recall_at_5']}, "
            f"S@1={item['snippet_at_1']}, S@3={item['snippet_at_3']}, S@5={item['snippet_at_5']}, "
            f"MRR={item['mrr']}"
        )
    print()

    failed_queries = [item for item in results["queries"] if not item.get("passed")]
    if not failed_queries:
        print("All retrieval queries passed at top-1 with snippet match.")
        return

    print("Failed Queries")
    for item in failed_queries:
        print(f"- {item['name']} ({item['query_type']})")
        print(f"  query: {item['query']}")
        print(f"  route: {item['route']}")
        top_hit = item.get("top_hit")
        if top_hit:
            citation = top_hit.get("citation") or {}
            print(f"  top hit file: {citation.get('file_name')}")
            print(f"  top hit doc: {top_hit.get('doc_number')}")
            print(f"  top hit snippet: {top_hit.get('snippet')}")
        else:
            print("  top hit: none")
        print()


def _print_evaluation(results):
    summary = results['summary']
    print("Evaluation Summary")
    print()
    print(f"Dataset: {summary['dataset']}")
    print(f"Documents: {summary['passed_documents']}/{summary['documents']} passed")
    print(f"Field accuracy: {summary['field_accuracy']}")
    print(f"Line item accuracy: {summary['line_item_accuracy']}")
    print()
    print("By Supplier")
    for supplier_name, item in summary['suppliers'].items():
        print(f"- {supplier_name}: documents={item['passed_documents']}/{item['documents']}, fields={item['field_accuracy']}, line_items={item['line_item_accuracy']}")
    print()

    failed_documents = [item for item in results['documents'] if not item.get('passed')]
    if failed_documents:
        print("Failed Documents")
        for item in failed_documents:
            print(f"- {item['name']} ({item['supplier']})")
            for check in item['checks']:
                if not check['passed']:
                    print(f"  {check['field']}: expected={check['expected']} actual={check['actual']}")
        print()
    else:
        print("All evaluation documents passed.")


def main():
    parser = argparse.ArgumentParser(description="Factory document RAG")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Create database tables")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a PDF file or directory")
    ingest_parser.add_argument("path")
    ingest_parser.add_argument("--force", action="store_true")
    ingest_parser.add_argument("--json", action="store_true")

    query_parser = subparsers.add_parser("query", help="Run a query")
    query_parser.add_argument("query")
    query_parser.add_argument("--limit", type=int, default=5)
    query_parser.add_argument("--no-cache", action="store_true")
    query_parser.add_argument("--json", action="store_true")

    find_parser = subparsers.add_parser("find", help="Find matching documents with concise output")
    find_parser.add_argument("query")
    find_parser.add_argument("--limit", type=int, default=5)
    find_parser.add_argument("--no-cache", action="store_true")
    find_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="Run validation checks")
    validate_parser.add_argument("--ingest", help="Optional path to ingest before retrieval checks")
    validate_parser.add_argument("--json", action="store_true")

    evaluate_parser = subparsers.add_parser("evaluate", help="Run extraction evaluation on a dataset file")
    evaluate_parser.add_argument("dataset", help="Path to a JSON dataset file")
    evaluate_parser.add_argument("--json", action="store_true")

    retrieval_evaluate_parser = subparsers.add_parser("evaluate-retrieval", help="Run retrieval evaluation on a golden query file")
    retrieval_evaluate_parser.add_argument("dataset", help="Path to a retrieval golden JSON file")
    retrieval_evaluate_parser.add_argument("--limit", type=int, default=5)
    retrieval_evaluate_parser.add_argument("--json", action="store_true")

    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    health_parser = subparsers.add_parser("health", help="Show service health")
    health_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    runtime = get_runtime()

    if args.command == "bootstrap":
        runtime.bootstrap()
        print("Database schema ready")
        return

    if args.command == "ingest":
        results = runtime.ingestion_service.ingest_path(args.path, force=args.force)
        if args.json:
            _print_json({"results": results})
        else:
            _print_ingest(results)
        return

    if args.command == "query":
        response = runtime.query_service.run(args.query, limit=args.limit, use_cache=not args.no_cache)
        if args.json:
            _print_json(response)
        else:
            _print_query(response)
        return

    if args.command == "find":
        response = runtime.query_service.run(args.query, limit=args.limit, use_cache=not args.no_cache)
        if args.json:
            _print_json(response)
        else:
            _print_find(response)
        return

    if args.command == "validate":
        results = run_validation(runtime, ingest_path=args.ingest)
        if args.json:
            _print_json(results)
        else:
            _print_validation(results)
        return

    if args.command == "evaluate":
        results = evaluate_dataset(args.dataset)
        if args.json:
            _print_json(results)
        else:
            _print_evaluation(results)
        return

    if args.command == "evaluate-retrieval":
        results = evaluate_retrieval(args.dataset, runtime.query_service, limit=args.limit)
        if args.json:
            _print_json(results)
        else:
            _print_retrieval_evaluation(results)
        return

    if args.command == "serve":
        from factory_rag.api import run as run_api

        run_api(host=args.host, port=args.port)
        return

    if args.command == "health":
        health = runtime.health()
        if args.json:
            _print_json(health)
        else:
            for key, value in health.items():
                print(f"{key}: {value}")


if __name__ == "__main__":
    main()
