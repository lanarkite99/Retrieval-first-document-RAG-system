# Factory Document RAG

Retrieval-first document search system for factory and operations workflows, designed for GST invoices, bills of materials, e-way bills, and financial PDFs.

This project focuses on the business problem that matters most in practice: given an invoice number, supplier, amount, line item, material code, or phrase, return the correct document, page, and supporting evidence quickly.

## Overview

The system ingests PDF documents, extracts text and lightweight metadata, creates multiple evidence units, and serves search through:

- a Python CLI
- a FastAPI backend
- a Streamlit interface
- a Docker Compose deployment stack

It is intentionally retrieval-first rather than parser-first. Structured extraction is used as enrichment, but the primary product is evidence-backed document retrieval.

## Key Features

- PDF ingestion from files or folders
- Shared inbox ingestion workflow through API and Streamlit
- Multi-store retrieval architecture with Postgres, OpenSearch, Qdrant, and Redis
- Evidence chunking across text blocks, lines, table rows, and header fields
- Query routing for exact identifier search, lexical lookup, and hybrid retrieval
- Evidence-first responses with file path, page, snippet, and confidence
- Optional Gemini-based answer synthesis on top of retrieved evidence
- FastAPI search endpoints for integration
- Streamlit UI for business users
- Retrieval and extraction evaluation workflows

## Scope and Positioning

This repository is strongest as a retrieval-first search system for business documents.

Best-fit use cases:

- invoice number lookup
- line-item and amount lookup
- BOM and material code search
- e-way bill lookup
- evidence-backed internal document search

It should not be positioned as a universal document automation or format-independent structured extraction engine. Extraction quality is still meaningfully weaker than retrieval quality on unseen layouts.

## Architecture

```mermaid
flowchart LR
    U[User / CLI / API / UI] --> QS[Query Service]
    QS --> RT[Query Router]
    RT --> EX[Exact Match]
    RT --> LX[Lexical Retrieval]
    RT --> HY[Hybrid Retrieval]

    EX --> PG[(Postgres)]
    LX --> PG
    LX --> OS[(OpenSearch)]
    HY --> PG
    HY --> OS
    HY --> QD[(Qdrant)]

    QS --> RR[Rerank and Merge]
    RR --> AS[Answer Service]
    AS --> GM[Gemini Optional]
    RR --> OUT[Evidence-First Response]
```

## Ingestion Pipeline

```mermaid
flowchart TD
    A[PDF File or Folder] --> B[Text Extraction]
    B --> C[Document Classification]
    C --> D[Metadata Extraction]
    D --> E[Chunk Builder]
    E --> F1[Text Chunks]
    E --> F2[Line Chunks]
    E --> F3[Table Row Chunks]
    E --> F4[Header Field Chunks]

    D --> G[(Postgres Documents)]
    F1 --> H[(Postgres Chunks)]
    F2 --> H
    F3 --> H
    F4 --> H

    H --> I[Embedding Service]
    I --> J[(Qdrant)]
    H --> K[(OpenSearch)]
    A --> L[(Local Storage)]
```

## Default Models

- Embedding backend: `sentence-transformer`
- Embedding model: `BAAI/bge-small-en-v1.5`
- LLM backend: `gemini`
- LLM model: `gemini-2.5-flash`
- Fallback embeddings: local hash embeddings

Why this setup works well for this project:

- identifiers, codes, totals, and rates depend heavily on lexical retrieval and normalization
- semantic embeddings help more on fuzzy text queries than exact business lookup
- Gemini is used as a summarization layer after retrieval, not as the primary search engine

## Repository Structure

```text
src/factory_rag/
  core/         runtime and configuration
  processing/   extraction, chunking, metadata, routing, embeddings helpers
  services/     ingestion, retrieval, query execution, answer generation
  stores/       Postgres, OpenSearch, Qdrant, Redis, local storage

apps/
  streamlit_app.py

eval/
  datasets/
  runners/
  checks/

tests/
  unit tests for routing and parsing behavior

scripts/
  data generation and helper scripts
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Start Infrastructure

```bash
docker compose up -d --build
```

This starts:

- FastAPI on `http://localhost:8000`
- Streamlit on `http://localhost:8501`
- Postgres on `localhost:5432`
- Qdrant on `localhost:6333`
- OpenSearch on `localhost:9200`
- Redis on `localhost:6379`

### 3. Bootstrap and Ingest

```bash
python main.py bootstrap
python main.py ingest data
```

To rebuild documents after chunking or indexing changes:

```bash
python main.py ingest golden_set --force
```

For the Streamlit and Docker deployment flow, the application also supports a configured inbox directory for bulk ingestion. Users can place PDFs in the inbox folder and trigger ingestion from the UI without entering filesystem paths manually.

## Usage

### CLI

Verbose retrieval output:

```bash
python main.py query "TF/2026-27/001"
python main.py query "which item has the rate of 85000.00?"
python main.py query "find me material code for Seat Foam Cushion"
```

Business-facing concise output:

```bash
python main.py find "TF/2026-27/001"
python main.py find "annual cloud hosting invoice"
python main.py find "Seat Foam Cushion"
```

Health check:

```bash
python main.py health
```

### API

Run the API locally:

```bash
python main.py serve --host 0.0.0.0 --port 8000
```

