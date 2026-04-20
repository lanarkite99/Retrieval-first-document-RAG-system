import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from factory_rag.router import QueryRouter  # noqa: E402


class QueryRouterTests(unittest.TestCase):
    def setUp(self):
        self.router = QueryRouter()

    def test_generic_identifier_query_uses_exact_match_route(self):
        plan = self.router.route("FM-GST-2026-2001")

        self.assertEqual(plan["route"], "exact_match")
        self.assertEqual(plan["identifier"], "FM-GST-2026-2001")
        self.assertFalse(plan["use_semantic"])

    def test_row_level_query_stays_lexical(self):
        plan = self.router.route("find me material code for Seat Foam Cushion")

        self.assertEqual(plan["route"], "lexical")
        self.assertTrue(plan["row_query"])
        self.assertFalse(plan["use_semantic"])

    def test_broad_semantic_query_uses_hybrid_route(self):
        plan = self.router.route("registered office for RIL")

        self.assertEqual(plan["route"], "hybrid")
        self.assertTrue(plan["use_semantic"])


if __name__ == "__main__":
    unittest.main()
