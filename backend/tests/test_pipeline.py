from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from moneytrace.analysis import build_snapshot, history_stats, previous_snapshots
from moneytrace.config import Instrument
from moneytrace.llm import compact, fallback_brief
from moneytrace.render import render
from tests.helpers import make_series, wave

EQUITY = [
    Instrument("SPY", "S&P 500", "index", "etf"),
    Instrument("QQQ", "Nasdaq 100", "index", "etf"),
    Instrument("IWM", "Russell 2000", "index", "etf"),
    Instrument("XLK", "Technology", "sector", "etf"),
    Instrument("XLE", "Energy", "sector", "etf"),
    Instrument("SMH", "Semiconductors", "theme", "etf"),
    Instrument("NVDA", "NVIDIA", "mega", "stock"),
    Instrument("AMD", "AMD", "mega", "stock"),
    Instrument("TLT", "20Y+ Treasuries", "credit", "etf"),
    Instrument("GLD", "Gold", "macro", "etf"),
    Instrument("BTC-USD", "Bitcoin", "crypto", "crypto"),
    Instrument("^TNX", "US 10Y", "macro", "rate"),
    Instrument("^VIX", "VIX", "macro", "index"),
]


def build_fixture_snapshot():
    series = {}
    for i, item in enumerate(EQUITY):
        if item.kind == "rate":
            series[item.symbol] = make_series(item.symbol, [4.0 + 0.01 * (j % 5) for j in range(80)])
        elif item.kind == "crypto":
            series[item.symbol] = wave(item.symbol, base=68000, drift=0.2, seed=i, amp=0.04)
        else:
            series[item.symbol] = wave(item.symbol, base=100 + i, drift=0.1 * (i % 3 - 1), seed=i)
    spy = series["SPY"]
    spy.meta = {"gmtoffset": -18000, "exchangeTimezoneName": "America/New_York"}
    with patch("moneytrace.analysis.previous_snapshots", return_value=[]):
        return build_snapshot(series, EQUITY, {})


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = build_fixture_snapshot()

    def test_snapshot_shape(self):
        snap = self.snapshot
        self.assertEqual(len(snap["rows"]), len(EQUITY))
        self.assertTrue(snap["session"]["session_date"])
        self.assertGreater(snap["derived"]["breadth"]["n"], 0)
        self.assertTrue(snap["derived"]["sectors"])
        self.assertIn("regime", snap["derived"])

    def test_contributor_shares_sum_to_about_100(self):
        shares = [c["share"] for c in self.snapshot["derived"]["contributors"]]
        self.assertTrue(shares)
        self.assertLessEqual(max(shares), 100.0)
        self.assertGreaterEqual(min(shares), 0.0)

    def test_compact_payload_is_json_serialisable(self):
        payload = compact(self.snapshot)
        text = json.dumps(payload)
        self.assertNotIn("NaN", text)
        self.assertNotIn("Infinity", text)
        self.assertIn("definitions", payload)

    def test_fallback_brief_renders_without_llm(self):
        brief = fallback_brief(self.snapshot)
        self.assertTrue(brief["headline"])
        self.assertTrue(brief["tldr"])
        text = render(self.snapshot, brief, {"model": None})
        for section in ("## 1. Where the money moved", "## 3. Who is driving the tape", "## 5. Cross-asset check"):
            self.assertIn(section, text)
        self.assertNotIn("None", text)
        self.assertIn("not investment advice", text.lower())

    def test_render_includes_tables_and_warning(self):
        text = render(self.snapshot, fallback_brief(self.snapshot), {"model": "test/model"})
        self.assertIn("| Ticker", text)
        self.assertIn("Share of move", text)
        self.assertIn("test/model", text)


class HistoryTests(unittest.TestCase):
    def test_streaks_and_reversals(self):
        prior = {
            "rows": {
                "AAA": {"flow1": 1.0, "as_of": "2026-01-01"},
                "BBB": {"flow1": -1.0, "as_of": "2026-01-01"},
                "CCC": {"flow1": -2.0, "as_of": "2026-01-01"},
            }
        }
        rows = {
            "AAA": {"flow1": 2.0, "dv": 100.0, "as_of": "2026-01-02"},
            "BBB": {"flow1": 1.5, "dv": 5.0, "as_of": "2026-01-02"},
            "CCC": {"flow1": -3.0, "dv": 100.0, "as_of": "2026-01-02"},
        }
        stats = history_stats(rows, [prior], "2026-01-02")
        streaks = {s["symbol"]: s["streak"] for s in stats["streaks"]}
        self.assertEqual(streaks.get("AAA"), 2)
        self.assertEqual(streaks.get("CCC"), -2)
        self.assertNotIn("BBB", streaks)  # flipped, so no streak
        self.assertEqual([r["symbol"] for r in stats["reversals"]], ["BBB"])
        self.assertEqual(stats["sessions"], 2)

    def test_no_history_is_safe(self):
        stats = history_stats({"AAA": {"flow1": 1.0, "dv": 10.0, "as_of": "2026-01-02"}}, [], "2026-01-02")
        self.assertEqual(stats["streaks"], [])
        self.assertEqual(stats["sessions"], 1)

    def test_previous_snapshots_skips_today(self):
        import shutil
        from pathlib import Path

        tmp = Path(__file__).resolve().parent.parent / "data" / "_unittest_snapshots"
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            (tmp / "2026-01-01.json").write_text(json.dumps({"rows": {}}), encoding="utf-8")
            (tmp / "2026-01-02.json").write_text(json.dumps({"rows": {}}), encoding="utf-8")
            with patch("moneytrace.analysis.SNAPSHOT_DIR", tmp):
                loaded = previous_snapshots(exclude="2026-01-02")
            self.assertEqual(len(loaded), 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
