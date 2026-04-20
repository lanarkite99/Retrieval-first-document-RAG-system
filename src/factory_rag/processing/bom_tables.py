import re

from factory_rag.document_schema import BOM_LINE_ITEM_FIELDS


STOP_WORDS = {
    "notes",
    "note",
    "approved by",
    "authorised signatory",
    "authorized signatory",
    "terms",
    "bank details",
    "summary",
    "total",
    "grand total",
}


def _normalize(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _split_cells(line):
    line = line.strip()
    if not line:
        return []

    if "|" in line:
        cells = [cell.strip() for cell in line.split("|")]
        return [cell for cell in cells if cell]

    if "\t" in line:
        cells = [cell.strip() for cell in line.split("\t")]
        return [cell for cell in cells if cell]

    parts = re.split(r"\s{2,}", line)
    cells = []
    for part in parts:
        part = part.strip()
        if part:
            cells.append(part)
    return cells


def _match_column(cell):
    normalized = _normalize(cell)
    for field_name, aliases in BOM_LINE_ITEM_FIELDS.items():
        for alias in aliases:
            if normalized == _normalize(alias):
                return field_name
    return None


def _score_header(cells):
    mapping = {}
    matched = 0

    for index, cell in enumerate(cells):
        field_name = _match_column(cell)
        if not field_name:
            continue
        if field_name in mapping:
            continue
        mapping[field_name] = index
        matched += 1

    return matched, mapping


def _is_stop_line(line):
    normalized = _normalize(line)
    if not normalized:
        return True
    if normalized in STOP_WORDS:
        return True
    for word in STOP_WORDS:
        if normalized.startswith(word):
            return True
    return False


def _parse_quantity(value):
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    if not match:
        return None
    number = match.group(0)
    if "." in number:
        return float(number)
    return int(number)


def _is_probable_row(cells, header_map):
    if len(cells) < 2:
        return False

    if "description" in header_map:
        index = header_map["description"]
        if index < len(cells) and cells[index].strip():
            return True

    if "part_number" in header_map:
        index = header_map["part_number"]
        if index < len(cells) and re.search(r"[A-Za-z0-9-]{3,}", cells[index]):
            return True

    return False


def _build_row(cells, header_map):
    row = {}

    for field_name, index in header_map.items():
        if index >= len(cells):
            continue
        value = cells[index].strip()
        if not value:
            continue
        if field_name == "quantity":
            row[field_name] = _parse_quantity(value)
        else:
            row[field_name] = value

    return row


def extract_bom_line_items(text):
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    header_index = None
    header_map = None
    header_cells = None

    for index, line in enumerate(lines):
        cells = _split_cells(line)
        if len(cells) < 3:
            continue
        matched, mapping = _score_header(cells)
        if matched >= 3 and "description" in mapping:
            header_index = index
            header_map = mapping
            header_cells = cells
            break

    if header_index is None:
        return {
            "line_items": [],
            "table_header": None,
            "column_map": {},
            "line_item_count": 0,
        }

    rows = []
    current_row = None

    for line in lines[header_index + 1 :]:
        if _is_stop_line(line):
            if rows:
                break
            continue

        cells = _split_cells(line)
        if not cells:
            if rows:
                break
            continue

        if _score_header(cells)[0] >= 3:
            continue

        if _is_probable_row(cells, header_map):
            row = _build_row(cells, header_map)
            if row:
                rows.append(row)
                current_row = row
            continue

        if current_row and len(cells) == 1 and cells[0]:
            description = current_row.get("description", "")
            current_row["description"] = (description + " " + cells[0]).strip()
            continue

        if rows:
            break

    return {
        "line_items": rows,
        "table_header": header_cells,
        "column_map": header_map,
        "line_item_count": len(rows),
    }
