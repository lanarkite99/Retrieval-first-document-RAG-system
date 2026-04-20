import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from factory_rag.bom_tables import extract_bom_line_items  # noqa: E402


class BomTableTests(unittest.TestCase):
    def test_extracts_bom_rows_from_tabular_text(self):
        text = """
        BILL OF MATERIAL
        Part Number    Description              Qty    Unit    Rate      Amount
        KR-1001        Rear Torsion Beam        1      Nos     1049.00   1049.00
        KR-1002        Mounting Bracket         2      Nos     265.00    530.00
        Grand Total Cost: Rs. 1,579.00
        """

        result = extract_bom_line_items(text)

        self.assertEqual(result["line_item_count"], 2)
        self.assertEqual(result["line_items"][0]["part_number"], "KR-1001")
        self.assertEqual(result["line_items"][0]["description"], "Rear Torsion Beam")
        self.assertEqual(result["line_items"][0]["quantity"], 1)
        self.assertEqual(result["line_items"][1]["unit"], "Nos")
        self.assertEqual(result["column_map"]["description"], 1)

    def test_returns_empty_result_when_no_header_is_found(self):
        result = extract_bom_line_items("This document has no parseable BOM table.")

        self.assertEqual(result["line_item_count"], 0)
        self.assertEqual(result["line_items"], [])
        self.assertIsNone(result["table_header"])


if __name__ == "__main__":
    unittest.main()
