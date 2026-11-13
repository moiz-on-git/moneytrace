"""Configuration: paths, instrument universe, tech stacks, LLM settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
REPORT_DIR = ROOT / "reports"
LOG_DIR = ROOT / "logs"

OPENROUTER_URL = "https://openrouter.ai/api/v1"
OPENROUTER_CHAT = OPENROUTER_URL + "/chat/completions"
APP_TITLE = "Money Trace"

# Tried in order; the first one that exists in the live OpenRouter catalogue wins.
# Cheap, fast, strong instruction-followers -- a daily brief costs well under $0.01.
PREFERRED_MODELS = [
    "deepseek/deepseek-v4-flash",
    "google/gemini-3.5-flash",
    "anthropic/claude-haiku-5.5",
    "z-ai/glm-5.3-flash",
    "openai/gpt-5-mini",
    "qwen/qwen3.8-flash",
]

CACHE_TTL_SECONDS = 15 * 60


@dataclass(frozen=True)
class Instrument:
    """One thing whose money trail we track."""

    symbol: str
    name: str
    group: str
    kind: str = "etf"

    @property
    def slug(self) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in self.symbol)


def _build() -> list[Instrument]:
    spec: dict[str, list[tuple[str, str, str]]] = {
        # group -> [(symbol, name, kind)]
        "index": [
            ("SPY", "S&P 500", "etf"),
            ("QQQ", "Nasdaq 100", "etf"),
            ("IWM", "Russell 2000", "etf"),
            ("DIA", "Dow 30", "etf"),
            ("RSP", "S&P 500 equal-weight", "etf"),
        ],
        "sector": [
            ("XLK", "Technology", "etf"),
            ("XLF", "Financials", "etf"),
            ("XLE", "Energy", "etf"),
            ("XLV", "Health Care", "etf"),
            ("XLI", "Industrials", "etf"),
            ("XLY", "Cons. Discretionary", "etf"),
            ("XLP", "Cons. Staples", "etf"),
            ("XLU", "Utilities", "etf"),
            ("XLB", "Materials", "etf"),
            ("XLRE", "Real Estate", "etf"),
            ("XLC", "Comm. Services", "etf"),
        ],
        "theme": [
            ("SMH", "Semiconductors", "etf"),
            ("IGV", "Software", "etf"),
            ("HACK", "Cybersecurity", "etf"),
            ("SKYY", "Cloud computing", "etf"),
            ("AIQ", "AI & big data", "etf"),
            ("BOTZ", "Robotics & AI", "etf"),
            ("QTUM", "Quantum computing", "etf"),
            ("GRID", "Grid infrastructure", "etf"),
            ("NLR", "Nuclear power", "etf"),
            ("URA", "Uranium", "etf"),
            ("LIT", "Lithium & battery", "etf"),
            ("TAN", "Solar", "etf"),
            ("ICLN", "Clean energy", "etf"),
            ("COPX", "Copper miners", "etf"),
            ("GDX", "Gold miners", "etf"),
            ("XBI", "Biotech", "etf"),
            ("ITA", "Aerospace & defense", "etf"),
            ("JETS", "Airlines", "etf"),
            ("KRE", "Regional banks", "etf"),
            ("XHB", "Homebuilders", "etf"),
            ("XRT", "Retail", "etf"),
            ("XOP", "Oil & gas E&P", "etf"),
            ("ARKK", "Innovation (ARK)", "etf"),
        ],
        "macro": [
            ("DX-Y.NYB", "US dollar index", "index"),
            ("^TNX", "US 10Y yield", "rate"),
            ("^FVX", "US 5Y yield", "rate"),
            ("^TYX", "US 30Y yield", "rate"),
            ("^IRX", "US 13W bill", "rate"),
            ("^VIX", "VIX volatility", "index"),
            ("GC=F", "Gold futures", "future"),
            ("SI=F", "Silver futures", "future"),
            ("CL=F", "WTI crude", "future"),
            ("NG=F", "Nat gas", "future"),
            ("HG=F", "Copper futures", "future"),
        ],
        "credit": [
            ("TLT", "20Y+ Treasuries", "etf"),
            ("IEF", "7-10Y Treasuries", "etf"),
            ("SHY", "1-3Y Treasuries", "etf"),
            ("HYG", "High-yield credit", "etf"),
            ("LQD", "IG credit", "etf"),
            ("TIP", "Inflation-protected", "etf"),
        ],
        "global": [
            ("EEM", "Emerging markets", "etf"),
            ("EFA", "Developed ex-US", "etf"),
            ("FXI", "China large cap", "etf"),
            ("KWEB", "China internet", "etf"),
            ("EWJ", "Japan", "etf"),
            ("EWZ", "Brazil", "etf"),
            ("INDA", "India", "etf"),
            ("EWT", "Taiwan", "etf"),
            ("EWY", "Korea", "etf"),
        ],
        "mega": [
            ("NVDA", "NVIDIA", "stock"),
            ("MSFT", "Microsoft", "stock"),
            ("AAPL", "Apple", "stock"),
            ("GOOGL", "Alphabet", "stock"),
            ("AMZN", "Amazon", "stock"),
            ("META", "Meta Platforms", "stock"),
            ("AVGO", "Broadcom", "stock"),
            ("TSLA", "Tesla", "stock"),
            ("AMD", "AMD", "stock"),
            ("NFLX", "Netflix", "stock"),
            ("TSM", "TSMC", "stock"),
            ("ASML", "ASML", "stock"),
            ("ARM", "Arm Holdings", "stock"),
            ("MU", "Micron", "stock"),
            ("ORCL", "Oracle", "stock"),
            ("CRM", "Salesforce", "stock"),
            ("ADBE", "Adobe", "stock"),
            ("PLTR", "Palantir", "stock"),
            ("SMCI", "Super Micro", "stock"),
            ("INTC", "Intel", "stock"),
        ],
        "stock": [
            ("JPM", "JPMorgan", "stock"),
            ("BAC", "Bank of America", "stock"),
            ("GS", "Goldman Sachs", "stock"),
            ("XOM", "Exxon Mobil", "stock"),
            ("CVX", "Chevron", "stock"),
            ("LLY", "Eli Lilly", "stock"),
            ("UNH", "UnitedHealth", "stock"),
            ("WMT", "Walmart", "stock"),
            ("COST", "Costco", "stock"),
            ("VST", "Vistra", "stock"),
            ("CEG", "Constellation Energy", "stock"),
            ("OKLO", "Oklo", "stock"),
            ("SMR", "NuScale Power", "stock"),
            ("NNE", "Nano Nuclear", "stock"),
            ("IONQ", "IonQ", "stock"),
            ("RGTI", "Rigetti", "stock"),
            ("COIN", "Coinbase", "stock"),
            ("MSTR", "Strategy (MSTR)", "stock"),
            ("HOOD", "Robinhood", "stock"),
            ("MARA", "MARA Holdings", "stock"),
            ("CRCL", "Circle", "stock"),
        ],
        "crypto": [
            ("BTC-USD", "Bitcoin", "crypto"),
            ("ETH-USD", "Ethereum", "crypto"),
            ("SOL-USD", "Solana", "crypto"),
            ("XRP-USD", "XRP", "crypto"),
            ("BNB-USD", "BNB", "crypto"),
        ],
    }
    out: list[Instrument] = []
    for group, rows in spec.items():
        for symbol, name, kind in rows:
            out.append(Instrument(symbol, name, group, kind))
    return out


UNIVERSE: list[Instrument] = _build()
BY_SYMBOL: dict[str, Instrument] = {i.symbol: i for i in UNIVERSE}

# "Key technologies" -- a lens over the universe, not a separate fetch.
TECH_STACKS: list[dict] = [
    {
        "label": "AI compute & semis",
        "tickers": ["SMH", "NVDA", "AVGO", "TSM", "ASML", "AMD", "MU", "ARM"],
        "note": "accelerators, foundry, memory, lithography",
    },
    {
        "label": "AI power & grid",
        "tickers": ["GRID", "NLR", "URA", "VST", "CEG", "OKLO", "SMR"],
        "note": "electricity is the binding constraint on datacenters",
    },
    {
        "label": "Software & cloud",
        "tickers": ["IGV", "SKYY", "MSFT", "ORCL", "CRM", "ADBE"],
        "note": "seat-based SaaS vs AI consumption pricing",
    },
    {
        "label": "Cybersecurity",
        "tickers": ["HACK"],
        "note": "defensive tech spend, resilient budgets",
    },
    {
        "label": "Quantum",
        "tickers": ["QTUM", "IONQ", "RGTI"],
        "note": "long-duration speculative compute theme",
    },
    {
        "label": "Robotics & automation",
        "tickers": ["BOTZ"],
        "note": "physical AI, reshoring capex",
    },
    {
        "label": "Biotech",
        "tickers": ["XBI", "LLY"],
        "note": "rate-sensitive risk appetite proxy",
    },
    {
        "label": "Defense",
        "tickers": ["ITA"],
        "note": "fiscal / geopolitical spend",
    },
    {
        "label": "Crypto rails",
        "tickers": ["COIN", "MSTR", "HOOD", "MARA", "CRCL", "BTC-USD"],
        "note": "high-beta liquidity proxy",
    },
    {
        "label": "Energy transition",
        "tickers": ["TAN", "ICLN", "LIT", "COPX"],
        "note": "policy + copper/battery supply chain",
    },
    {
        "label": "China tech",
        "tickers": ["KWEB", "FXI"],
        "note": "policy-driven beta, cheap vs US",
    },
    {
        "label": "Consumer",
        "tickers": ["XRT", "AMZN", "WMT", "COST"],
        "note": "the real-economy tell",
    },
]


def load_env(path: Path | None = None) -> None:
    """Minimal .env loader (no dependency on python-dotenv)."""
    path = path or (ROOT / ".env")
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def api_key() -> str | None:
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return key or None


def ensure_dirs() -> None:
    for d in (DATA_DIR, CACHE_DIR, SNAPSHOT_DIR, REPORT_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
