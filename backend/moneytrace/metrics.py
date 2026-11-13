"""Metric engine: returns, participation, money-flow proxies and positioning.

`flow1` is Money Trace's own estimate of net dollar pressure for one session:

    agreement  = 0.5 * close_position_in_range + 0.5 * sign(return)      # -1 .. +1
    conviction = min(1, |return| / ATR%)                                  # 0 .. 1
    flow       = dollar_volume * agreement * conviction

All three have to line up before a day counts as real inflow: price closed up, closed
near the high of its range, and the move was large relative to that instrument's own
normal range. A flat day, or a gap-down that closes on the high, nets out near zero
instead of producing a fake billion-dollar "inflow".

This is a proxy built from price and volume. It is not ETF creation/redemption data,
not 13F positioning, and not a measure of net cash entering a security -- every trade
has a buyer and a seller. The report labels it accordingly.
"""

from __future__ import annotations

import statistics
from typing import Sequence

from .config import Instrument
from .sources import Series


def _div(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return a / b


def pct_return(vals: Sequence[float], n: int) -> float | None:
    if len(vals) <= n:
        return None
    prev, last = vals[-1 - n], vals[-1]
    if not prev:
        return None
    return last / prev - 1.0


def median(vals: Sequence[float]) -> float | None:
    vals = [v for v in vals if v]
    return statistics.median(vals) if vals else None


def stdev(vals: Sequence[float]) -> float | None:
    clean = [v for v in vals if v is not None]
    return statistics.pstdev(clean) if len(clean) > 2 else None


def _atr_frac(s: Series, n: int = 14) -> float | None:
    """Average true range as a fraction of price: 'how much does this normally move?'"""
    if len(s) < n + 1:
        return None
    trs = []
    for i in range(len(s) - n, len(s)):
        h, l, pc = s.high[i], s.low[i], s.close[i - 1]
        if None in (h, l, pc):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if not trs or not s.close[-1]:
        return None
    return (sum(trs) / len(trs)) / s.close[-1]


def _cmf(s: Series, n: int = 20) -> float | None:
    """Standard 20-day Chaikin Money Flow, kept as a separate accumulation gauge."""
    if len(s) < n + 1:
        return None
    num = den = 0.0
    for i in range(len(s) - n, len(s)):
        h, l, c, v = s.high[i], s.low[i], s.close[i], s.volume[i]
        if None in (h, l, c) or not v:
            continue
        mult = ((c - l) - (h - c)) / (h - l) if h > l else 0.0
        num += mult * v
        den += v
    return _div(num, den)


def _zscore_last(rets: list[float]) -> float | None:
    if len(rets) < 20:
        return None
    hist = rets[-61:-1]
    sd = stdev(hist)
    if not sd:
        return None
    return (rets[-1] - statistics.mean(hist)) / sd


def _pct_rank(history: list[float], value: float) -> float:
    if not history:
        return 50.0
    return 100.0 * sum(1 for h in history if h <= value) / len(history)


def _dollar_volume(kind: str, close: float, volume: float) -> float:
    """Yahoo reports crypto volume in USD terms already; everything else is in shares."""
    if not volume:
        return 0.0
    return float(volume) if kind == "crypto" else close * volume


def _day_flow(dv: float, close: float, high: float, low: float, ret: float, atr_frac: float) -> float | None:
    if not dv or not close or high is None or low is None:
        return None
    if high > low:
        close_pos = (2.0 * (close - low) / (high - low)) - 1.0  # -1 (at low) .. +1 (at high)
    else:
        close_pos = 0.0
    direction = 1.0 if ret > 0 else (-1.0 if ret < 0 else 0.0)
    agreement = 0.5 * close_pos + 0.5 * direction
    conviction = min(1.0, abs(ret) / atr_frac) if atr_frac and atr_frac > 1e-5 else min(1.0, abs(ret) * 40)
    return dv * agreement * conviction


def compute_row(inst: Instrument, s: Series) -> dict:
    """One row of the daily snapshot."""
    adj = s.adj or s.close
    close = s.close[-1]
    volume = s.volume[-1] or 0.0
    dv = _dollar_volume(inst.kind, close, volume)
    atr_frac = _atr_frac(s)

    rets1 = [(adj[i] / adj[i - 1] - 1.0) for i in range(1, len(adj)) if adj[i - 1] and adj[i] is not None]
    row: dict = {
        "symbol": inst.symbol,
        "name": inst.name,
        "group": inst.group,
        "kind": inst.kind,
        "as_of": s.last_date,
        "close": round(close, 4),
        "n_bars": len(s),
        "atr_pct": round(atr_frac * 100, 3) if atr_frac else None,
    }

    if inst.kind == "rate":
        prev = adj[-2] if len(adj) > 1 else None
        row["level"] = round(close, 3)
        row["chg_bps"] = round((close - prev) * 100, 1) if prev is not None else None
        # yields move in basis points, not percent of themselves
        row["chg_bps_5"] = round((close - adj[-6]) * 100, 1) if len(adj) > 5 else None
        row["chg_bps_20"] = round((close - adj[-21]) * 100, 1) if len(adj) > 20 else None
        row["chg_pct"] = None
    else:
        row["chg_pct"] = round(rets1[-1], 6) if rets1 else None
        row["chg_bps"] = None

    row["ret1"] = round(rets1[-1], 6) if rets1 else None
    row["ret5"] = round(r, 6) if (r := pct_return(adj, 5)) is not None else None
    row["ret20"] = round(r, 6) if (r := pct_return(adj, 20)) is not None else None
    row["ret60"] = round(r, 6) if (r := pct_return(adj, 60)) is not None else None

    row["dv"] = round(dv, 2) if dv else None
    med = median(
        [
            _dollar_volume(inst.kind, s.close[i], s.volume[i] or 0)
            for i in range(max(0, len(s) - 21), len(s) - 1)
        ]
    )
    row["dv_med20"] = round(med, 2) if med else None
    row["rvol"] = round(_div(dv, med), 3) if (dv and med) else None

    # close position inside the day's range (0 = low, 1 = high)
    if s.high[-1] is not None and s.low[-1] is not None and s.high[-1] > s.low[-1]:
        row["cpr"] = round((close - s.low[-1]) / (s.high[-1] - s.low[-1]), 3)

    # daily flow estimate plus 5/20-session accumulation
    daily: list[float | None] = []
    for i in range(max(1, len(s) - 20), len(s)):
        ret_i = (s.close[i] / s.close[i - 1] - 1.0) if s.close[i - 1] else 0.0
        dv_i = _dollar_volume(inst.kind, s.close[i], s.volume[i] or 0.0)
        daily.append(_day_flow(dv_i, s.close[i], s.high[i], s.low[i], ret_i, atr_frac or 0.0))
    clean_daily = [f for f in daily if f is not None]
    row["flow1"] = round(clean_daily[-1], 2) if clean_daily else None
    row["flow5"] = round(sum(clean_daily[-5:]), 2) if clean_daily else None
    row["flow20"] = round(sum(clean_daily), 2) if clean_daily else None
    row["cmf20"] = round(_cmf(s), 4) if _cmf(s) is not None else None

    row["z1"] = round(_zscore_last(rets1), 2) if rets1 and _zscore_last(rets1) is not None else None
    row["ret1_ts_rank"] = round(_pct_rank(rets1[-252:-1], rets1[-1]), 1) if len(rets1) > 30 else None

    if len(adj) > 20:
        row["above20"] = close > statistics.mean(adj[-20:])
    if len(adj) > 50:
        row["above50"] = close > statistics.mean(adj[-50:])
    if len(adj) >= 200:
        hi = max(adj[-250:])
        row["off_high"] = round(close / hi - 1.0, 6) if hi else None

    if len(adj) > 40:
        r5 = [adj[i] / adj[i - 5] - 1.0 for i in range(5, len(adj)) if adj[i - 5]]
        if len(r5) >= 30 and row["ret5"] is not None:
            row["ret5_ts_rank"] = round(_pct_rank(r5[:-1], r5[-1]), 1)
    return row


def cross_section(rows: dict[str, dict]) -> None:
    """Add cross-sectional ranks that only make sense once every row exists."""

    def rank(field: str, out: str) -> None:
        vals = [(sym, r[field]) for sym, r in rows.items() if r.get(field) is not None]
        if len(vals) < 5:
            return
        ordered = sorted(vals, key=lambda kv: kv[1])
        n = len(ordered)
        for pos, (sym, _v) in enumerate(ordered):
            rows[sym][out] = round(100.0 * pos / (n - 1), 1)

    rank("ret1", "ret1_xrank")
    rank("ret5", "ret5_xrank")
    rank("ret20", "ret20_xrank")
    rank("flow1", "flow1_xrank")
    rank("rvol", "rvol_xrank")


def relative_strength(rows: dict[str, dict], bench: str = "SPY") -> None:
    """Return spread vs the benchmark over 5 and 20 sessions (percentage points)."""
    b = rows.get(bench)
    if not b:
        return
    for row in rows.values():
        if row.get("as_of") != b.get("as_of"):
            row["rs5"] = None
            row["rs20"] = None
            continue
        row["rs5"] = (
            round((row["ret5"] - b["ret5"]) * 100, 2)
            if row.get("ret5") is not None and b.get("ret5") is not None
            else None
        )
        row["rs20"] = (
            round((row["ret20"] - b["ret20"]) * 100, 2)
            if row.get("ret20") is not None and b.get("ret20") is not None
            else None
        )
