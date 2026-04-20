import re


HEADINGS = {
    "from",
    "to",
    "supplier",
    "buyer",
    "bill to",
    "description",
    "subtotal",
    "grand total",
    "bank details",
    "notes",
    "terms",
    "item",
    "component",
}

ROW_SECTION_WORDS = {
    "description",
    "hsn",
    "item",
    "component",
    "material",
    "qty",
    "quantity",
    "rate",
    "taxable",
}


def _is_heading(line):
    lowered = line.lower().strip(":")
    if lowered in HEADINGS:
        return True
    if line.isupper() and len(line.split()) <= 6:
        return True
    if line.endswith(":") and len(line.split()) <= 6:
        return True
    return False


def _normalize(value):
    value = (value or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _contains_number(value):
    return bool(re.search(r"\d", value or ""))


def _contains_decimal(value):
    return bool(re.search(r"\d+\.\d+", value or ""))


def _numeric_token_count(value):
    return len(re.findall(r"\d+(?:\.\d+)?", value or ""))


def _is_text_rich_line(value):
    letters = re.findall(r"[A-Za-z]", value or "")
    return len(letters) >= 5


def _looks_like_row_section(section):
    normalized = _normalize(section)
    for word in ROW_SECTION_WORDS:
        if word in normalized:
            return True
    return False


def _page_lines_with_sections(page):
    rows = []
    current_section = "body"

    for line in page["text"].splitlines():
        line = line.strip()
        if not line:
            continue

        heading = _is_heading(line)
        if heading:
            current_section = line

        rows.append(
            {
                "page_number": page["page_number"],
                "section": current_section,
                "line": line,
                "is_heading": heading,
            }
        )

    return rows


def _split_page_into_blocks(page_lines):
    blocks = []
    current_lines = []
    current_section = "body"

    for item in page_lines:
        line = item["line"]

        if item["is_heading"]:
            if current_lines:
                blocks.append(
                    {
                        "page_number": item["page_number"],
                        "section": current_section,
                        "text": "\n".join(current_lines),
                    }
                )
                current_lines = []
            current_section = line
            current_lines.append(line)
            continue

        if current_lines and len(" ".join(current_lines)) + len(line) > 320:
            blocks.append(
                {
                    "page_number": item["page_number"],
                    "section": current_section,
                    "text": "\n".join(current_lines),
                }
            )
            current_lines = []

        current_lines.append(line)

    if current_lines:
        blocks.append(
            {
                "page_number": page_lines[0]["page_number"],
                "section": current_section,
                "text": "\n".join(current_lines),
            }
        )

    return blocks


def _split_large_block(block, chunk_size):
    lines = block["text"].splitlines()
    pieces = []
    current_lines = []

    for line in lines:
        candidate = "\n".join(current_lines + [line])
        if current_lines and len(candidate) > chunk_size:
            pieces.append(
                {
                    "page_number": block["page_number"],
                    "section": block["section"],
                    "chunk_text": "\n".join(current_lines),
                    "token_count": len(" ".join(current_lines).split()),
                    "evidence_type": "text_chunk",
                }
            )
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        pieces.append(
            {
                "page_number": block["page_number"],
                "section": block["section"],
                "chunk_text": "\n".join(current_lines),
                "token_count": len(" ".join(current_lines).split()),
                "evidence_type": "text_chunk",
            }
        )

    return pieces


def _build_text_chunks(page_lines, chunk_size):
    chunks = []
    if not page_lines:
        return chunks

    blocks = _split_page_into_blocks(page_lines)
    for block in blocks:
        if len(block["text"]) <= chunk_size:
            chunks.append(
                {
                    "page_number": block["page_number"],
                    "section": block["section"],
                    "chunk_text": block["text"],
                    "token_count": len(block["text"].split()),
                    "evidence_type": "text_chunk",
                }
            )
            continue

        for piece in _split_large_block(block, chunk_size):
            chunks.append(piece)

    return chunks


def _build_line_chunks(page_lines):
    chunks = []

    for item in page_lines:
        line = item["line"]
        if item["is_heading"]:
            continue
        if len(line) < 12:
            continue
        if len(line.split()) < 2:
            continue

        chunks.append(
            {
                "page_number": item["page_number"],
                "section": item["section"],
                "chunk_text": line,
                "token_count": len(line.split()),
                "evidence_type": "line_chunk",
            }
        )

    return chunks


def _build_table_row_chunks(page_lines):
    chunks = []

    for index, item in enumerate(page_lines):
        line = item["line"]
        if item["is_heading"]:
            continue

        if _is_text_rich_line(line) and _contains_number(line):
            if _contains_decimal(line) or _numeric_token_count(line) >= 2 or _looks_like_row_section(item["section"]):
                chunks.append(
                    {
                        "page_number": item["page_number"],
                        "section": item["section"],
                        "chunk_text": line,
                        "token_count": len(line.split()),
                        "evidence_type": "table_row",
                    }
                )
                continue

        if not _is_text_rich_line(line):
            continue
        if _contains_number(line):
            continue

        window_lines = [line]
        numeric_lines = 0

        for next_item in page_lines[index + 1 : index + 7]:
            if next_item["is_heading"]:
                break
            next_line = next_item["line"]
            window_lines.append(next_line)
            if _contains_number(next_line):
                numeric_lines += 1

        if numeric_lines < 3:
            continue

        chunks.append(
            {
                "page_number": item["page_number"],
                "section": item["section"],
                "chunk_text": "\n".join(window_lines),
                "token_count": len(" ".join(window_lines).split()),
                "evidence_type": "table_row",
            }
        )

    return chunks


def build_chunks(pages, chunk_size, chunk_overlap):
    del chunk_overlap

    chunks = []
    seen = set()

    for page in pages:
        page_lines = _page_lines_with_sections(page)
        for builder in [_build_text_chunks, _build_line_chunks, _build_table_row_chunks]:
            if builder is _build_text_chunks:
                built = builder(page_lines, chunk_size)
            else:
                built = builder(page_lines)

            for chunk in built:
                key = (
                    chunk["page_number"],
                    chunk["section"],
                    chunk["evidence_type"],
                    chunk["chunk_text"],
                )
                if key in seen:
                    continue
                seen.add(key)
                chunks.append(chunk)

    return chunks
