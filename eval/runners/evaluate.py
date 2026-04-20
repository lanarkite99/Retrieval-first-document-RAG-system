import json
from datetime import date, datetime
from pathlib import Path

from factory_rag.classifier import classify_document
from factory_rag.extraction import extract_pdf
from factory_rag.metadata import extract_metadata


def _normalize_text(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    return " ".join(value.split())


def _normalize_number(value):
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except Exception:
        return None


def _normalize_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return _normalize_text(value)
    if isinstance(value, (int, float)):
        return _normalize_number(value)
    return value


def _compare_value(expected, actual):
    if isinstance(expected, (int, float)):
        return _normalize_number(expected) == _normalize_number(actual)
    return _normalize_value(expected) == _normalize_value(actual)


def _load_entry(entry):
    if entry.get("text"):
        text = entry["text"]
    elif entry.get("file"):
        text = extract_pdf(entry["file"])["full_text"]
    else:
        raise ValueError("Each evaluation entry needs either 'file' or 'text'.")

    doc_type = classify_document(text)
    metadata = extract_metadata(doc_type, text)
    return doc_type, metadata


def _score_fields(expected_fields, metadata):
    checks = []
    for field_name, expected_value in expected_fields.items():
        actual_value = metadata.get(field_name)
        passed = _compare_value(expected_value, actual_value)
        checks.append(
            {
                "field": field_name,
                "expected": expected_value,
                "actual": actual_value,
                "passed": passed,
            }
        )
    return checks


def _score_extra_fields(expected_fields, metadata):
    checks = []
    actual_extra = metadata.get("extra_fields", {})
    for field_name, expected_value in expected_fields.items():
        actual_value = actual_extra.get(field_name)
        passed = _compare_value(expected_value, actual_value)
        checks.append(
            {
                "field": field_name,
                "expected": expected_value,
                "actual": actual_value,
                "passed": passed,
            }
        )
    return checks


def _score_line_items(expected_items, metadata):
    actual_items = metadata.get("line_items", [])
    checks = []

    if len(expected_items) != len(actual_items):
        checks.append(
            {
                "field": "line_item_count",
                "expected": len(expected_items),
                "actual": len(actual_items),
                "passed": False,
            }
        )
        return checks

    checks.append(
        {
            "field": "line_item_count",
            "expected": len(expected_items),
            "actual": len(actual_items),
            "passed": True,
        }
    )

    for index, expected_row in enumerate(expected_items):
        actual_row = actual_items[index]
        for field_name, expected_value in expected_row.items():
            actual_value = actual_row.get(field_name)
            checks.append(
                {
                    "field": f"line_items[{index}].{field_name}",
                    "expected": expected_value,
                    "actual": actual_value,
                    "passed": _compare_value(expected_value, actual_value),
                }
            )

    return checks


def _empty_supplier_summary(name):
    return {
        "supplier": name,
        "documents": 0,
        "passed_documents": 0,
        "field_checks": 0,
        "passed_field_checks": 0,
        "line_item_checks": 0,
        "passed_line_item_checks": 0,
    }


def _field_bucket(summary, check):
    field_name = check["field"]
    bucket = summary["field_summary"].setdefault(
        field_name,
        {"checks": 0, "passed": 0},
    )
    bucket["checks"] += 1
    if check["passed"]:
        bucket["passed"] += 1


def evaluate_dataset(dataset_path):
    dataset_path = Path(dataset_path)
    data = json.loads(dataset_path.read_text())

    document_results = []
    summary = {
        "dataset": str(dataset_path),
        "documents": 0,
        "passed_documents": 0,
        "field_checks": 0,
        "passed_field_checks": 0,
        "line_item_checks": 0,
        "passed_line_item_checks": 0,
        "field_summary": {},
        "suppliers": {},
    }

    for entry in data:
        name = entry.get("name") or entry.get("file") or "unnamed"
        supplier_name = entry.get("supplier") or "unknown"
        expected_doc_type = entry.get("doc_type")
        expected_fields = entry.get("expected_fields", {})
        expected_extra_fields = entry.get("expected_extra_fields", {})
        expected_line_items = entry.get("expected_line_items", [])

        doc_type, metadata = _load_entry(entry)

        checks = []
        checks.append(
            {
                "field": "doc_type",
                "expected": expected_doc_type,
                "actual": doc_type,
                "passed": _compare_value(expected_doc_type, doc_type),
            }
        )
        checks.extend(_score_fields(expected_fields, metadata))
        checks.extend(_score_extra_fields(expected_extra_fields, metadata))

        line_item_checks = _score_line_items(expected_line_items, metadata)

        all_checks = checks + line_item_checks
        passed = all(item["passed"] for item in all_checks)

        summary["documents"] += 1
        if passed:
            summary["passed_documents"] += 1

        supplier_bucket = summary["suppliers"].setdefault(supplier_name, _empty_supplier_summary(supplier_name))
        supplier_bucket["documents"] += 1
        if passed:
            supplier_bucket["passed_documents"] += 1

        for check in checks:
            summary["field_checks"] += 1
            supplier_bucket["field_checks"] += 1
            if check["passed"]:
                summary["passed_field_checks"] += 1
                supplier_bucket["passed_field_checks"] += 1
            _field_bucket(summary, check)

        for check in line_item_checks:
            summary["line_item_checks"] += 1
            supplier_bucket["line_item_checks"] += 1
            if check["passed"]:
                summary["passed_line_item_checks"] += 1
                supplier_bucket["passed_line_item_checks"] += 1
            _field_bucket(summary, check)

        document_results.append(
            {
                "name": name,
                "supplier": supplier_name,
                "passed": passed,
                "checks": all_checks,
                "missing_fields": metadata.get("extraction", {}).get("missing_fields", []),
                "line_item_count": metadata.get("line_item_count", 0),
                "metadata_preview": {
                    "doc_type": metadata.get("doc_type"),
                    "doc_number": metadata.get("doc_number"),
                    "supplier_name": metadata.get("supplier_name"),
                    "buyer_name": metadata.get("buyer_name"),
                    "amount": metadata.get("amount"),
                    "part_number": metadata.get("part_number"),
                    "revision": metadata.get("revision"),
                },
            }
        )

    summary["document_accuracy"] = 0.0
    if summary["documents"]:
        summary["document_accuracy"] = round(summary["passed_documents"] / summary["documents"], 4)

    summary["field_accuracy"] = 0.0
    if summary["field_checks"]:
        summary["field_accuracy"] = round(summary["passed_field_checks"] / summary["field_checks"], 4)

    summary["line_item_accuracy"] = 0.0
    if summary["line_item_checks"]:
        summary["line_item_accuracy"] = round(summary["passed_line_item_checks"] / summary["line_item_checks"], 4)

    for supplier_name, bucket in summary["suppliers"].items():
        bucket["document_accuracy"] = 0.0
        if bucket["documents"]:
            bucket["document_accuracy"] = round(bucket["passed_documents"] / bucket["documents"], 4)

        bucket["field_accuracy"] = 0.0
        if bucket["field_checks"]:
            bucket["field_accuracy"] = round(bucket["passed_field_checks"] / bucket["field_checks"], 4)

        bucket["line_item_accuracy"] = 0.0
        if bucket["line_item_checks"]:
            bucket["line_item_accuracy"] = round(bucket["passed_line_item_checks"] / bucket["line_item_checks"], 4)

    return {
        "summary": summary,
        "documents": document_results,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate extraction against a dataset")
    parser.add_argument("dataset")
    args = parser.parse_args()
    print(json.dumps(evaluate_dataset(args.dataset), indent=2, default=str))
