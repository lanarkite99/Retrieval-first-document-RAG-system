import json
import os
from hashlib import sha1
from urllib import error, request

import streamlit as st


API_URL = os.getenv("FACTORY_RAG_API_URL", "http://localhost:8000")


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


def _run_find(query, limit, use_cache):
    payload = json.dumps(
        {
            "query": query,
            "limit": limit,
            "use_cache": use_cache,
        }
    ).encode("utf-8")

    req = request.Request(
        f"{API_URL}/find",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data


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

    with st.sidebar:
        st.header("Search Options")
        limit = st.slider("Matches", min_value=1, max_value=10, value=5)
        use_cache = st.toggle("Use cache", value=True)
        st.caption(f"API: {API_URL}")
        st.markdown("**Examples**")
        st.markdown("- `TF/2026-27/001`")
        st.markdown("- `annual cloud hosting invoice`")
        st.markdown("- `find me material code for Seat Foam Cushion`")
        st.markdown("- `vehicle number for e-way bill TF/2026-27/001`")

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
