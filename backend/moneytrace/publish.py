"""Publishes the compact, versioned JSON API that the mobile app reads.

The generated files are committed to `docs/v1/` so GitHub serves them as a static,
read-only backend. Nothing here needs a server: the app does a plain GET.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import API_DIR, API_SESSIONS_DIR, ensure_dirs

SCHEMA = 1

DISCLAIMER = (
    "Flows are estimated from price and volume, not fund-flow data. Prices are the last "
    "available session close, not real time. Research tool, not investment advice."
)

TAPE_SYMBOLS = ("SPY", "QQQ", "IWM", "RSP", "DIA")


def _num(value, digits: int = 6):
    return None if value is None else round(float(value), digits)


def _flow(row: dict) -> dict:
    return {
        "symbol": row["symbol"],
        "name": row["name"],
        "group": row["group"],
        "chg": _num(row.get("ret1")),
        "flow": _num(row.get("flow1"), 2),
        "rvol": _num(row.get("rvol"), 3),
        "chg5": _num(row.get("ret5")),
    }


def _sector(row: dict) -> dict:
    return {
        "symbol": row["symbol"],
        "name": row["name"],
        "chg": _num(row.get("ret1")),
        "chg5": _num(row.get("ret5")),
        "chg20": _num(row.get("ret20")),
        "flow": _num(row.get("flow1"), 2),
        "flow5": _num(row.get("flow5"), 2),
        "rvol": _num(row.get("rvol"), 3),
        "rs5": _num(row.get("rs5"), 2),
        "quadrant": row.get("quadrant"),
    }


def _driver(row: dict) -> dict:
    return {
        "symbol": row["symbol"],
        "name": row["name"],
        "group": row["group"],
        "chg": _num(row.get("ret1")),
        "share": _num(row.get("share"), 2),
        "weight": _num(row.get("weight"), 5),
        "flow": _num(row.get("flow1"), 2),
        "rvol": _num(row.get("rvol"), 3),
    }


def _stack(row: dict) -> dict:
    return {
        "label": row["label"],
        "chg": _num(row.get("ret1")),
        "chg5": _num(row.get("ret5")),
        "flow": _num(row.get("flow1"), 2),
        "breadth": row.get("breadth_up"),
        "tickers": list(row.get("tickers") or [])[:8],
        "leader": row.get("leader"),
        "laggard": row.get("laggard"),
    }


def _macro(row: dict) -> dict:
    is_rate = row["kind"] == "rate"
    return {
        "symbol": row["symbol"],
        "name": row["name"],
        "kind": row["kind"],
        "level": _num(row.get("level") if is_rate else row.get("close"), 4),
        "chg": None if is_rate else _num(row.get("ret1")),
        "chg5": None if is_rate else _num(row.get("ret5")),
        "chg20": None if is_rate else _num(row.get("ret20")),
        "chg_bps": _num(row.get("chg_bps"), 1) if is_rate else None,
        "chg5_bps": _num(row.get("chg_bps_5"), 1) if is_rate else None,
        "chg20_bps": _num(row.get("chg_bps_20"), 1) if is_rate else None,
    }


def _crypto(row: dict) -> dict:
    return {
        "symbol": row["symbol"],
        "name": row["name"],
        "close": _num(row.get("close"), 2),
        "chg": _num(row.get("chg_pct")),
        "chg5": _num(row.get("ret5")),
        "chg20": _num(row.get("ret20")),
        "flow": _num(row.get("flow1"), 2),
        "rvol": _num(row.get("rvol"), 3),
    }


def _tape(rows: dict) -> list[dict]:
    out = []
    for symbol in TAPE_SYMBOLS:
        row = rows.get(symbol)
        if not row:
            continue
        out.append(
            {
                "symbol": symbol,
                "name": row["name"],
                "close": _num(row.get("close"), 2),
                "chg": _num(row.get("ret1")),
                "chg5": _num(row.get("ret5")),
            }
        )
    return out


def build_api(snapshot: dict, brief: dict, meta: dict) -> dict:
    """Turn an internal snapshot into the public v1 payload."""
    rows = snapshot["rows"]
    derived = snapshot["derived"]
    session = snapshot.get("session") or {}
    date = session.get("session_date") or ""
    if not date:
        raise ValueError("snapshot has no session date; refusing to publish")

    macro_symbols = [s for s, r in rows.items() if r["group"] in ("macro", "credit")]
    crypto_symbols = [s for s, r in rows.items() if r["group"] == "crypto"]

    payload = {
        "schema": SCHEMA,
        "session": {
            "date": date,
            "status": session.get("status"),
            "timezone": session.get("timezone"),
            "generated_at": snapshot.get("generated_at"),
        },
        "headline": brief.get("headline") or "",
        "regime": derived.get("regime") or None,
        "breadth": derived.get("breadth") or None,
        "tape": _tape(rows),
        "groups": [
            {
                "group": g["group"],
                "flow": _num(g.get("flow1"), 2),
                "avg_chg": _num(g.get("avg_ret")),
                "dv": _num(g.get("dv"), 2),
            }
            for g in (derived.get("group_flows") or [])
        ],
        "flows": {
            "in": [_flow(r) for r in (derived.get("inflows") or [])],
            "out": [_flow(r) for r in (derived.get("outflows") or [])],
        },
        "sectors": [_sector(s) for s in (derived.get("sectors") or [])],
        "drivers": [_driver(c) for c in (derived.get("contributors") or [])],
        "stacks": [_stack(s) for s in (derived.get("stacks") or [])],
        "macro": [_macro(rows[s]) for s in macro_symbols],
        "crypto": [_crypto(rows[s]) for s in crypto_symbols],
        "movers": [_flow(r) for r in (derived.get("movers") or [])],
        "streaks": [
            {
                "symbol": s["symbol"],
                "name": (rows.get(s["symbol"]) or {}).get("name", s["symbol"]),
                "days": s["streak"],
                "cum": _num(s.get("cum"), 2),
            }
            for s in (derived.get("streaks") or [])
        ],
        "brief": brief,
        "meta": {
            "instruments": snapshot.get("meta", {}).get("n_symbols"),
            "history_sessions": snapshot.get("meta", {}).get("history_sessions"),
            "model": meta.get("model"),
            "cost_usd": (meta.get("usage") or {}).get("cost"),
        },
        "disclaimer": DISCLAIMER,
    }
    return payload


def _index_entry(payload: dict) -> dict:
    spy = next((t["chg"] for t in payload["tape"] if t["symbol"] == "SPY"), None)
    breadth = payload.get("breadth") or {}
    return {
        "date": payload["session"]["date"],
        "headline": payload.get("headline") or "",
        "regime": (payload.get("regime") or {}).get("tone"),
        "regime_score": (payload.get("regime") or {}).get("score"),
        "spy": spy,
        "pct_up": breadth.get("pct_up"),
    }


def publish(snapshot: dict, brief: dict, meta: dict) -> list[Path]:
    """Write latest.json, sessions/<date>.json and index.json. Returns written paths."""
    ensure_dirs()
    payload = build_api(snapshot, brief, meta)
    date = payload["session"]["date"]
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    latest_path = API_DIR / "latest.json"
    session_path = API_SESSIONS_DIR / f"{date}.json"
    latest_path.write_text(body, encoding="utf-8")
    session_path.write_text(body, encoding="utf-8")

    index_path = API_DIR / "index.json"
    index: dict = {"schema": SCHEMA, "updated_at": None, "latest": date, "sessions": []}
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and isinstance(existing.get("sessions"), list):
                index = existing
        except Exception:  # noqa: BLE001 - corrupt index is rebuildable
            pass

    sessions = {s["date"]: s for s in index.get("sessions", []) if isinstance(s, dict) and s.get("date")}
    sessions[date] = _index_entry(payload)
    index.update(
        {
            "schema": SCHEMA,
            "updated_at": payload["session"]["generated_at"],
            "latest": date,
            "sessions": sorted(sessions.values(), key=lambda s: s["date"], reverse=True),
        }
    )
    index_path.write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    return [latest_path, session_path, index_path]