Primary endpoints:

- `GET /`
- `GET /health`
- `GET /metrics`
- `POST /documents/ingest`
- `GET /documents/inbox`
- `POST /documents/ingest/inbox`
- `GET /documents/{id}`
- `POST /query`
- `POST /find`

### Streamlit

Run the business-facing UI:

```bash
streamlit run apps/streamlit_app.py
```

The UI surfaces the top match first and shows:

- document number
- file name
- page
- storage path
- amount and supplier when available
- evidence snippet or nearby context

It also includes a simple document intake workflow:

- users drop PDFs into the configured inbox folder
- Streamlit triggers bulk ingestion through the API
- the UI displays processed, duplicate, partial, and failed counts

## Evaluation

Two evaluation modes are included:

### Retrieval Evaluation

```bash
python main.py evaluate-retrieval eval/datasets/golden_set_retrieval_golden.json
python main.py evaluate-retrieval golden_set/final_metrics/final_metrics_retrieval_golden.json
```

Primary metrics:

- `Recall@1`
- `Recall@3`
- `Recall@5`
- `Snippet@1`
- `Snippet@3`
- `Snippet@5`
- `MRR`

Latest holdout retrieval snapshot:

- Dataset: `golden_set/final_metrics/final_metrics_retrieval_golden.json`
- Queries: `36`
- `Recall@1`: `0.8611`
- `Recall@3`: `0.9722`
- `Recall@5`: `1.0`
- `Snippet@1`: `0.5556`
- `Snippet@3`: `0.6944`
- `Snippet@5`: `0.7778`
- `MRR`: `0.9222`

### Extraction Evaluation

```bash
python main.py evaluate eval/datasets/golden_set_extraction_eval.json
python main.py evaluate golden_set/final_metrics/final_metrics_extraction_eval.json
```

Primary metrics:

- document pass rate
- field accuracy
- line item accuracy

Latest holdout extraction snapshot:

- Dataset: `golden_set/final_metrics/final_metrics_extraction_eval.json`
- Documents passed: `0/18`
- Field accuracy: `0.5591`
- Line item accuracy: `0.7222`

Interpretation:

- retrieval is strong enough for a practical v1 document search system
- extraction is still not strong enough to position this as fully automated document AI

## Testing

Unit tests cover routing, metadata normalization, and BOM parsing behavior.

```bash
python -m unittest discover -s tests -v
```

## Environment Variables

```env
RAG_POSTGRES_DSN=postgresql://rag:ragpass@localhost:5432/ragdb
RAG_QDRANT_URL=http://localhost:6333
RAG_OPENSEARCH_URL=http://localhost:9200
RAG_REDIS_URL=redis://localhost:6379/0

RAG_EMBEDDING_BACKEND=sentence-transformer
RAG_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

RAG_LLM_BACKEND=gemini
RAG_LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_key_here

RAG_ENABLE_SUMMARY=1
RAG_STORAGE_DIR=storage
RAG_DATA_DIR=data
RAG_INGEST_INBOX=data/incoming
```

Optional alternatives:

- `RAG_EMBEDDING_BACKEND=gemini`
- `RAG_GEMINI_EMBEDDING_MODEL=gemini-embedding-001`

## Resetting the System

To clear ingested state and start from scratch:

```powershell
docker compose down -v
Remove-Item -Recurse -Force .\storage\*
docker compose up -d
python main.py bootstrap
```

Then reingest:

```powershell
python main.py ingest golden_set --force
```

## Operational Ingestion Pattern

The current repository supports two ingestion styles:

- direct CLI or API ingestion by path
- inbox-based ingestion for non-technical users

The inbox workflow is the better operational fit for a small business team:

- users drop PDFs into a shared `incoming` folder
- the UI or API triggers bulk ingestion
- duplicates are skipped using checksum-based deduplication

For a more production-style setup, the recommended future design is:

- `incoming/` for newly received files
- `processed/` for successfully ingested files
- `failed/` for files that need manual review
- scheduled ingestion every few minutes or at a fixed daily time
- persistent checksum and ingestion-state tracking rather than relying on folder dates

## Demo Data

Generate fresh sample PDFs:

```bash
python scripts/generate_demo_pdfs.py
```

Example workflow:

```bash
python main.py ingest data/generated_batch
python main.py find "seat foam cushion"
python main.py evaluate eval/datasets/generated_batch_eval.json
```

## Design Principles

- Retrieval-first rather than parser-first
- Evidence-first responses rather than unsupported chat answers
- Small canonical schema with flexible metadata
- Lexical retrieval for identifiers, codes, totals, and rates
- Hybrid retrieval for fuzzy text queries
- LLMs as optional summarization helpers rather than source of truth

## Limitations

- strongest on native-text PDFs
- OCR and scanned-document support is limited
- extraction remains little weak across unseen layouts
- financial statement retrieval is weaker than invoice retrieval
- some BOM component questions still depend on better row-level evidence selection

## Future Improvements

- automated scheduled ingestion from a shared inbox folder
- `incoming / processed / failed` folder lifecycle for cleaner operations
- background ingestion jobs instead of long synchronous UI requests
- ingestion manifests and richer operational reporting
- OCR support for scanned documents
- stronger financial statement retrieval and answer-bearing snippet selection

## License

Apache 2.0
