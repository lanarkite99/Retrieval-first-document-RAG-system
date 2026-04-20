import sys
import unittest
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from factory_rag.processing.metadata import (  # noqa: E402
    _is_table_header_line,
    _parse_date,
    extract_query_filters,
)


class MetadataTests(unittest.TestCase):
    def test_parse_date_accepts_hyphenated_month_format(self):
        self.assertEqual(_parse_date("10-Apr-2026"), date(2026, 4, 10))

    def test_generic_doc_number_is_extracted_from_query(self):
        filters = extract_query_filters("vehicle number for e-way bill FM-GST-2026-2001")
        self.assertEqual(filters["doc_number"], "FM-GST-2026-2001")

    def test_row_query_does_not_force_total_amount_filter(self):
        filters = extract_query_filters("which item has the rate of 85000.00?")
        self.assertNotIn("amount", filters)

    def test_explicit_total_query_extracts_amount_filter(self):
        filters = extract_query_filters("show invoice total amount 85000.00")
        self.assertEqual(filters["amount"], 85000.0)

    def test_table_header_line_detection(self):
        self.assertTrue(_is_table_header_line("Part Number Description Qty Unit Rate Amount"))
        self.assertFalse(_is_table_header_line("Buyer"))


if __name__ == "__main__":
    unittest.main()
