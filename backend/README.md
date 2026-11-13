# Money Trace — backend

The engine. Fetches market data, computes money-flow and rotation metrics, writes a markdown report,
and publishes the JSON API the mobile app reads.

Runs on GitHub Actions, or locally. No paid data, no server, no Python dependencies.

## Run

```powershell
cd backend
python -m moneytrace run
```

Writes:

| Path | What |
| --- | --- |
| `backend/reports/YYYY-MM-DD.md` | Human-readable brief |
| `backend/data/snapshots/YYYY-MM-DD.json` | Every metric for every instrument (history) |
| `docs/v1/latest.json` | App API — today |
| `docs/v1/sessions/YYYY-MM-DD.json` | App API — per session |
| `docs/v1/index.json` | App API — archive list |

```powershell
python -m moneytrace run --no-ai      # skip the model, use templates
python -m moneytrace run --refresh    # ignore the 15-minute cache
python -m moneytrace run --no-publish # report only, don't touch docs/
python -m moneytrace status           # latest brief in the terminal
python -m moneytrace models           # which OpenRouter model would be used
python -m unittest discover -s tests -t .
```

Requires Python 3.10+ and nothing else.

## How the numbers are built

This is the part that matters, because "where money is moving" is easy to fake.

### Flow (est)

No free feed gives real fund flows. Money Trace estimates, and says so:

```
agreement  = ½ (close position in the day's range, -1..+1) + ½ sign(return)
conviction = min(1, |return| / ATR%)
flow       = dollar_volume × agreement × conviction
```

All three must agree before a day counts as inflow. A flat day nets near zero; a gap-down that closes
on its high also nets near zero, because the tape did not resolve. The first version used plain Chaikin
and reported **+$110B flowing into NVDA on a −4.3% day** — this formulation reports −$4.3B, which is
what happened.

It is a proxy for dollar pressure, not net cash entering a security (every trade has a buyer and a
seller).

### RVOL

Today's dollar volume ÷ 20-session median. Above ~1.5x means real participation. Yahoo quotes crypto
volume in USD already, so it is not multiplied by price again.

### Share of move

Traded-dollar share × return, normalised by total absolute displacement. Answers "who accounted for
today's movement" without pretending to be index points — traded-dollar weights are much larger than
true index weights for mega caps.

### Risk appetite

Risk-on basket (SPY, IWM, HYG, KRE, XLY, BTC) vs risk-off (TLT, GLD, DXY, VIX, XLP, XLU). Each 5-day
return is ranked against its own trailing year, then the baskets are differenced onto 0–100.

### Streaks

Computed from stored snapshots, so the tool gets more useful the longer it runs.

## Coverage

111 instruments: 5 indexes, 11 sectors, 23 themes, 11 macro, 6 credit, 9 global, 41 single stocks,
5 crypto. Edit `moneytrace/config.py` (`_build()` and `TECH_STACKS`) to change it. Dead symbols are
dropped and listed in `meta.errors`.

## The AI brief

One OpenRouter call per day, cheapest strong model available at runtime (~$0.001). The model receives
only computed JSON (~7k tokens) and writes prose — it never computes anything.

Guardrails: strict JSON schema validated field by field; a claim sanitiser strips unsupported
superlatives ("worst since…") while keeping the number; definitions travel with the data so "share of
move" is never called index points. If the model fails, the report still renders from deterministic
templates.

## Tests

28 tests, no network, ~0.03s.

```powershell
python -m unittest discover -s tests -t .
```

They pin the behaviour that breaks quietly: flow sign on gap-down recovery, crypto dollar volume,
basis points for yields, the sanitiser, list fields in the brief, full pipeline render, streaks.

## Layout

```
moneytrace/
  config.py    paths, universe, tech stacks, model preferences, .env loader
  sources.py   Yahoo chart fetch, disk cache, Stooq fallback, parallel pull
  metrics.py   returns, dollar volume, RVOL, flow estimator, ATR, percentiles
  analysis.py  breadth, regime, rotation, drivers, stacks, streaks
  llm.py       OpenRouter client, prompt, JSON validation, claim sanitiser, fallback
  render.py    markdown report
  publish.py   docs/v1 JSON API
  cli.py       entry point
tests/         unit tests
data/          snapshots + cache (cache is gitignored)
reports/       markdown briefs
```

## Limitations

End-of-day prices from Yahoo's public endpoint (cached 15 minutes, Stooq fallback). Flow is estimated
from price and volume and will sometimes disagree with real fund-flow data. No news, fundamentals or
earnings calendar — when the brief gives a reason, it is inference from the tape, not a reported fact.
Not investment advice.
