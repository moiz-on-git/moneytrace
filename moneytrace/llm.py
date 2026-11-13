"""OpenRouter summarisation layer.

The model receives only the computed numbers and is asked for strict JSON. If the
call fails for any reason the tool still produces a brief from deterministic
templates, so a bad network day never means a missing report.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .config import (
    APP_TITLE,
    CACHE_DIR,
    OPENROUTER_CHAT,
    OPENROUTER_URL,
    PREFERRED_MODELS,
    ensure_dirs,
)

UA = "money-trace/1.0"


# ---------------------------------------------------------------- transport


def _request(url: str, key: str | None = None, payload: dict | None = None, timeout: float = 120) -> dict:
    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if payload is not None:
        headers["HTTP-Referer"] = "https://github.com/money-trace"
        headers["X-Title"] = APP_TITLE
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:  # noqa: BLE001
                pass
            if exc.code in (401, 402, 403):
                raise RuntimeError(f"OpenRouter auth/credit error {exc.code}: {body}") from exc
            if exc.code == 400:
                raise RuntimeError(f"OpenRouter bad request: {body}") from exc
            last = RuntimeError(f"HTTP {exc.code}: {body}")
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(1.5 * (attempt + 1))
    raise last if last else RuntimeError("request failed")


def list_models(key: str | None = None, ttl: float = 86400) -> list[dict]:
    ensure_dirs()
    path = CACHE_DIR / "openrouter_models.json"
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - cached.get("_ts", 0) < ttl:
                return cached["data"]
        except Exception:  # noqa: BLE001
            pass
    data = _request(f"{OPENROUTER_URL}/models")["data"]
    path.write_text(json.dumps({"_ts": time.time(), "data": data}), encoding="utf-8")
    return data


def resolve_model(key: str | None = None, preferred: list[str] | None = None) -> str:
    """Pick the first preferred model that the live catalogue actually has."""
    preferred = preferred or PREFERRED_MODELS
    try:
        models = list_models(key)
    except Exception:  # noqa: BLE001
        return preferred[0]
    ids = {m["id"] for m in models}
    for cand in preferred:
        if cand in ids:
            return cand
    # nothing matched: take the cheapest sane chat model
    cheap = []
    for m in models:
        price = m.get("pricing") or {}
        try:
            pin = float(price.get("prompt", 1))
        except (TypeError, ValueError):
            continue
        mid = m["id"]
        if any(x in mid for x in ("embed", "tts", "whisper", "image", "vision-only")):
            continue
        cheap.append((pin, mid))
    cheap.sort()
    return cheap[0][1] if cheap else preferred[0]


# ---------------------------------------------------------------- prompting

SYSTEM = """You are the writer of a daily institutional-style markets brief called Money Trace.
You are given pre-computed numbers about one trading session: an estimated dollar money-flow per
instrument (dollar volume weighted by direction, close position in range and move size relative to
ATR -- a proxy, not fund-flow data), percentage moves, relative volume (RVOL), percentiles, breadth,
sector rotation quadrants, dollar-weighted contribution to the index move, theme baskets, cross-asset
levels, and multi-session flow streaks.

Hard rules:
- Use ONLY the numbers given. Never invent a price, a flow, a headline, or a reason that the data
  does not support. If data is missing, say so plainly.
- Never claim a record, a "worst/best since", a "highest in months", or that something is "flat" /
  "unchanged" unless the payload supports it. Use the percentile fields (ts_rank, z1) when you want to
  say a move was unusual, and quote the number even when it is small.
- Be concrete: name tickers and quote the numbers that justify each claim.
- Interpret, do not predict. No price targets. No "buy/sell/hold". This is not investment advice.
- `share_of_move` is each name's share of the session's dollar-weighted movement, not index points and not
  official index weight. Never write the word "index" when describing it; say "of the session's
  dollar-weighted move".
- Short sentences. Desk-note tone. No hype words, no "unprecedented", no emoji.
- Translate field names into plain English: say "4th percentile of its past year", not "ts_rank 4.0";
  say "4.9x normal volume", not "RVOL 4.93". Percentiles are whole numbers: write "bottom 1% of its
  past year", never "0.8th percentile".
