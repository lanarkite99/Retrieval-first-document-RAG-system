from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

from factory_rag.runtime import get_runtime


class IngestRequest(BaseModel):
    path: str


class IngestInboxRequest(BaseModel):
    force: bool = False


class QueryRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)
    use_cache: bool = True


app = FastAPI(
    title="Factory RAG API",
    version="1.0.0",
    description="Evidence-first retrieval API for invoices, BOMs, e-way bills, and related factory documents.",
)


@app.on_event("startup")
def startup_event():
    runtime = get_runtime()
    runtime.bootstrap()


@app.get("/", tags=["system"])
def index():
    return {
        "service": "factory-rag-api",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "search": "/find",
    }


@app.get("/health", tags=["system"])
def health():
    runtime = get_runtime()
    return runtime.health()


@app.get("/metrics", tags=["system"])
def metrics():
    runtime = get_runtime()
    return runtime.metrics.snapshot()


@app.post("/documents/ingest", tags=["documents"])
def ingest_documents(request: IngestRequest):
    runtime = get_runtime()
    return _build_ingest_response(request.path, runtime.ingestion_service.ingest_path(request.path))


@app.get("/documents/inbox", tags=["documents"])
def get_ingest_inbox():
    runtime = get_runtime()
    return {
        "path": str(runtime.settings.ingest_inbox_dir),
        "description": "Configured shared inbox for bulk document ingestion.",
    }


@app.post("/documents/ingest/inbox", tags=["documents"])
def ingest_inbox(request: IngestInboxRequest):
    runtime = get_runtime()
    inbox_path = str(runtime.settings.ingest_inbox_dir)
    results = runtime.ingestion_service.ingest_path(inbox_path, force=request.force)
    return _build_ingest_response(inbox_path, results)


@app.get("/documents/{doc_id}", tags=["documents"])
def get_document(doc_id: str):
    runtime = get_runtime()
    document = runtime.db.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.post("/query", tags=["search"])
def query_documents(request: QueryRequest):
    runtime = get_runtime()
    return runtime.query_service.run(request.query, limit=request.limit, use_cache=request.use_cache)


@app.post("/find", tags=["search"])
def find_documents(request: QueryRequest):
    runtime = get_runtime()
    response = runtime.query_service.run(request.query, limit=request.limit, use_cache=request.use_cache)
    return _build_find_response(response)


def _build_find_response(response):
    hits = response.get("hits") or []
    result = {
        "query": response.get("query"),
        "matches": response.get("diagnostics", {}).get("result_count", 0),
        "best_match": None,
        "more_matches": [],
    }

    if not hits:
        return result

    result["best_match"] = _hit_to_find_result(hits[0])

    for hit in hits[1:]:
        result["more_matches"].append(_hit_to_find_result(hit))

    return result


def _build_ingest_response(path, results):
    summary = {
        "processed": 0,
        "duplicate": 0,
        "partial": 0,
        "failed": 0,
    }

    for item in results:
        status = item.get("status")
        if status in summary:
            summary[status] += 1

    return {
        "path": path,
        "total_files": len(results),
        "summary": summary,
        "results": results,
    }


def _hit_to_find_result(hit):
    citation = hit.get("citation") or {}
    return {
        "document": hit.get("doc_number") or citation.get("file_name"),
        "file": citation.get("file_name"),
        "location": citation.get("storage_path"),
        "page": citation.get("page"),
        "supplier": hit.get("supplier_name"),
        "date": hit.get("doc_date"),
        "amount": hit.get("amount"),
        "currency": hit.get("currency"),
        "snippet": hit.get("snippet"),
    }


def run(host="127.0.0.1", port=8000):
    uvicorn.run("factory_rag.api:app", host=host, port=port, reload=False)
