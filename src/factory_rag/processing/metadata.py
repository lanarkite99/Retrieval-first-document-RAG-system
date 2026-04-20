import re
from datetime import datetime

from factory_rag.bom_tables import extract_bom_line_items
from factory_rag.document_schema import CANONICAL_FIELDS, DOC_TYPE_FIELDS


MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

SKIP_LABELS = {
    "description",
    "qty",
    "quantity",
    "rate",
    "amount",
    "tax",
    "item",
    "component",
    "unit",
    "hsn",
    "sac",
    "sr no",
    "line no",
}

TABLE_HEADER_TOKENS = {
    "amount",
    "code",
    "component",
    "description",
    "ext",
    "extended",
    "gst",
    "header",
    "hsn",
    "item",
    "material",
    "measure",
    "note",
    "notes",
    "part",
    "pos",
    "position",
    "qty",
    "quantity",
    "rate",
    "remarks",
    "revision",
    "taxable",
    "unit",
    "uom",
}

ALIAS_LABELS = set()
for field in CANONICAL_FIELDS.values():
    for alias in field["aliases"]:
        ALIAS_LABELS.add(alias)


def _search(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match
    return None


def _lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def _normalize_label(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _normalize_text(value):
    return re.sub(r"\s+", " ", (value or "")).strip()


def _looks_like_label(value):
    if not value:
        return False
    normalized = _normalize_label(value)
    if normalized in SKIP_LABELS:
        return False
    words = normalized.split()
    if len(words) > 6:
        return False
    if re.search(r"\d", normalized):
        return False
    return True


def _find_following_value(lines, index):
    for offset in range(1, 4):
        if index + offset >= len(lines):
            break
        candidate = _normalize_text(lines[index + offset])
        if not candidate:
            continue
        if candidate.endswith(":"):
            continue
        return candidate
    return None


def _is_table_header_line(value):
    normalized = _normalize_label(value)
    if not normalized:
        return False

    tokens = normalized.split()
    if len(tokens) < 4:
        return False

    matched = 0
    for token in tokens:
        if token in TABLE_HEADER_TOKENS:
            matched += 1

    return matched >= 4 and (matched / len(tokens)) >= 0.5


def _collect_labeled_values(lines):
    fields = []

    for index, line in enumerate(lines):
        if _is_table_header_line(line):
            continue

        if ":" in line:
            left, right = line.split(":", 1)
            label = _normalize_label(left)
            value = _normalize_text(right)
            if _looks_like_label(label):
                if value:
                    fields.append({"label": label, "value": value, "source": "inline"})
                else:
                    candidate = _find_following_value(lines, index)
                    if candidate:
                        fields.append({"label": label, "value": candidate, "source": "next_line"})
                continue

        if line.endswith(":"):
            label = _normalize_label(line[:-1])
            if _looks_like_label(label):
                candidate = _find_following_value(lines, index)
                if candidate:
                    fields.append({"label": label, "value": candidate, "source": "next_line"})
                continue

        normalized_line = _normalize_label(line)
        if normalized_line in ALIAS_LABELS:
            candidate = _find_following_value(lines, index)
            if candidate:
                fields.append({"label": normalized_line, "value": candidate, "source": "heading"})

    return fields


def _first_label_value(fields, aliases):
    alias_labels = []
    for alias in aliases:
        alias_labels.append(_normalize_label(alias))

    for alias_label in alias_labels:
        for item in fields:
            if item["label"] == alias_label:
                return item
    return None


def _parse_date(value):
    if not value:
        return None

    value = value.strip()
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
        "%d %b, %Y",
        "%d %B, %Y",
    ]

    for format_name in formats:
        try:
            return datetime.strptime(value, format_name).date()
        except ValueError:
            continue

    return None


def _parse_amount(value):
    if not value:
        return None

    cleaned = value.replace(",", "").strip()
    cleaned = re.sub(r"^(?:rs\.?|inr|₹)\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^I(?=\d)", "", cleaned)
    matches = re.findall(r"\d+(?:\.\d+)?", cleaned)
    if not matches:
        return None
    return float(matches[-1])


def _parse_gstin(value):
    if not value:
        return None
    match = re.search(r"[0-9A-Z]{15}", value.upper())
    if not match:
        return None
    return match.group(0)


def _parse_value(field_type, value):
    if field_type == "date":
        return _parse_date(value)
    if field_type == "amount":
        return _parse_amount(value)
    if field_type == "gstin":
        return _parse_gstin(value)
    if field_type == "text":
        return _normalize_text(value)
    return value


def _regex_fallbacks(text):
    fallbacks = {}

    doc_match = _search(
        [
            r"\b([A-Z]{1,8}-[A-Z]{1,8}-\d{4}-\d+)\b",
            r"\b(INV-[A-Z0-9-]+)\b",
            r"\b(GST-INV-[A-Z0-9-]+)\b",
            r"\b(BOM-[A-Z0-9-]+)\b",
            r"\b([0-9]{4}-[A-Z]{2}-[0-9]{2})\b",
        ],
        text,
    )
    if doc_match:
        fallbacks["doc_number"] = doc_match.group(1).strip()

    date_match = _search(
        [
            r"\b([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{4})\b",
            r"\b([0-9]{1,2}-[A-Za-z]{3,9}-[0-9]{4})\b",
            r"\b([0-9]{4}-[0-9]{2}-[0-9]{2})\b",
            r"\b([0-9]{1,2}\s+[A-Za-z]{3,9}\s*,?\s*[0-9]{4})\b",
        ],
        text,
    )
    if date_match:
        fallbacks["doc_date"] = _parse_date(date_match.group(1))

    gstins = re.findall(r"[0-9A-Z]{15}", text.upper())
    if gstins:
        fallbacks["gstin"] = gstins[0]
        if len(gstins) > 1:
            fallbacks["buyer_gstin"] = gstins[1]

    amount_match = _search(
        [
            r"(?:Grand Total|Total Amount|Invoice Total|Net Amount|Amount Payable|Final Amount|Total)\s*[:\-]?\s*(?:Rs\.?|INR|₹|I)?\s*([0-9I,]+\.\d{2}|[0-9I,]+)",
        ],
        text,
    )
    if amount_match:
        fallbacks["amount"] = _parse_amount(amount_match.group(1))

    return fallbacks


def _build_default_metadata(doc_type):
    return {
        "doc_type": doc_type,
        "currency": "INR",
        "doc_number": None,
        "supplier_name": None,
        "buyer_name": None,
        "doc_date": None,
        "amount": None,
        "gstin": None,
        "buyer_gstin": None,
        "po_number": None,
        "payment_terms": None,
        "part_number": None,
        "revision": None,
        "plant_code": None,
    }


def extract_metadata(doc_type, text):
    lines = _lines(text)
    labeled_values = _collect_labeled_values(lines)
    data = _build_default_metadata(doc_type)
    extracted_fields = {}
    confidence = {}
    consumed_labels = set()

    active_fields = DOC_TYPE_FIELDS.get(doc_type, DOC_TYPE_FIELDS["unknown"])

    for field_name in active_fields:
        schema = CANONICAL_FIELDS[field_name]
        match = _first_label_value(labeled_values, schema["aliases"])
        if not match:
            continue

        parsed_value = _parse_value(schema["type"], match["value"])
        if parsed_value in (None, ""):
            continue

        data[field_name] = parsed_value
        extracted_fields[field_name] = {
            "label": match["label"],
            "raw_value": match["value"],
            "source": match["source"],
        }
        confidence[field_name] = "high" if match["source"] == "inline" else "medium"
        consumed_labels.add(match["label"])

    for field_name, value in _regex_fallbacks(text).items():
        if field_name not in data or data.get(field_name) not in (None, ""):
            continue
        if value in (None, ""):
            continue
        data[field_name] = value
        extracted_fields[field_name] = {
            "label": "regex_fallback",
            "raw_value": value,
            "source": "regex",
        }
        confidence[field_name] = "medium"

    extra_fields = {}
    for item in labeled_values:
        label = item["label"]
        if label in consumed_labels:
            continue
        if label in SKIP_LABELS:
            continue
        if label in extra_fields:
            continue
        extra_fields[label] = item["value"]

    missing_fields = []
    for field_name in active_fields:
        if data.get(field_name) in (None, ""):
            missing_fields.append(field_name)

    data["extra_fields"] = extra_fields
    data["extraction"] = {
        "field_count": len(extracted_fields),
        "fields": extracted_fields,
        "confidence": confidence,
        "missing_fields": missing_fields,
    }

    if doc_type == "bom":
        bom_table = extract_bom_line_items(text)
        data["line_items"] = bom_table["line_items"]
        data["line_item_count"] = bom_table["line_item_count"]
        data["bom_table"] = {
            "table_header": bom_table["table_header"],
            "column_map": bom_table["column_map"],
        }
        data["extraction"]["line_item_count"] = bom_table["line_item_count"]

    return data


def extract_query_filters(query):
    filters = {}
    lowered = (query or "").lower()

    if "invoice" in lowered:
        filters["doc_type"] = "invoice"
    if "bill of material" in lowered or "bill of materials" in lowered or "bom" in lowered:
        filters["doc_type"] = "bom"

    doc_match = _search(
        [
            r"\b([A-Z]{1,10}/[0-9]{4}(?:-[0-9]{2})?/[0-9]{3,})\b",
            r"\b([A-Z]{1,8}-[A-Z]{1,8}-\d{4}-\d+)\b",
            r"\b(GST-INV-[A-Z0-9-]+)\b",
            r"\b(INV-[A-Z0-9-]+)\b",
            r"\b(BOM-[A-Z0-9-]+)\b",
            r"\b([0-9]{4}-[A-Z]{2}-[0-9]{2})\b",
        ],
        query,
    )
    if doc_match:
        filters["doc_number"] = doc_match.group(1).strip()

    supplier_match = _search(
        [
            r"(?:from|supplier|vendor)\s+([A-Za-z0-9&., -]+?)(?:\s+in\s+[A-Za-z]+\s+[0-9]{4}|\s+for\s+|\?|$)",
        ],
        query,
    )
    if supplier_match:
        filters["supplier_name"] = supplier_match.group(1).strip(" .?")

    month_match = _search([r"\b(" + "|".join(MONTHS.keys()) + r")[a-z]*\s+([0-9]{4})\b"], lowered)
    if month_match:
        filters["month"] = MONTHS[month_match.group(1)[:3]]
        filters["year"] = int(month_match.group(2))
    else:
        year_match = _search([r"\b(20[0-9]{2})\b"], lowered)
        if year_match:
            filters["year"] = int(year_match.group(1))

    row_query = any(word in lowered for word in ["item", "line", "rate", "qty", "quantity", "price", "part", "material", "vehicle", "revenue", "profit", "cash", "balance"])
    explicit_total_query = any(word in lowered for word in ["amount", "total", "grand total", "invoice total", "amount payable", "net amount"])
    numeric_only_query = bool(re.fullmatch(r"\s*(?:rs\.?|inr|₹)?\s*[0-9,]+(?:\.\d{1,2})?\s*", query or "", re.IGNORECASE))

    if explicit_total_query and not row_query or numeric_only_query:
        amount_match = _search(
            [
                r"(?:amount|total|invoice total|grand total|amount payable|net amount)\s*(?:is|=|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.\d{1,2})?)",
                r"\b([0-9,]+\.\d{2})\b",
            ],
            query,
        )
        if amount_match:
            amount = _parse_amount(amount_match.group(1))
            if amount is not None:
                filters["amount"] = amount

    gstin_match = _search([r"\b([0-9A-Z]{15})\b"], query.upper())
    if gstin_match:
        filters["gstin"] = gstin_match.group(1)

    return filters
