from __future__ import annotations

import unittest

from moneytrace.metrics import compute_row
from tests.helpers import inst, make_series


class ReturnTests(unittest.TestCase):
    def test_simple_return(self):
        s = make_series("T", [100.0] * 30 + [110.0])
        row = compute_row(inst("T"), s)
        self.assertAlmostEqual(row["ret1"], 0.1, places=6)
        self.assertAlmostEqual(row["ret5"], 0.1, places=6)

    def test_dollar_volume_and_rvol(self):
        volumes = [1_000_000.0] * 40 + [2_000_000.0]
        s = make_series("T", [100.0] * 41, volumes=volumes)
        row = compute_row(inst("T"), s)
        self.assertAlmostEqual(row["dv"], 2e8, delta=1.0)
        self.assertAlmostEqual(row["rvol"], 2.0, places=2)


class FlowTests(unittest.TestCase):
    def test_strong_up_close_is_inflow(self):
        closes = [100.0] * 40 + [110.0]
        highs = [101.0] * 40 + [111.0]
        lows = [99.0] * 40 + [100.0]
        row = compute_row(inst("T"), make_series("T", closes, highs=highs, lows=lows))
        self.assertGreater(row["flow1"], 0)
        self.assertLessEqual(abs(row["flow1"]), row["dv"])  # never bigger than the dollars traded

    def test_flat_day_is_near_zero(self):
        closes = [100.0] * 40 + [100.0]
        highs = [100.5] * 40 + [100.5]
        lows = [99.5] * 40 + [99.5]
        row = compute_row(inst("T"), make_series("T", closes, highs=highs, lows=lows))
        self.assertLess(abs(row["flow1"]), 0.02 * row["dv"])

    def test_gap_down_recovery_is_not_an_inflow(self):
        """Down 0.5% but closed at the top of the range: the old Chaikin proxy screamed +$B inflow."""
        closes = [100.0] * 40 + [99.5]
        highs = [101.0] * 40 + [100.0]
        lows = [99.0] * 40 + [95.0]
        row = compute_row(inst("T"), make_series("T", closes, highs=highs, lows=lows))
        self.assertLess(abs(row["flow1"]), 0.05 * row["dv"])

    def test_crypto_volume_is_already_dollars(self):
        s = make_series("BTC-USD", [68000.0] * 40 + [68000.0], volumes=[3.5e10] * 41)
        row = compute_row(inst("BTC-USD", kind="crypto", group="crypto"), s)
        self.assertAlmostEqual(row["dv"], 3.5e10, delta=1e6)

    def test_rate_moves_in_basis_points(self):
        s = make_series("^TNX", [4.0] * 40 + [4.1], volumes=[0.0] * 41)
        row = compute_row(inst("^TNX", kind="rate", group="macro"), s)
        self.assertAlmostEqual(row["chg_bps"], 10.0, places=2)
        self.assertIsNone(row["chg_pct"])
        self.assertIsNone(row["flow1"])  # no volume, no flow

    def test_short_history_does_not_crash(self):
        row = compute_row(inst("T"), make_series("T", [100.0, 101.0, 102.0]))
        self.assertAlmostEqual(row["ret1"], 102 / 101 - 1, places=6)
        self.assertIsNone(row["atr_pct"])  # needs 15 bars


if __name__ == "__main__":
    unittest.main()
