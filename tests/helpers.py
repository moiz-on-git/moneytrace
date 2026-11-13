"""Synthetic fixtures so the tests never touch the network."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from moneytrace.config import Instrument
from moneytrace.sources import Series


def make_series(
    symbol: str,
    closes: list[float],
    volumes: list[float] | None = None,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    meta: dict | None = None,
) -> Series:
    n = len(closes)
    base = datetime(2025, 1, 1)
    return Series(
        symbol=symbol,
        dates=[(base + timedelta(days=i)).date().isoformat() for i in range(n)],
        open=list(closes),
        high=list(highs if highs is not None else [c * 1.01 for c in closes]),
        low=list(lows if lows is not None else [c * 0.99 for c in closes]),
        close=list(closes),
        adj=list(closes),
        volume=list(volumes if volumes is not None else [1_000_000.0] * n),
        meta=meta or {},
        source="test",
    )


def wave(symbol: str, base: float = 100.0, drift: float = 0.0, seed: int = 0, n: int = 80, amp: float = 0.03) -> Series:
    """A deterministic, mildly trending series - enough for percentiles and ranks."""
    closes = [base * (1 + drift * i / n + amp * math.sin((i + seed) * 0.7)) for i in range(n)]
    return make_series(symbol, closes, volumes=[1_000_000.0 + (i % 7) * 50_000 for i in range(n)])


def inst(symbol: str, name: str = "Test", group: str = "sector", kind: str = "etf") -> Instrument:
    return Instrument(symbol, name, group, kind)
