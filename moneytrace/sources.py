"""Price/volume ingestion with an on-disk cache and a Stooq fallback.

Source of record is Yahoo Finance's public chart endpoint (no key, no crumb needed
for `chart`). Everything is cached so a re-run inside the TTL costs zero requests.
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from .config import CACHE_DIR, CACHE_TTL_SECONDS, Instrument, ensure_dirs

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
STOOQ = "https://stooq.com/q/d/l/?s={sym}&i=d"


@dataclass
class Series:
    symbol: str
    dates: list[str] = field(default_factory=list)
    open: list[float] = field(default_factory=list)
    high: list[float] = field(default_factory=list)
    low: list[float] = field(default_factory=list)
    close: list[float] = field(default_factory=list)
    adj: list[float] = field(default_factory=list)
    volume: list[float] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    source: str = "yahoo"

    def __len__(self) -> int:
        return len(self.close)

    @property
    def last_date(self) -> str:
        return self.dates[-1] if self.dates else ""


def _http_get(url: str, timeout: float = 25.0, retries: int = 3) -> bytes:
    headers = {"User-Agent": UA, "Accept": "*/*", "Connection": "close"}
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:  # 404 = dead symbol, do not retry
            if exc.code in (400, 401, 403, 404):
                raise
            last = exc
        except Exception as exc:  # noqa: BLE001 - network layer, retry everything
            last = exc
        time.sleep(0.6 * (attempt + 1) + random.random() * 0.3)
    raise last if last else RuntimeError("request failed")


def _cache_path(symbol: str) -> "object":
    slug = "".join(ch if ch.isalnum() else "_" for ch in symbol)
    return CACHE_DIR / f"{slug}.json"


def _read_cache(symbol: str, ttl: float) -> dict | None:
    path = _cache_path(symbol)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if time.time() - payload.get("_fetched_at", 0) > ttl:
        return None
    return payload


def _write_cache(symbol: str, payload: dict) -> None:
    ensure_dirs()
    payload = dict(payload)
    payload["_fetched_at"] = time.time()
    try:
        _cache_path(symbol).write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def _clean(series: Series) -> Series:
    """Drop bars without a usable close, dedupe dates, keep chronological order."""
    rows = list(
        zip(series.dates, series.open, series.high, series.low, series.close, series.adj, series.volume)
    )
    rows = [r for r in rows if r[4] is not None and r[4] > 0]
    rows.sort(key=lambda r: r[0])
    seen: dict[str, tuple] = {}
    for r in rows:
        seen[r[0]] = r
    rows = [seen[d] for d in sorted(seen)]
    series.dates = [r[0] for r in rows]
    series.open = [r[1] for r in rows]
    series.high = [r[2] for r in rows]
    series.low = [r[3] for r in rows]
    series.close = [r[4] for r in rows]
    series.adj = [r[5] if r[5] else r[4] for r in rows]
    series.volume = [r[6] or 0.0 for r in rows]
    return series


def _from_yahoo_payload(symbol: str, payload: dict) -> Series:
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError(f"no chart result for {symbol}")
    res = result[0]
    ts = res.get("timestamp") or []
    quote = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    adj_block = ((res.get("indicators") or {}).get("adjclose") or [{}])[0]
    adj = adj_block.get("adjclose") or []
    closes = quote.get("close") or []
    s = Series(
        symbol=symbol,
        dates=[datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat() for t in ts],
        open=quote.get("open") or [],
        high=quote.get("high") or [],
        low=quote.get("low") or [],
        close=closes,
        adj=adj if len(adj) == len(closes) else list(closes),
        volume=quote.get("volume") or [],
        meta=res.get("meta") or {},
        source="yahoo",
    )
    return _clean(s)


def fetch_yahoo(symbol: str, range_: str = "1y", interval: str = "1d") -> Series:
    url = YAHOO_CHART.format(sym=urllib.parse.quote(symbol)) + f"?range={range_}&interval={interval}&includePrePost=false"
    raw = _http_get(url)
    payload = json.loads(raw.decode("utf-8", errors="replace"))
    return _from_yahoo_payload(symbol, payload)


def fetch_stooq(symbol: str) -> Series:
    """CSV fallback: Date,Open,High,Low,Close,Volume."""
    url = STOOQ.format(sym=(symbol.lower().replace("-", "") + ".us") if symbol.endswith("-USD") else (symbol.lower() + ".us"))
    text = _http_get(url, timeout=25).decode("utf-8", errors="replace")
    lines = [ln for ln in text.strip().splitlines() if ln and not ln.lower().startswith("date")]
    if len(lines) < 30:
        raise ValueError(f"stooq returned {len(lines)} rows for {symbol}")
    s = Series(symbol=symbol, source="stooq")
    for ln in lines[-500:]:
        parts = ln.split(",")
        if len(parts) < 6:
            continue
        try:
            d, o, h, l, c, v = parts[0], float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])
        except ValueError:
            continue
        s.dates.append(d)
        s.open.append(o)
        s.high.append(h)
        s.low.append(l)
        s.close.append(c)
        s.adj.append(c)
        s.volume.append(v)
    return _clean(s)


def fetch_one(inst: Instrument, force: bool = False, ttl: float = CACHE_TTL_SECONDS) -> Series:
    symbol = inst.symbol
    if not force:
        cached = _read_cache(symbol, ttl)
        if cached and cached.get("payload"):
            try:
                return _from_yahoo_payload(symbol, cached["payload"])
            except Exception:  # noqa: BLE001 - corrupt cache, refetch
                pass
    errors = []
    for fetch in (fetch_yahoo,):
        try:
            series = fetch(symbol)
            _write_cache(symbol, {"payload": _to_payload(series)})
            return series
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{fetch.__name__}: {exc}")
    if inst.kind in ("etf", "stock"):
        try:
            series = fetch_stooq(symbol)
            return series
        except Exception as exc:  # noqa: BLE001
            errors.append(f"stooq: {exc}")
    raise RuntimeError("; ".join(errors))


def _to_payload(series: Series) -> dict:
    """Round-trip a Series through the Yahoo shape so the cache has one format."""
    quote = {
        "open": series.open,
        "high": series.high,
        "low": series.low,
        "close": series.close,
        "volume": series.volume,
    }
    return {
        "chart": {
            "result": [
                {
                    "meta": series.meta,
                    "timestamp": [
                        int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp()) for d in series.dates
                    ],
                    "indicators": {"quote": [quote], "adjclose": [{"adjclose": series.adj}]},
                }
            ],
            "error": None,
        }
    }


def fetch_universe(
    instruments: Iterable[Instrument], force: bool = False, workers: int = 6, ttl: float = CACHE_TTL_SECONDS
) -> tuple[dict[str, Series], dict[str, str]]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    insts = list(instruments)
    series: dict[str, Series] = {}
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_one, inst, force, ttl): inst for inst in insts}
        for fut in as_completed(futures):
            inst = futures[fut]
            try:
                series[inst.symbol] = fut.result()
            except Exception as exc:  # noqa: BLE001
                errors[inst.symbol] = str(exc)[:200]
    return series, errors
