from __future__ import annotations

import unittest

from moneytrace.llm import _clean_brief, _strip_unsupported_claims
from moneytrace.render import bp, md_table, pct, ratio, usd


class SanitizerTests(unittest.TestCase):
    def test_cuts_unsupported_superlative_keeps_data(self):
        out = _strip_unsupported_claims(
            "NVDA fell 4.3% on 4.9x normal volume, its worst day in a year (4th percentile)."
        )
        self.assertIn("4.3%", out)
        self.assertNotIn("worst", out.lower())
        self.assertIn("4th percentile", out)

    def test_removes_record_clause(self):
        out = _strip_unsupported_claims("AVGO jumped 5.5% on $10.1B, a record day for the stock, and closed near highs.")
        self.assertNotIn("record", out.lower())
        self.assertIn("5.5%", out)

    def test_leaves_supported_sentences_alone(self):
        text = "Small caps dropped 1.6%, 8th percentile, with $4.9B outflow."
        self.assertEqual(_strip_unsupported_claims(text), text)

    def test_drops_sentence_with_no_facts_after_cut(self):
        self.assertEqual(_strip_unsupported_claims("Broadcom had its highest volume since March."), "")

    def test_empty_and_none_safe(self):
        self.assertEqual(_strip_unsupported_claims(""), "")


class CleanBriefTests(unittest.TestCase):
    def test_keeps_lists_as_lists_and_names_intact(self):
        raw = {
            "headline": "NVDA -4.3%",
            "tldr": ["a 1% move"],
            "where_money_moved": [
                {"direction": "in", "theme": "AI power", "evidence": "GRID drew +$322M.", "vehicles": ["GRID", "NLR"]}
            ],
            "who_is_driving": [{"name": "NVDA", "why": "48.5% of the move."}],
            "key_tech": [{"tech": "Quantum", "signal": "IONQ -9.4%.", "tickers": ["QTUM"]}],
            "stocks": [{"ticker": "AMD", "note": "+5.9% on 2.2x."}],
        }
        brief = _clean_brief(raw)
        assert brief is not None
        self.assertEqual(brief["where_money_moved"][0]["vehicles"], ["GRID", "NLR"])
        self.assertEqual(brief["who_is_driving"][0]["name"], "NVDA")
        self.assertEqual(brief["stocks"][0]["ticker"], "AMD")

    def test_short_identifiers_are_not_stripped(self):
        brief = _clean_brief({"headline": "x 1%", "key_tech": [{"tech": "AI", "signal": "SMH +2%.", "tickers": ["SMH"]}]})
        assert brief is not None
        self.assertEqual(brief["key_tech"][0]["tech"], "AI")

    def test_rejects_empty(self):
        self.assertIsNone(_clean_brief({}))
        self.assertIsNone(_clean_brief(None))
        self.assertIsNone(_clean_brief({"headline": "", "tldr": []}))


class FormatTests(unittest.TestCase):
    def test_pct(self):
        self.assertEqual(pct(0.0123), "+1.23%")
        self.assertEqual(pct(-0.0123), "-1.23%")
        self.assertEqual(pct(None), "-")

    def test_usd_scales(self):
        self.assertEqual(usd(1.93e10), "+$19.30B")
        self.assertEqual(usd(-4.33e9), "-$4.33B")
        self.assertEqual(usd(613.09e6), "+$613.1M")

    def test_bp_and_ratio(self):
        self.assertEqual(bp(10.4), "+10bp")
        self.assertEqual(bp(None), "-")
        self.assertEqual(ratio(2.21), "2.2x")

    def test_table_right_aligns_numbers(self):
        table = md_table(["Ticker", "Flow"], [["AMD", "+$19.30B"]], aligns=["l", "r"])
        header, sep, row = table.splitlines()
        self.assertTrue(sep.split("|")[2].strip().endswith(":"))
        self.assertTrue(row.endswith("|"))


if __name__ == "__main__":
    unittest.main()
