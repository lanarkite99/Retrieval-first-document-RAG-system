from factory_rag.classifier import classify_document
from factory_rag.extraction import extract_pdf
from factory_rag.metadata import extract_metadata
from eval.ground_truth import EXTRACTION_CASES, TEXT_EXTRACTION_CASES


def _compare_case(expected, metadata):
    checks = {}
    for key, value in expected.items():
        checks[key] = metadata.get(key) == value
    return checks


def _compare_line_items(expected_items, actual_items):
    checks = {}
    if len(expected_items) != len(actual_items):
        checks["line_item_count"] = False
        return checks

    checks["line_item_count"] = True

    for index, expected in enumerate(expected_items):
        actual = actual_items[index]
        for key, value in expected.items():
            checks[f"line_item_{index + 1}:{key}"] = actual.get(key) == value

    return checks


def run_extraction_checks():
    results = []

    for case in EXTRACTION_CASES:
        extracted = extract_pdf(case["file"])
        doc_type = classify_document(extracted["full_text"])
        metadata = extract_metadata(doc_type, extracted["full_text"])

        checks = {
            "doc_type": doc_type == case["doc_type"],
            "doc_number": metadata.get("doc_number") == case["doc_number"],
            "supplier_name": metadata.get("supplier_name") == case["supplier_name"],
        }

        results.append(
            {
                "case": case["file"],
                "passed": all(checks.values()),
                "checks": checks,
            }
        )

    for case in TEXT_EXTRACTION_CASES:
        doc_type = classify_document(case["text"])
        metadata = extract_metadata(doc_type, case["text"])
        checks = _compare_case(case["expected"], metadata)

        for label, value in case.get("extra_fields", {}).items():
            checks[f"extra:{label}"] = metadata.get("extra_fields", {}).get(label) == value

        if case.get("expected_line_items"):
            line_item_checks = _compare_line_items(case["expected_line_items"], metadata.get("line_items", []))
            checks.update(line_item_checks)
            checks["line_item_count_field"] = metadata.get("line_item_count") == len(case["expected_line_items"])
            checks["has_bom_table"] = "bom_table" in metadata and bool(metadata["bom_table"].get("column_map"))

        checks["doc_type"] = doc_type == case["doc_type"]
        checks["has_extraction_block"] = "extraction" in metadata

        results.append(
            {
                "case": case["name"],
                "passed": all(checks.values()),
                "checks": checks,
            }
        )

    return results
