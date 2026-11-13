"""Command line entry point: `python -m moneytrace`."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from . import __version__
from .analysis import build_snapshot, save_snapshot
from .config import REPORT_DIR, UNIVERSE, api_key, ensure_dirs, load_env
from .llm import fallback_brief, generate, resolve_model
from .publish import publish
from .render import pct, ratio, render, usd, write_report
from .sources import fetch_universe


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def _digest(snapshot: dict, brief: dict, meta: dict) -> str:
    d = snapshot["derived"]
    rows = snapshot["rows"]
    session = snapshot.get("session") or {}
    reg = d.get("regime") or {}
    breadth = d.get("breadth") or {}
    out = []
    out.append("")
    out.append(f"MONEY TRACE  {session.get('session_date','?')}  [{session.get('status','?')}]")
    out.append("-" * 78)
    if brief.get("headline"):
        out.append(f"  {brief['headline']}")
    out.append(
        f"  Regime: {(reg.get('tone') or 'n/a').upper()} {reg.get('score','?')}/100"
        f"  |  Breadth: {breadth.get('pct_up','?')}% up"
        f"  |  SPY {pct(rows.get('SPY',{}).get('ret1'))}"
        f"  |  QQQ {pct(rows.get('QQQ',{}).get('ret1'))}"
    )
    out.append("")
    infl = d.get("inflows") or []
    outl = d.get("outflows") or []
    if infl:
        out.append("  Money moving IN")
        for r in infl[:5]:
            out.append(f"    {r['symbol']:<8} {r['name'][:22]:<22} {usd(r.get('flow1')):>9}  {pct(r.get('ret1')):>8}  {ratio(r.get('rvol')):>6}")
    if outl:
        out.append("  Money moving OUT")
        for r in outl[:5]:
            out.append(f"    {r['symbol']:<8} {r['name'][:22]:<22} {usd(r.get('flow1')):>9}  {pct(r.get('ret1')):>8}  {ratio(r.get('rvol')):>6}")
    out.append("")
    for b in (brief.get("tldr") or [])[:3]:
        out.append(f"  * {b}")
    out.append("")
    gen = meta.get("model") or "deterministic templates"
    if meta.get("error"):
        gen = f"deterministic templates (model failed: {str(meta['error'])[:80]})"
    out.append(f"  Summary: {gen}")
    if meta.get("usage"):
        out.append(f"  Usage:   {meta['usage']}")
    return "\n".join(out)


def _latest_age_hours() -> float | None:
    """Age of the newest generated report, in hours."""
    path = REPORT_DIR / "latest.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stamp = payload.get("generated_at")
        if not stamp:
            return None
        then = datetime.fromisoformat(stamp)
        if then.tzinfo is None:
            then = then.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - then).total_seconds() / 3600.0
    except Exception:  # noqa: BLE001
        return None


def cmd_run(args: argparse.Namespace) -> int:
    ensure_dirs()
    load_env()
    if args.max_age_hours:
        age = _latest_age_hours()
        if age is not None and age < args.max_age_hours:
            print(f"Latest brief is {age:.1f}h old (limit {args.max_age_hours:g}h) - nothing to do.")
            return 0
    t0 = time.time()
    print(f"Fetching {len(UNIVERSE)} instruments...", flush=True)
    series, errors = fetch_universe(UNIVERSE, force=args.refresh, workers=args.workers)
    print(f"  {len(series)} series in {time.time()-t0:.1f}s, {len(errors)} failures", flush=True)
    if errors:
        for sym, err in list(errors.items())[:5]:
            print(f"    ! {sym}: {err[:120]}")

    snapshot = build_snapshot(series, UNIVERSE, errors)
    if not snapshot["rows"]:
        print("No usable data. Check your network connection.", file=sys.stderr)
        return 2
    snap_path = save_snapshot(snapshot)
    print(f"  snapshot -> {snap_path}", flush=True)

    key = None if args.no_ai else api_key()
    meta: dict = {}
    brief = None
    if key:
        print("Writing the brief via OpenRouter...", flush=True)
        brief, meta = generate(snapshot, key, model=args.model)
        if brief is None:
            print(f"  ! model failed ({meta.get('error','unknown')}); using templates", flush=True)
    if brief is None:
        brief = fallback_brief(snapshot)
        meta = meta or {"model": None, "reason": "no API key" if not key else "fallback"}
    snapshot["brief"] = brief
    report_path = write_report(snapshot, brief, meta)
    print(_digest(snapshot, brief, meta))
    print(f"\nReport: {report_path}")

    if not args.no_publish:
        try:
            api_paths = publish(snapshot, brief, meta)
            print(f"API:    {api_paths[0].parent}")
        except Exception as exc:  # noqa: BLE001 - never lose the report over the API step
            print(f"  ! API publish failed: {exc}", file=sys.stderr)

    if args.open:
        import os

        os.startfile(report_path)  # type: ignore[attr-defined]
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ensure_dirs()
    path = REPORT_DIR / "latest.json"
    if not path.exists():
        print("No report yet. Run `python -m moneytrace` first.", file=sys.stderr)
        return 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    session = payload.get("session") or {}
    brief = payload.get("brief") or {}
    print(f"Latest: {session.get('session_date')}  [{session.get('status')}]")
    print(f"Model:  {(payload.get('llm') or {}).get('model')}")
    print(f"Headline: {brief.get('headline')}")
    for b in brief.get("tldr") or []:
        print(f"  - {b}")
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    key = api_key()
    if not key:
        print("No OPENROUTER_API_KEY found in .env", file=sys.stderr)
        return 1
    chosen = resolve_model(key, [args.model] if args.model else None)
    print(f"Selected model: {chosen}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="moneytrace", description="Daily money-flow monitor with an AI-written brief.")
    p.add_argument("--version", action="version", version=f"moneytrace {__version__}")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="fetch, analyse, summarise, write the report (default)")
    run.add_argument("--no-ai", action="store_true", help="skip OpenRouter, use deterministic templates")
    run.add_argument("--model", help="force an OpenRouter model id")
    run.add_argument("--refresh", action="store_true", help="ignore the local cache")
    run.add_argument("--workers", type=int, default=6, help="parallel fetches (default 6)")
    run.add_argument("--open", action="store_true", help="open the report when done")
    run.add_argument("--no-publish", action="store_true", help="skip writing the docs/v1 JSON API")
    run.add_argument(
        "--max-age-hours",
        type=float,
        default=None,
        help="skip if a report was generated more recently than this (for schedulers)",
    )
    run.set_defaults(func=cmd_run)

    st = sub.add_parser("status", help="show the latest brief")
    st.set_defaults(func=cmd_status)

    md = sub.add_parser("models", help="show which model would be used")
    md.add_argument("--model")
    md.set_defaults(func=cmd_models)

    return p


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    args = build_parser().parse_args(argv)
    if not getattr(args, "command", None):
        # bare invocation == run
        args = build_parser().parse_args(["run"])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
