"""Turns raw per-symbol metrics into the story: where money moved, who drove it.

Everything here is deterministic and auditable; the LLM only ever writes prose on
top of these numbers, it never invents them.
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    SNAPSHOT_DIR,
    TECH_STACKS,
    UNIVERSE,
    Instrument,
)
from .metrics import compute_row, cross_section, relative_strength
from .sources import Series

EQUITY_GROUPS = {"index", "sector", "theme", "mega", "stock", "global"}
RISK_ON_BASKET = ["SPY", "IWM", "HYG", "KRE", "XLY", "BTC-USD"]
RISK_OFF_BASKET = ["TLT", "GLD", "DX-Y.NYB", "^VIX", "XLP", "XLU"]


def _usd(x: float | None) -> float:
    return float(x or 0.0)


def _top(rows: list[dict], key: str, n: int, reverse: bool = True) -> list[dict]:
    usable = [r for r in rows if r.get(key) is not None]
    return sorted(usable, key=lambda r: r[key], reverse=reverse)[:n]


def session_clock(spy_meta: dict, spy_as_of: str) -> dict:
    gmtoff = spy_meta.get("gmtoffset") or 0
    now_utc = datetime.now(timezone.utc)
    market_now = datetime.fromtimestamp(now_utc.timestamp() + gmtoff, tz=timezone.utc)
    market_today = market_now.date().isoformat()
    live = spider = False
    label = "close"
    if spy_as_of == market_today:
        live = True
        label = "intraday" if (market_now.hour, market_now.minute) < (16, 0) else "close"
    else:
        try:
            behind = (datetime.fromisoformat(market_today) - datetime.fromisoformat(spy_as_of)).days
        except ValueError:
            behind = 99
        if behind <= 3:
            label = "prior session"
        else:
            label = f"stale ({behind}d)"
    return {
        "session_date": spy_as_of,
        "status": label,
        "live": live,
        "market_now": market_now.strftime("%Y-%m-%d %H:%M"),
        "timezone": spy_meta.get("exchangeTimezoneName") or "America/New_York",
        "region": spy_meta.get("fullExchangeName") or "US",
    }


def breadth(rows: dict[str, dict], session_date: str) -> dict:
    eq = [
        r
        for r in rows.values()
        if r["group"] in EQUITY_GROUPS and r.get("ret1") is not None and r.get("as_of") == session_date
    ]
    if not eq:
        return {}
    up = [r for r in eq if r["ret1"] > 0]
    above20 = [r for r in eq if r.get("above20")]
    up_dv = sum(_usd(r.get("dv")) for r in up)
    down_dv = sum(_usd(r.get("dv")) for r in eq if r["ret1"] <= 0)
    return {
        "n": len(eq),
        "advancers": len(up),
        "decliners": len(eq) - len(up),
        "pct_up": round(100 * len(up) / len(eq), 1),
        "pct_above20": round(100 * len(above20) / len(eq), 1),
        "dollar_breadth": round(100 * up_dv / (up_dv + down_dv), 1) if (up_dv + down_dv) else None,
        "median_move": round(statistics.median([r["ret1"] for r in eq]), 5),
        "high_volume_movers": len([r for r in eq if (r.get("rvol") or 0) > 1.5]),
    }


def regime(rows: dict[str, dict]) -> dict:
    def avg_rank(symbols: list[str]) -> float | None:
        ranks = [rows[s]["ret5_ts_rank"] for s in symbols if s in rows and rows[s].get("ret5_ts_rank") is not None]
        return statistics.mean(ranks) if ranks else None

    on = avg_rank(RISK_ON_BASKET)
    off = avg_rank(RISK_OFF_BASKET)
    if on is None or off is None:
        return {}
    score = max(0.0, min(100.0, 50 + (on - off) / 2))
    tone = "risk-on" if score >= 60 else "risk-off" if score <= 40 else "mixed"
    return {
        "score": round(score, 1),
        "tone": tone,
        "risk_on_rank": round(on, 1),
        "risk_off_rank": round(off, 1),
        "components_on": {s: rows[s]["ret5_ts_rank"] for s in RISK_ON_BASKET if s in rows and rows[s].get("ret5_ts_rank") is not None},
        "components_off": {s: rows[s]["ret5_ts_rank"] for s in RISK_OFF_BASKET if s in rows and rows[s].get("ret5_ts_rank") is not None},
    }


def sectors(rows: dict[str, dict], session_date: str) -> list[dict]:
    out = []
    for r in rows.values():
        if r["group"] != "sector" or r.get("as_of") != session_date:
            continue
        r5, f5 = r.get("ret5"), r.get("flow5")
        if r5 is None or f5 is None:
            quadrant = "n/a"
        elif r5 > 0 and f5 > 0:
            quadrant = "leading"
        elif r5 > 0:
            quadrant = "fading"
        elif f5 > 0:
            quadrant = "accumulating"
        else:
            quadrant = "lagging"
        out.append(
            {
                "symbol": r["symbol"],
                "name": r["name"],
                "ret1": r.get("ret1"),
                "ret5": r5,
                "ret20": r.get("ret20"),
                "flow1": r.get("flow1"),
                "flow5": f5,
                "rvol": r.get("rvol"),
                "rs5": r.get("rs5"),
                "quadrant": quadrant,
            }
        )
    return sorted(out, key=lambda x: (x["ret1"] if x["ret1"] is not None else -9), reverse=True)


def contributors(rows: dict[str, dict], session_date: str, n: int = 12) -> list[dict]:
    """Who accounts for the session's dollar-weighted movement.

    Traded-dollar share x move, then normalised by the total absolute displacement,
    so the column reads as "share of everything that moved today" instead of
    pretending to be index points (our traded-dollar weights are much larger than
    real index weights for the biggest names).
    """
    pool = [r for r in rows.values() if r["group"] in EQUITY_GROUPS and r.get("as_of") == session_date and r.get("dv")]
    total_dv = sum(_usd(r["dv"]) for r in pool)
    if not total_dv:
        return []
    raw = []
    for r in pool:
        weight = _usd(r["dv"]) / total_dv
        displacement = weight * (r.get("ret1") or 0)
        raw.append((r, weight, displacement))
    total_abs = sum(abs(x[2]) for x in raw) or 1.0
    out = []
    for r, weight, displacement in raw:
        out.append(
            {
                "symbol": r["symbol"],
                "name": r["name"],
                "group": r["group"],
                "ret1": r.get("ret1"),
                "dv": r.get("dv"),
                "weight": round(weight, 5),
                "share": round(100 * abs(displacement) / total_abs, 1),
                "direction": "up" if (r.get("ret1") or 0) > 0 else "down",
                "flow1": r.get("flow1"),
                "rvol": r.get("rvol"),
            }
        )
    return sorted(out, key=lambda x: x["share"], reverse=True)[:n]


def group_flows(rows: dict[str, dict], session_date: str) -> list[dict]:
    out = []
    bucket: dict[str, dict] = {}
    for r in rows.values():
        if r.get("as_of") != session_date or r.get("dv") is None:
            continue
        g = r["group"]
        b = bucket.setdefault(g, {"group": g, "flow1": 0.0, "dv": 0.0, "ret": []})
        b["flow1"] += _usd(r.get("flow1"))
        b["dv"] += _usd(r.get("dv"))
        if r.get("ret1") is not None:
            b["ret"].append(r["ret1"])
    for g, b in bucket.items():
        out.append(
            {
                "group": g,
                "flow1": round(b["flow1"], 2),
                "dv": b["dv"],
                "avg_ret": round(statistics.mean(b["ret"]), 5) if b["ret"] else None,
            }
        )
    return sorted(out, key=lambda x: x["flow1"], reverse=True)


def stacks(rows: dict[str, dict], session_date: str) -> list[dict]:
    out = []
    for stack in TECH_STACKS:
        members = [rows[t] for t in stack["tickers"] if t in rows and rows[t].get("as_of") == session_date]
        if not members:
            continue
        rets = [m["ret1"] for m in members if m.get("ret1") is not None]
        flows = [m.get("flow1") for m in members if m.get("flow1") is not None]
        ranked = sorted(
            [m for m in members if m.get("ret1") is not None], key=lambda m: m["ret1"], reverse=True
        )
        out.append(
            {
                "label": stack["label"],
                "note": stack["note"],
                "tickers": [m["symbol"] for m in members],
                "ret1": round(statistics.mean(rets), 5) if rets else None,
                "ret5": round(statistics.mean([m["ret5"] for m in members if m.get("ret5") is not None]), 5)
                if any(m.get("ret5") is not None for m in members)
                else None,
                "flow1": round(sum(flows), 2) if flows else None,
                "max_rvol": max([m.get("rvol") or 0 for m in members]) or None,
                "leader": {"symbol": ranked[0]["symbol"], "ret1": ranked[0]["ret1"]} if ranked else None,
                "laggard": {"symbol": ranked[-1]["symbol"], "ret1": ranked[-1]["ret1"]}
                if len(ranked) > 1
                else None,
                "breadth_up": round(100 * len([m for m in members if (m.get("ret1") or 0) > 0]) / len(members), 0),
            }
        )
    return sorted(out, key=lambda x: (x["flow1"] if x["flow1"] is not None else -9e18), reverse=True)


def previous_snapshots(limit: int = 12, exclude: str | None = None) -> list[dict]:
    files = sorted(SNAPSHOT_DIR.glob("*.json"))
    out = []
    for path in files:
        if exclude and path.stem == exclude:
            continue
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return out[-limit:]


def history_stats(rows: dict[str, dict], snapshots: list[dict], session_date: str) -> dict:
    """Multi-session flow persistence: streaks, cumulative flow, reversals."""
    if not snapshots:
        return {"streaks": [], "cum": {}, "reversals": [], "sessions": 1}

    per_symbol: dict[str, list[tuple[str, float]]] = {}
    for snap in snapshots:
        for sym, row in (snap.get("rows") or {}).items():
            if row.get("flow1") is None:
                continue
            per_symbol.setdefault(sym, []).append((row.get("as_of", ""), row["flow1"]))
    for sym, row in rows.items():
        if row.get("flow1") is None:
            continue
        seq = per_symbol.setdefault(sym, [])
        if not seq or seq[-1][0] != row["as_of"]:
            seq.append((row["as_of"], row["flow1"]))

    streaks, cum = [], {}
    for sym, seq in per_symbol.items():
        values = [v for _d, v in seq]
        if not values:
            continue
        cum[sym] = {"cum5": round(sum(values[-5:]), 2), "cum20": round(sum(values[-20:]), 2), "n": len(values)}
        sign = math.copysign(1, values[-1]) if values[-1] else 0
        streak = 0
        for v in reversed(values):
            if not v or math.copysign(1, v) != sign:
                break
            streak += 1
        if streak >= 2:
            streaks.append({"symbol": sym, "streak": streak * int(sign), "cum": round(sum(values[-abs(streak):]), 2)})

    reversals = []
    for sym, row in rows.items():
        seq = per_symbol.get(sym) or []
        if len(seq) < 2 or row.get("flow1") is None or row.get("dv") is None:
            continue
        prev = seq[-2][1]
        today = row["flow1"]
        if prev and today and math.copysign(1, prev) != math.copysign(1, today):
            size = abs(today) / max(1.0, abs(prev))
            if size > 0.8 and abs(today) > 0.1 * row["dv"]:
                reversals.append(
                    {
                        "symbol": sym,
                        "today": round(today, 2),
                        "prev": round(prev, 2),
                        "direction": "in" if today > 0 else "out",
                    }
                )

    streaks.sort(key=lambda x: abs(x["cum"]), reverse=True)
    reversals.sort(key=lambda x: abs(x["today"]), reverse=True)
    return {
        "streaks": streaks[:12],
        "cum": cum,
        "reversals": reversals[:8],
        "sessions": len(snapshots) + 1,
    }


def build_snapshot(
    series: dict[str, Series],
    instruments: list[Instrument],
    errors: dict[str, str],
    generated_at: datetime | None = None,
) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc)
    rows: dict[str, dict] = {}
    for inst in instruments:
        s = series.get(inst.symbol)
        if not s or len(s) < 25:
            continue
        try:
            rows[inst.symbol] = compute_row(inst, s)
        except Exception as exc:  # noqa: BLE001
            errors[inst.symbol] = f"metrics: {exc}"
    cross_section(rows)
    relative_strength(rows)

    spy = rows.get("SPY") or {}
    spy_series = series.get("SPY")
    session_date = spy.get("as_of") or ""
    clock = session_clock(spy_series.meta if spy_series else {}, session_date) if spy else {}

    prior = previous_snapshots(exclude=session_date)
    hist = history_stats(rows, prior, session_date)

    eq_rows = [r for r in rows.values() if r["group"] in EQUITY_GROUPS and r.get("as_of") == session_date]
    flows = _top([r for r in eq_rows if r.get("flow1") is not None], "flow1", 10)
    outflows = _top([r for r in eq_rows if r.get("flow1") is not None], "flow1", 10, reverse=False)

    movers = [
        r
        for r in eq_rows
        if r.get("ret1") is not None and abs(r["ret1"]) >= 0.02 and (r.get("rvol") or 0) >= 1.2
    ]
    movers = sorted(movers, key=lambda r: abs(r["ret1"]), reverse=True)[:14]

    snapshot = {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "session": clock,
        "meta": {
            "n_symbols": len(rows),
            "n_requested": len(instruments),
            "errors": errors,
            "history_sessions": hist.get("sessions", 1),
        },
        "rows": rows,
        "derived": {
            "breadth": breadth(rows, session_date),
            "regime": regime(rows),
            "sectors": sectors(rows, session_date),
            "contributors": contributors(rows, session_date),
            "group_flows": group_flows(rows, session_date),
            "stacks": stacks(rows, session_date),
            "inflows": flows,
            "outflows": outflows,
            "movers": movers,
            "streaks": hist["streaks"],
            "reversals": hist["reversals"],
            "cum_flow": hist["cum"],
        },
    }
    return snapshot


def save_snapshot(snapshot: dict) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    date = snapshot["session"].get("session_date") or datetime.now(timezone.utc).date().isoformat()
    path = SNAPSHOT_DIR / f"{date}.json"
    path.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    return path
