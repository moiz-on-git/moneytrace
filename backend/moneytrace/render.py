"""Markdown rendering of the daily snapshot + brief."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import REPORT_DIR

GROUPS = {
    "index": "Indexes",
    "sector": "Sectors",
    "theme": "Themes",
    "mega": "Mega-cap tech",
    "stock": "Single stocks",
    "credit": "Credit & rates",
    "global": "Global",
    "crypto": "Crypto",
    "macro": "Macro",
}


def pct(x, digits: int = 2, sign: bool = True) -> str:
    if x is None:
        return "-"
    try:
        return f"{x*100:+.{digits}f}%" if sign else f"{x*100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def usd(x) -> str:
    if x is None:
        return "-"
    sign = "-" if x < 0 else "+"
    v = abs(float(x))
    if v >= 1e12:
        return f"{sign}${v/1e12:.2f}T"
    if v >= 1e9:
        return f"{sign}${v/1e9:.2f}B"
    if v >= 1e6:
        return f"{sign}${v/1e6:.1f}M"
    if v >= 1e3:
        return f"{sign}${v/1e3:.0f}K"
    return f"{sign}${v:.0f}"


def usd_plain(x) -> str:
    if x is None:
        return "-"
    v = abs(float(x))
    for unit, scale in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if v >= scale:
            return f"${v/scale:.2f}{unit}"
    return f"${v:.0f}"


def ratio(x) -> str:
    return f"{x:.1f}x" if isinstance(x, (int, float)) else "-"


def bp(x) -> str:
    return f"{x:+.0f}bp" if isinstance(x, (int, float)) else "-"


def move(row: dict, horizon: str) -> str:
    """Yields move in basis points; everything else in percent."""
    if row.get("kind") == "rate":
        field = {"1d": "chg_bps", "1w": "chg_bps_5", "1m": "chg_bps_20"}.get(horizon, "chg_bps")
        return bp(row.get(field))
    field = {"1d": "ret1", "1w": "ret5", "1m": "ret20"}.get(horizon, "ret1")
    return pct(row.get(field))


def num(x, digits: int = 2) -> str:
    return f"{x:.{digits}f}" if isinstance(x, (int, float)) else "-"


def _cell(text, width: int | None = None) -> str:
    text = str(text).replace("|", "/").replace("\n", " ")
    if width and len(text) > width:
        text = text[: width - 1] + "…"
    return text


def md_table(headers: list[str], rows: list[list], widths: list[int] | None = None, aligns: list[str] | None = None) -> str:
    widths = widths or [None] * len(headers)
    aligns = aligns or []
    body = [[_cell(c, widths[i] if widths else None) for i, c in enumerate(r)] for r in rows]
    all_rows = [headers] + body
    sizes = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]

    def right(i: int) -> bool:
        return i < len(aligns) and aligns[i] == "r"

    def line(r):
        cells = [str(c).rjust(sizes[i]) if right(i) else str(c).ljust(sizes[i]) for i, c in enumerate(r)]
        return "| " + " | ".join(cells) + " |"

    sep_cells = ["-" * max(3, sizes[i] - 1) + ":" if right(i) else "-" * sizes[i] for i in range(len(headers))]
    sep = "| " + " | ".join(sep_cells) + " |"
    return "\n".join([line(headers), sep] + [line(r) for r in body])


def gauge(score: float | None) -> str:
    if score is None:
        return "[????????????????????]"
    filled = int(round(score / 5))
    return "[" + "#" * filled + "-" * (20 - filled) + "]"


def _level(row: dict) -> str:
    if row.get("kind") == "rate":
        val = row.get("level")
        if val is None:
            return "-"
        bps = row.get("chg_bps")
        return f"{val:.2f}%" + (f" ({bps:+.0f}bp)" if bps is not None else "")
    close = row.get("close")
    if close is None:
        return "-"
    return f"{close:,.2f}" if close < 1000 else f"{close:,.0f}"


def render(snapshot: dict, brief: dict, meta: dict) -> str:
    rows = snapshot["rows"]
    d = snapshot["derived"]
    session = snapshot.get("session") or {}
    date = session.get("session_date", "unknown")
    breadth = d.get("breadth") or {}
    reg = d.get("regime") or {}
    generated = snapshot.get("generated_at", "")
    n = snapshot["meta"].get("n_symbols", 0)
    sessions = snapshot["meta"].get("history_sessions", 1)

    L: list[str] = []
    add = L.append

    add(f"# Money Trace - {date}")
    add("")
    add(
        f"**Session:** {session.get('status','?')} ({session.get('timezone','?')}) | "
        f"**Generated:** {generated} | **Coverage:** {n} instruments | "
        f"**History:** {sessions} session(s)"
    )
    add("")

    # ----------------------------------------------------------- signal
    if brief.get("headline"):
        add(f"> **{brief['headline'].strip()}**")
        add("")
    add("```")
    add(f"Risk appetite {gauge(reg.get('score'))} {num(reg.get('score'),0)}/100  {(reg.get('tone') or 'n/a').upper()}")
    if breadth:
        add(
            f"Breadth       {breadth.get('pct_up')}% advancing ({breadth.get('advancers')} up / {breadth.get('decliners')} down)"
            f"  |  {breadth.get('pct_above20')}% above 20d MA  |  median {pct(breadth.get('median_move'))}"
        )
    idx = [(s, rows[s]) for s in ("SPY", "QQQ", "IWM", "RSP") if s in rows]
    add("Tape          " + "  ".join(f"{s} {pct(r.get('ret1'))}" for s, r in idx))
    if "BTC-USD" in rows:
        add(f"Crypto        BTC {pct(rows['BTC-USD'].get('chg_pct'))}  |  VIX {_level(rows.get('^VIX', {}))}")
    add("```")
    add("")

    if brief.get("tldr"):
        add("**The short version**")
        add("")
        for b in brief["tldr"]:
            add(f"- {b}")
        add("")

    # ----------------------------------------------------------- 1 flows
    add("## 1. Where the money moved")
    add("")
    gf = d.get("group_flows") or []
    if gf:
        add("**Estimated net flow by asset group**")
        add("")
        add(
            md_table(
                ["Group", "Net flow (est)", "Dollar volume", "Avg move"],
                [
                    [
                        GROUPS.get(g["group"], g["group"]),
                        usd(g["flow1"]),
                        usd_plain(g["dv"]),
                        pct(g["avg_ret"]),
                    ]
                    for g in gf
                ],
                aligns=["l", "r", "r", "r"],
            )
        )
        add("")

    for title, key in (("Biggest estimated inflows", "inflows"), ("Biggest estimated outflows", "outflows")):
        items = d.get(key) or []
        if not items:
            continue
        add(f"**{title}**")
        add("")
        add(
            md_table(
                ["Ticker", "Name", "Group", "1D", "Flow (est)", "RVOL", "5D"],
                [
                    [
                        r["symbol"],
                        r["name"],
                        GROUPS.get(r["group"], r["group"]),
                        pct(r.get("ret1")),
                        usd(r.get("flow1")),
                        ratio(r.get("rvol")),
                        pct(r.get("ret5")),
                    ]
                    for r in items
                ],
                widths=[10, 24, 14, 8, 12, 6, 8],
                aligns=["l", "l", "l", "r", "r", "r", "r"],
            )
        )
        add("")

    streaks = [s for s in (d.get("streaks") or []) if rows.get(s["symbol"])]
    if streaks and sessions > 1:
        add("**Money that keeps moving the same way**")
        add("")
        add(
            md_table(
                ["Ticker", "Name", "Streak", "Cumulative flow", "5D move"],
                [
                    [
                        s["symbol"],
                        rows[s["symbol"]]["name"],
                        f"{abs(s['streak'])}d {'in' if s['streak'] > 0 else 'out'}",
                        usd(s["cum"]),
                        pct(rows[s["symbol"]].get("ret5")),
                    ]
                    for s in streaks[:8]
                ],
                widths=[10, 24, 10, 16, 8],
                aligns=["l", "l", "l", "r", "r"],
            )
        )
        add("")

    reversals = d.get("reversals") or []
    if reversals:
        add("**Flow reversals vs the prior session**")
        add("")
        for r in reversals[:6]:
            row = rows.get(r["symbol"], {})
            add(
                f"- **{r['symbol']}** ({row.get('name','')}) flipped to net {r['direction']}: "
                f"{usd(r['prev'])} -> {usd(r['today'])}, {pct(row.get('ret1'))} today."
            )
        add("")

    if brief.get("where_money_moved") and brief.get("generated_by") != "fallback-templates":
        add("**Read**")
        add("")
        for w in brief["where_money_moved"]:
            direction = (w.get("direction") or "").upper()
            tag = "IN" if direction.startswith("I") else "OUT"
            vehicles = w.get("vehicles") or ""
            if isinstance(vehicles, list):
                vehicles = ", ".join(vehicles)
            add(f"- **{tag} {w.get('theme','')}** {w.get('evidence','')} _{vehicles}_")
        add("")

    # ----------------------------------------------------------- 2 rotation
    secs = d.get("sectors") or []
    if secs:
        add("## 2. Rotation map")
        add("")
        add(
            md_table(
                ["Sector", "1D", "5D", "20D", "Flow 1D", "Flow 5D", "RVOL", "vs SPY 5D", "Quadrant"],
                [
                    [
                        s["name"],
                        pct(s.get("ret1")),
                        pct(s.get("ret5")),
                        pct(s.get("ret20")),
                        usd(s.get("flow1")),
                        usd(s.get("flow5")),
                        ratio(s.get("rvol")),
                        f"{s['rs5']:+.1f}pp" if s.get("rs5") is not None else "-",
                        s["quadrant"],
                    ]
                    for s in secs
                ],
                widths=[22, 8, 8, 8, 11, 11, 6, 10, 12],
                aligns=["l", "r", "r", "r", "r", "r", "r", "r", "l"],
            )
        )
        add("")
        leading = [s["name"] for s in secs if s["quadrant"] == "leading"][:3]
        accumulating = [s["name"] for s in secs if s["quadrant"] == "accumulating"][:3]
        lagging = [s["name"] for s in secs if s["quadrant"] == "lagging"][:3]
        add(
            f"- **Leading** (price and flow up): {', '.join(leading) if leading else 'none'}\n"
            f"- **Accumulating** (flow up, price still down): {', '.join(accumulating) if accumulating else 'none'}\n"
            f"- **Lagging** (both down): {', '.join(lagging) if lagging else 'none'}"
        )
        add("")

    # ----------------------------------------------------------- 3 drivers
    contrib = d.get("contributors") or []
    if contrib:
        add("## 3. Who is driving the tape")
        add("")
        add(
            "Share of the session's dollar-weighted movement: each name's slice of traded dollars times its "
            "move, normalised across the equity universe. This is activity share, not official index weight."
        )
        add("")
        add(
            md_table(
                ["Ticker", "Name", "1D", "Traded $ share", "Share of move", "Flow (est)", "RVOL"],
                [
                    [
                        c["symbol"],
                        c["name"],
                        pct(c.get("ret1")),
                        f"{c['weight']*100:.1f}%",
                        f"{c['share']:.1f}%",
                        usd(c.get("flow1")),
                        ratio(c.get("rvol")),
                    ]
                    for c in contrib
                ],
                widths=[10, 24, 8, 16, 15, 11, 6],
                aligns=["l", "l", "r", "r", "r", "r", "r"],
            )
        )
        add("")
        if brief.get("who_is_driving"):
            for w in brief["who_is_driving"]:
                add(f"- **{w.get('name','')}** - {w.get('why','')}")
            add("")

    # ----------------------------------------------------------- 4 tech
    stacks = d.get("stacks") or []
    if stacks:
        add("## 4. Key technologies and themes")
        add("")
        add(
            md_table(
                ["Stack", "1D", "5D", "Flow (est)", "Leader", "Laggard", "Breadth"],
                [
                    [
                        s["label"],
                        pct(s.get("ret1")),
                        pct(s.get("ret5")),
                        usd(s.get("flow1")),
                        f"{s['leader']['symbol']} {pct(s['leader']['ret1'])}" if s.get("leader") else "-",
                        f"{s['laggard']['symbol']} {pct(s['laggard']['ret1'])}" if s.get("laggard") else "-",
                        f"{int(s.get('breadth_up') or 0)}% up",
                    ]
                    for s in stacks
                ],
                widths=[24, 8, 8, 11, 16, 16, 9],
                aligns=["l", "r", "r", "r", "l", "l", "r"],
            )
        )
        add("")
        if brief.get("key_tech"):
            for t in brief["key_tech"]:
                tk = t.get("tickers")
                if isinstance(tk, list):
                    tk = ", ".join(tk)
                add(f"- **{t.get('tech','')}** - {t.get('signal','')} _{tk or ''}_")
            add("")

    # ----------------------------------------------------------- 5 cross-asset
    macro = [rows[s] for s in ("^TNX", "^FVX", "^TYX", "^IRX", "DX-Y.NYB", "^VIX", "GC=F", "CL=F", "HG=F") if s in rows]
    macro += [rows[s] for s in ("TLT", "IEF", "HYG", "LQD") if s in rows]
    crypto = [rows[s] for s in ("BTC-USD", "ETH-USD", "SOL-USD") if s in rows]
    if macro or crypto:
        add("## 5. Cross-asset check")
        add("")
        add(
            md_table(
                ["Instrument", "Level", "1D", "1W", "1M"],
                [
                    [r["name"], _level(r), move(r, "1d"), move(r, "1w"), move(r, "1m")]
                    for r in macro
                ],
                widths=[24, 16, 9, 9, 9],
                aligns=["l", "l", "r", "r", "r"],
            )
        )
        add("")
        if crypto:
            add(
                md_table(
                    ["Crypto", "Level", "1D", "1W", "1M", "Flow (est)"],
                    [
                        [
                            r["name"],
                            f"${r['close']:,.0f}" if r.get("close") else "-",
                            pct(r.get("chg_pct")),
                            pct(r.get("ret5")),
                            pct(r.get("ret20")),
                            usd(r.get("flow1")),
                        ]
                        for r in crypto
                    ],
                    widths=[12, 12, 9, 9, 9, 11],
                    aligns=["l", "r", "r", "r", "r", "r"],
                )
            )
            add("")

    # ----------------------------------------------------------- 6 movers
    movers = d.get("movers") or []
    if movers:
        add("## 6. Unusual activity")
        add("")
        add("Moves of 2%+ on at least 1.2x normal volume.")
        add("")
        add(
            md_table(
                ["Ticker", "Name", "1D", "RVOL", "Flow (est)", "5D", "20D"],
                [
                    [
                        m["symbol"],
                        m["name"],
                        pct(m.get("ret1")),
                        ratio(m.get("rvol")),
                        usd(m.get("flow1")),
                        pct(m.get("ret5")),
                        pct(m.get("ret20")),
                    ]
                    for m in movers
                ],
                widths=[10, 24, 8, 6, 11, 8, 8],
                aligns=["l", "l", "r", "r", "r", "r", "r"],
            )
        )
        add("")

    # ----------------------------------------------------------- 7 risks
    if brief.get("stocks") or brief.get("risks") or brief.get("watch_tomorrow"):
        add("## 7. Risks and tomorrow's watchlist")
        add("")
        if brief.get("stocks"):
            add("**On the radar**")
            add("")
            for s in brief["stocks"]:
                add(f"- **{s.get('ticker','')}** - {s.get('note','')}")
            add("")
        if brief.get("risks"):
            add("**What could flip this**")
            add("")
            for r in brief["risks"]:
                add(f"- {r}")
            add("")
        if brief.get("watch_tomorrow"):
            add("**Check tomorrow**")
            add("")
            for w in brief["watch_tomorrow"]:
                add(f"- {w}")
            add("")

    # ----------------------------------------------------------- footer
    add("---")
    add("")
    add("### How to read this")
    add("")
    add(
        "- **Flow (est)** = dollar volume x agreement x conviction, where agreement is the average of "
        "(where the close sits in the day's range) and (the sign of the move), and conviction is the size "
        "of the move relative to that instrument's own ATR. All three have to line up before a day counts "
        "as real inflow. It is an **estimate from price and volume**, not ETF creation/redemption data, "
        "not 13F positioning, and not net cash entering a security."
    )
    add(
        "- **RVOL** is today's dollar volume divided by the 20-session median. Above ~1.5x means real participation."
    )
    add(
        "- **Share of move** is each name's slice of traded dollars times its move, normalised across the "
        "equity universe. It shows who dominated activity today; it is not official index weight or index points."
    )
    add("- **Risk appetite** ranks a risk-on basket (SPY, IWM, HYG, KRE, XLY, BTC) against a risk-off basket "
        "(TLT, GLD, DXY, VIX, XLP, XLU) over 5 sessions, each against its own 1-year history. 50 = neutral.")
    add("")
    gen = "OpenRouter " + str(meta.get("model") or "n/a") if meta.get("model") else "deterministic templates"
    add(
        f"_Data: Yahoo Finance public chart API (adjusted closes for returns), cached locally. "
        f"Summary generated by {gen}. Prices are as of the last available session close, not real-time. "
        f"This is a research tool, not investment advice._"
    )
    add("")
    return "\n".join(L)


def write_report(snapshot: dict, brief: dict, meta: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    date = (snapshot.get("session") or {}).get("session_date") or "unknown"
    text = render(snapshot, brief, meta)
    path = REPORT_DIR / f"{date}.md"
    path.write_text(text, encoding="utf-8")
    (REPORT_DIR / "latest.md").write_text(text, encoding="utf-8")
    (REPORT_DIR / "latest.json").write_text(
        json.dumps(
            {
                "generated_at": snapshot.get("generated_at"),
                "session_date": date,
                "brief": brief,
                "llm": meta,
                "session": snapshot.get("session"),
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return path
