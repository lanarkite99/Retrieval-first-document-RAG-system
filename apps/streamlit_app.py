import json
import os
from hashlib import sha1
from urllib import error, request

import streamlit as st


API_URL = os.getenv("FACTORY_RAG_API_URL", "http://localhost:8000")
DEFAULT_INGEST_INBOX = os.getenv("FACTORY_RAG_INGEST_INBOX", "/app/data/incoming")


def _snippet_widget_key(match, key_prefix):
    parts = [
        key_prefix,
        str(match.get("document") or ""),
        str(match.get("file") or ""),
        str(match.get("page") or ""),
        str(match.get("snippet") or ""),
    ]
    digest = sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{key_prefix}-snippet-{digest}"


st.set_page_config(
    page_title="Factory RAG Search",
    page_icon="F",
    layout="wide",
)


def _request_json(path, payload=None, method="GET", timeout=30):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(
        f"{API_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )

    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _run_find(query, limit, use_cache):
    return _request_json(
        "/find",
        payload={
            "query": query,
            "limit": limit,
            "use_cache": use_cache,
        },
        method="POST",
        timeout=120,
    )


def _get_ingest_inbox():
    try:
        response = _request_json("/documents/inbox", timeout=15)
        return response.get("path") or DEFAULT_INGEST_INBOX
    except Exception:
        return DEFAULT_INGEST_INBOX


def _run_ingest_inbox(force=False):
    return _request_json(
        "/documents/ingest/inbox",
        payload={"force": force},
        method="POST",
        timeout=600,
    )


def _render_ingest_results(result):
    if not result:
        return

    summary = result.get("summary") or {}
    st.markdown("## Ingestion Summary")
    metric_columns = st.columns(5)
    metric_columns[0].metric("Files", result.get("total_files") or 0)
    metric_columns[1].metric("Processed", summary.get("processed", 0))
    metric_columns[2].metric("Duplicates", summary.get("duplicate", 0))
    metric_columns[3].metric("Partial", summary.get("partial", 0))
    metric_columns[4].metric("Failed", summary.get("failed", 0))
    st.caption(f"Inbox folder: {result.get('path') or '-'}")

    rows = []
    for item in result.get("results") or []:
        rows.append(
            {
                "status": item.get("status"),
                "file": item.get("source_filename"),
                "doc_type": item.get("doc_type"),
                "doc_number": item.get("doc_number"),
                "chunks": item.get("chunks"),
                "error": item.get("error"),
            }
        )

    if rows:
        with st.expander("View Ingestion Results", expanded=False):
            st.dataframe(rows, use_container_width=True)


def _render_match(match, title, key_prefix):
    st.markdown(f"### {title}")
    left, right = st.columns([3, 2])

    with left:
        st.write(f"**Document:** {match.get('document') or '-'}")
        st.write(f"**File:** {match.get('file') or '-'}")
        st.write(f"**Page:** {match.get('page') or '-'}")
        if match.get("supplier"):
            st.write(f"**Supplier:** {match['supplier']}")
        if match.get("date"):
            st.write(f"**Date:** {match['date']}")
        if match.get("amount") is not None and match.get("currency"):
            st.write(f"**Amount:** {match['amount']} {match['currency']}")

    with right:
        if match.get("location"):
            st.code(match["location"], language="text")
            st.caption("Stored file location")

    if match.get("snippet"):
        st.info(match["snippet"])

    with st.expander("More Context"):
        st.write("This match may not directly answer the question, but it points to the most relevant document and page found by retrieval.")
        st.write(f"**Document:** {match.get('document') or '-'}")
        st.write(f"**File:** {match.get('file') or '-'}")
        st.write(f"**Location:** {match.get('location') or '-'}")
        st.write(f"**Page:** {match.get('page') or '-'}")
        if match.get("supplier"):
            st.write(f"**Supplier:** {match['supplier']}")
        if match.get("date"):
            st.write(f"**Date:** {match['date']}")
        if match.get("amount") is not None and match.get("currency"):
            st.write(f"**Amount:** {match['amount']} {match['currency']}")
        if match.get("snippet"):
            st.text_area(
                "Evidence snippet",
                value=match["snippet"],
                height=120,
                disabled=True,
                key=_snippet_widget_key(match, key_prefix),
            )
        else:
            st.caption("No text snippet available for this match.")


def main():
    st.title("Factory Document Search")
    st.caption("Search invoices, BOMs, e-way bills, and financial documents by number, amount, supplier, item, or material code.")

    if "ingest_result" not in st.session_state:
        st.session_state["ingest_result"] = None

    with st.sidebar:
        st.header("Search Options")
        limit = st.slider("Matches", min_value=1, max_value=10, value=5)
        use_cache = st.toggle("Use cache", value=True)
        st.caption(f"API: {API_URL}")
        st.divider()
        st.header("Document Intake")
        ingest_inbox_path = _get_ingest_inbox()
        st.caption("Drop PDFs into the shared inbox folder, then trigger bulk ingestion.")
        st.code(ingest_inbox_path, language="text")
        force_reingest = st.toggle(
            "Force reingest",
            value=False,
            help="Rebuild already ingested PDFs from the inbox folder.",
        )
        if st.button("Ingest Inbox Folder", use_container_width=True):
            try:
                with st.spinner("Ingesting documents from inbox..."):
                    st.session_state["ingest_result"] = _run_ingest_inbox(force=force_reingest)
            except error.HTTPError as exc:
                st.error(f"Ingestion API error: {exc.code}")
            except Exception as exc:
                st.error(f"Could not start ingestion: {exc}")
        st.markdown("**Examples**")
        st.markdown("- `TF/2026-27/001`")
        st.markdown("- `annual cloud hosting invoice`")
        st.markdown("- `find me material code for Seat Foam Cushion`")
        st.markdown("- `vehicle number for e-way bill TF/2026-27/001`")

    if st.session_state.get("ingest_result"):
        _render_ingest_results(st.session_state["ingest_result"])

    query = st.text_input("Search", placeholder="Enter invoice number, supplier, amount, item, or material code")

    if not query:
        st.write("Enter a query to search your document corpus.")
        return

    try:
        with st.spinner("Searching documents..."):
            result = _run_find(query, limit=limit, use_cache=use_cache)
    except error.HTTPError as exc:
        st.error(f"API error: {exc.code}")
        return
    except Exception as exc:
        st.error(f"Could not reach API: {exc}")
        return

    top_row = st.columns(2)
    top_row[0].metric("Matches", result.get("matches") or 0)
    top_row[1].metric("Status", "Found" if result.get("best_match") else "No match")

    if not result.get("best_match"):
        st.warning("No matching documents found.")
        return

    _render_match(result["best_match"], "Best Match", "best-match")

    more_matches = result.get("more_matches") or []
    if more_matches:
        st.markdown("## More Matches")
        for index, match in enumerate(more_matches, start=2):
            with st.expander(f"Match {index}: {match.get('document') or match.get('file')}"):
                _render_match(match, f"Match {index}", f"match-{index}")


if __name__ == "__main__":
    main()