- Where the data conflicts with the obvious narrative, say so; that is the valuable part.

Return a single JSON object, no markdown fence, exactly this shape:
{
  "regime": "risk-on" | "risk-off" | "mixed" | "rotation",
  "headline": "<= 90 chars, the single most important fact of the session",
  "tldr": ["2-4 bullets, <= 30 words each, each with a number"],
  "where_money_moved": [
    {"direction": "in" | "out", "theme": "short label", "evidence": "1 sentence with numbers", "vehicles": ["TICKER"]}
  ],
  "who_is_driving": [
    {"name": "TICKER or group", "why": "1-2 sentences, cite share of move / flow / RVOL"}
  ],
  "key_tech": [
    {"tech": "e.g. AI compute & semis", "signal": "what the money did, 1 sentence", "tickers": ["SMH"]}
  ],
  "stocks": [{"ticker": "XYZ", "note": "why it is on the radar today"}],
  "risks": ["what could flip this, grounded in the data"],
  "watch_tomorrow": ["specific, checkable items"],
  "confidence": 0.0-1.0
}
Aim for exactly 3 where_money_moved, 3 who_is_driving, 4 key_tech, 3 stocks, 2 risks, 2 watch_tomorrow.
Be terse: every string under 22 words, every evidence sentence a single clause with one number."""


def compact(snapshot: dict) -> dict:
    """Small, LLM-friendly slice of the snapshot (keeps the prompt cheap)."""
    rows = snapshot["rows"]
    d = snapshot["derived"]

    def slim(row: dict, keys: list[str]) -> dict:
        return {k: row.get(k) for k in keys if row.get(k) is not None}

    macro_syms = [s for s, r in rows.items() if r["group"] in ("macro", "credit")]
    macro = [slim(rows[s], ["symbol", "name", "close", "chg_pct", "chg_bps", "level", "ret5", "ret20"]) for s in macro_syms]

    return {
        "definitions": {
            "flow1": "estimated net dollar pressure for the session, in USD: dollar volume x agreement x "
            "conviction. A proxy, not fund flows.",
            "share_of_move": "each name's share of the session's total dollar-weighted movement. NOT index "
            "points and NOT official index weight.",
            "rvol": "dollar volume vs its own 20-session median; >1.5 = real participation",
            "ts_rank": "percentile of this move within the instrument's own last year (0-100)",
            "streak_days": "consecutive sessions of same-sign flow ending today",
        },
        "session": snapshot["session"],
        "breadth": d.get("breadth"),
        "regime": {k: v for k, v in (d.get("regime") or {}).items() if k in ("score", "tone")},
        "headline_numbers": {
            s: slim(rows[s], ["ret1", "ret5", "rvol"])
            for s in ("SPY", "QQQ", "IWM", "RSP", "TLT", "HYG", "GLD", "^VIX", "^TNX", "DX-Y.NYB", "BTC-USD")
            if s in rows
        },
        "inflows": [
            slim(r, ["symbol", "name", "group", "ret1", "flow1", "rvol", "ret5", "z1", "ret1_ts_rank"])
            for r in d.get("inflows", [])
        ],
        "outflows": [
            slim(r, ["symbol", "name", "group", "ret1", "flow1", "rvol", "ret5", "z1", "ret1_ts_rank"])
            for r in d.get("outflows", [])
        ],
        "sectors": [
            slim(s, ["symbol", "name", "ret1", "ret5", "ret20", "flow1", "flow5", "rvol", "rs5", "quadrant"])
            for s in d.get("sectors", [])
        ],
        "contributors": [
            {
                **slim(c, ["symbol", "name", "direction", "ret1", "flow1", "weight", "rvol"]),
                "share_of_move": c.get("share"),
            }
            for c in d.get("contributors", [])
        ],        "group_flows": d.get("group_flows"),
        "stacks": [
            slim(s, ["label", "ret1", "ret5", "flow1", "max_rvol", "leader", "laggard", "breadth_up", "note"])
            for s in d.get("stacks", [])
        ],
        "streaks": [
            {"symbol": s["symbol"], "streak_days": s["streak"], "cum_flow": s["cum"]} for s in d.get("streaks", [])
        ],
        "reversals": d.get("reversals"),
        "unusual_movers": [slim(m, ["symbol", "name", "ret1", "rvol", "flow1"]) for m in d.get("movers", [])],
        "macro": macro,
        "crypto": [
            slim(rows[s], ["symbol", "name", "chg_pct", "ret5", "flow1", "rvol"])
            for s in rows
            if rows[s]["group"] == "crypto"
        ],
    }


# ---------------------------------------------------------------- generation

# Claims like "worst day in months" need history the payload does not contain.
_UNSUPPORTED_CLAIM = re.compile(
    r"\b(worst|best|highest|lowest|biggest|smallest|strongest|weakest|sharpest|largest|record)\b"
    r"[^.;]{0,70}\b(since|in (over |the )?(a |the )?(few |several )?"
    r"(day|week|month|year|quarter)s?)\b",
    re.IGNORECASE,
)


_BANNED_CLAIM = re.compile(r"\b(record|all-time|unprecedented|never before)\b", re.IGNORECASE)


def _strip_unsupported_claims(text: str) -> str:
    """Remove the unsupported clause, not the whole sentence, so the data survives."""
    if not text:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    for sentence in parts:
        modified = False
        match = _UNSUPPORTED_CLAIM.search(sentence)
        if match:
            before, after = sentence[: match.start()], sentence[match.end() :]
            # drop a dangling possessive/article left behind by the cut ("...volume, its")
            before = re.sub(
                r"[\s,;:-]*\b(its|their|his|her|the|a|an|this|that|and|or|with)\s*$", "", before, flags=re.IGNORECASE
            )
            sentence = before + after
            sentence = re.sub(r"\s{2,}", " ", sentence)
            sentence = re.sub(r"\s+([,.;:])", r"\1", sentence)
            sentence = re.sub(r"([,;:])\s*(?=[,.;:])", r"\1", sentence)
            sentence = re.sub(r"\(\s*[,;:]?\s*\)", "", sentence)
            modified = True
        if _BANNED_CLAIM.search(sentence):
            # keep the clauses that carry facts, drop the rhetorical one
            sentence = ", ".join(c for c in re.split(r",\s*", sentence) if not _BANNED_CLAIM.search(c))
            modified = True
        # "its best day in the 98th percentile" -> "in the 98th percentile"
        sentence = re.sub(
            r"\b(?:its|their|a)\s+(?:best|worst|strongest|weakest|biggest)\s+"
            r"(?:day|session|week|month|quarter)\s+(?:in|at)\s+the\b",
            "in the",
            sentence,
            flags=re.IGNORECASE,
        )
        sentence = sentence.strip(" ,;:-")
        if not sentence:
            continue
        # only reject if sanitising left us with nothing factual
        if modified and (not re.search(r"\d", sentence) or len(sentence) < 25):
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def _extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1] if len(text.split("```")) > 2 else text
        text = text.removeprefix("json").strip()
    candidates = [text]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except Exception:  # noqa: BLE001
            continue
    return None


def _clean_brief(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict) or not raw:
        return None

    def s(x, limit=280) -> str:
        return (str(x).strip() if x is not None else "")[:limit]

    def prose(x, limit=280) -> str:
        """Free text: allowed, but unsupported superlatives get cut out."""
        return _strip_unsupported_claims(s(x, limit))[:limit]

    def lst(x) -> list:
        return x if isinstance(x, list) else []

    def dicts(
        key: str, fields: list[str], limit: int, list_fields: tuple[str, ...] = (), prose_fields: tuple[str, ...] = ()
    ) -> list[dict]:
        out = []
        for item in lst(raw.get(key))[:limit]:
            if not isinstance(item, dict):
                continue
            cleaned: dict = {}
            for f in fields:
                val = item.get(f)
                if f in list_fields:
                    if isinstance(val, list):
                        cleaned[f] = [s(x, 40) for x in val if s(x)][:8]
                    elif isinstance(val, str) and val.strip():
                        cleaned[f] = [s(val, 40)]
                    else:
                        cleaned[f] = []
                else:
                    cleaned[f] = prose(val) if f in prose_fields else s(val)
            if any(cleaned.values()):
                out.append(cleaned)
        return out

    brief = {
        "regime": s(raw.get("regime"), 20) or "mixed",
        "headline": prose(raw.get("headline"), 160),
        "tldr": [prose(x, 240) for x in lst(raw.get("tldr"))[:4] if prose(x)],
        "where_money_moved": dicts(
            "where_money_moved", ["direction", "theme", "evidence", "vehicles"], 5, ("vehicles",), ("evidence",)
        ),
        "who_is_driving": dicts("who_is_driving", ["name", "why"], 6, prose_fields=("why",)),
        "key_tech": dicts("key_tech", ["tech", "signal", "tickers"], 6, ("tickers",), ("signal",)),
        "stocks": dicts("stocks", ["ticker", "note"], 6, prose_fields=("note",)),
        "risks": [prose(x, 240) for x in lst(raw.get("risks"))[:4] if prose(x)],
        "watch_tomorrow": [prose(x, 240) for x in lst(raw.get("watch_tomorrow"))[:4] if prose(x)],
        "confidence": raw.get("confidence") if isinstance(raw.get("confidence"), (int, float)) else None,
    }
    if not brief["headline"] and not brief["tldr"]:
        return None
    return brief


def generate(snapshot: dict, key: str, model: str | None = None) -> tuple[dict | None, dict]:
    """Return (brief, meta). brief is None when the call failed."""
    model = model or resolve_model(key)
    payload = compact(snapshot)
    user_msg = (
        "Session data (JSON):\n"
        + json.dumps(payload, separators=(",", ":"), default=str)
        + "\n\nWrite the brief now as a single JSON object."
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.25,
        "max_tokens": 3800,
        "response_format": {"type": "json_object"},
        "usage": {"include": True},
    }
    meta: dict = {"model": model, "started": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        content = ""
        for attempt in range(2):
            if attempt == 1:
                # last time we ran out of output tokens -> ask for the short version
                body["max_tokens"] = 4800
                body["messages"] = [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user_msg},
                    {
                        "role": "user",
                        "content": "Your previous reply was cut off. Return the same JSON but tighter: "
                        "max 3 tldr, 3 where_money_moved, 3 who_is_driving, 4 key_tech, 3 stocks, "
                        "2 risks, 2 watch_tomorrow. Keep every string under 25 words.",
                    },
                ]
            try:
                resp = _request(OPENROUTER_CHAT, key=key, payload=body)
            except RuntimeError as exc:
                if "bad request" not in str(exc).lower():
                    raise
                body.pop("response_format", None)  # model may not support JSON mode
                resp = _request(OPENROUTER_CHAT, key=key, payload=body)
            choice = (resp.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content") or ""
            usage = resp.get("usage") or {}
            meta.update(
                {
                    "usage": {
                        k: usage.get(k)
                        for k in ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
                        if usage.get(k) is not None
                    },
                    "model_returned": resp.get("model"),
                    "finish_reason": choice.get("finish_reason"),
                }
            )
            brief = _clean_brief(_extract_json(content))
            if brief is not None:
                brief["generated_by"] = "openrouter"
                return brief, meta
        meta["error"] = f"unparseable model output (finish_reason={meta.get('finish_reason')})"
        meta["raw"] = content[:600]
        return None, meta
    except Exception as exc:  # noqa: BLE001
        meta["error"] = str(exc)[:400]
        return None, meta


# ---------------------------------------------------------------- fallback


def _fmt_pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x*100:+.2f}%"


def _fmt_usd(x: float | None) -> str:
    if x is None:
        return "n/a"
    sign = "-" if x < 0 else "+"
    x = abs(x)
    for unit, scale in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if x >= scale:
            return f"{sign}${x/scale:.2f}{unit}"
    return f"{sign}${x:.0f}"


def fallback_brief(snapshot: dict) -> dict:
    """Deterministic brief used when the LLM is unavailable."""
    d = snapshot["derived"]
    rows = snapshot["rows"]
    inflow = d.get("inflows") or []
    outflow = d.get("outflows") or []
    sectors = d.get("sectors") or []
    breadth = d.get("breadth") or {}
    regime = d.get("regime") or {}

    def label(sym: str) -> str:
        r = rows.get(sym) or {}
        return f"{sym} ({r.get('name','')})" if r.get("name") else sym

    tl = []
    if inflow:
        i = inflow[0]
        tl.append(f"Largest estimated inflow: {label(i['symbol'])} at {_fmt_usd(i['flow1'])} on {i.get('rvol') or 0:.1f}x volume, {_fmt_pct(i.get('ret1'))}.")
    if outflow:
        o = outflow[0]
        tl.append(f"Largest estimated outflow: {label(o['symbol'])} at {_fmt_usd(o['flow1'])}, {_fmt_pct(o.get('ret1'))}.")
    if breadth:
        tl.append(f"Breadth {breadth.get('pct_up')}% advancing across {breadth.get('n')} equity instruments; {breadth.get('pct_above20')}% above their 20-day average.")
    if regime:
        tl.append(f"Risk appetite reads {regime.get('tone')} at {regime.get('score')}/100.")

    where = []
    for i in inflow[:3]:
        where.append(
            {
                "direction": "in",
                "theme": i["symbol"],
                "evidence": f"{_fmt_usd(i.get('flow1'))} estimated net flow, {_fmt_pct(i.get('ret1'))}, {i.get('rvol') or 0:.1f}x relative volume.",
                "vehicles": [i["symbol"]],
            }
        )
    for o in outflow[:3]:
        where.append(
            {
                "direction": "out",
                "theme": o["symbol"],
                "evidence": f"{_fmt_usd(o.get('flow1'))} estimated net flow, {_fmt_pct(o.get('ret1'))}, {o.get('rvol') or 0:.1f}x relative volume.",
                "vehicles": [o["symbol"]],
            }
        )

    driving = [
        {
            "name": c["symbol"],
            "why": f"{c['share']:.1f}% of today's dollar-weighted movement ({c['direction']}), "
            f"{_fmt_pct(c.get('ret1'))} on {_fmt_usd(c.get('flow1'))} estimated flow.",
        }
        for c in (d.get("contributors") or [])[:5]
    ]
    tech = [
        {
            "tech": s["label"],
            "signal": f"{_fmt_pct(s.get('ret1'))} today, {_fmt_pct(s.get('ret5'))} over 5 sessions, {_fmt_usd(s.get('flow1'))} estimated flow.",
            "tickers": s["tickers"][:4],
        }
        for s in (d.get("stacks") or [])[:5]
    ]
    stocks = [
        {"ticker": m["symbol"], "note": f"{_fmt_pct(m.get('ret1'))} on {m.get('rvol') or 0:.1f}x volume, {_fmt_usd(m.get('flow1'))} flow."}
        for m in (d.get("movers") or [])[:5]
    ]
    risks = []
    if breadth and breadth.get("pct_above20") is not None and breadth["pct_above20"] < 45:
        risks.append(f"Only {breadth['pct_above20']}% of the equity universe sits above its 20-day average; the tape is narrow.")
    if regime.get("score") is not None and regime["score"] < 40:
        risks.append("Risk appetite is in the bottom two quintiles; rallies are more likely to be sold.")
    if not risks:
        risks.append("No breadth or regime red flags in today's data; the main risk is a single-name-driven tape.")

    return {
        "regime": regime.get("tone") or "mixed",
        "headline": tl[0] if tl else "Session data collected; no summary model was available.",
        "tldr": tl[:4],
        "where_money_moved": where,
        "who_is_driving": driving,
        "key_tech": tech,
        "stocks": stocks,
        "risks": risks,
        "watch_tomorrow": [
            "Whether today's top inflow vehicles hold their relative volume.",
            "Follow-through in the weakest sector (see rotation table).",
        ],
        "confidence": None,
        "generated_by": "fallback-templates",
    }
