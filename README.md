# Money Trace

A daily money-flow monitor. Every run answers four questions:

1. **Where did the money move?** — ranked estimated dollar flows across indexes, sectors, themes, single
   stocks, credit, commodities and crypto.
2. **Who is driving it?** — which names account for the session's dollar-weighted movement, and how
   concentrated it was.
3. **Which technologies and stocks are in favour?** — 12 tech stacks (AI compute, AI power, software,
   cyber, quantum, robotics, biotech, defense, crypto rails, energy transition, China tech, consumer)
   scored on price, flow and breadth.
4. **What changed?** — multi-session flow streaks, reversals, rotation quadrants, breadth and a
   risk-appetite gauge, then a short AI-written brief on top.

No paid data. No Python dependencies. One OpenRouter call per day (~$0.001).

---

## Quick start

```powershell
python -m moneytrace run
```

That is the whole thing. First run takes ~20s and writes `reports/2026-11-12.md` plus `reports/latest.md`.
On Windows you can also double-click **`run.cmd`**, which runs it and opens the report.

```powershell
python -m moneytrace run --no-ai      # skip the model, use deterministic templates
python -m moneytrace run --refresh    # ignore the 15-minute local cache
python -m moneytrace run --open       # open the report when done
python -m moneytrace status           # print the latest brief in the terminal
python -m moneytrace models           # show which OpenRouter model would be used
python -m unittest discover -s tests -t .   # 28 tests, no network
```

Requires Python 3.10+. No `pip install` needed — the standard library does the HTTP, the JSON, the
math and the concurrency.

---

## What a run produces

| Output | What it is |
| --- | --- |
| `reports/YYYY-MM-DD.md` | The full brief: dashboard, flow tables, rotation map, drivers, tech stacks, cross-asset, movers, risks. |
| `reports/latest.md` | Same file, always the most recent session. |
| `data/snapshots/YYYY-MM-DD.json` | Every computed metric for every instrument. This is what builds history. |
| `reports/latest.json` | Just the AI brief + model metadata + usage cost. |

The terminal prints a digest:

```
MONEY TRACE  2026-11-12  [close]
------------------------------------------------------------------------------
  Semis split: AMD surges 5.9% while NVDA drops 4.3% in heaviest volume of the day.
  Regime: MIXED 57.8/100  |  Breadth: 18.0% up  |  SPY -0.35%  |  QQQ -0.32%

  Money moving IN
    AMD      AMD                     +$19.30B    +5.86%    2.2x
    AVGO     Broadcom                +$10.15B    +5.54%    1.9x
  Money moving OUT
    IWM      Russell 2000             -$4.86B    -1.64%    1.0x
    NVDA     NVIDIA                   -$4.33B    -4.34%    4.9x
```

---

## How the numbers are actually built

This is the part worth reading, because the tool's value depends on it being honest.

### Flow (est)

There is no free feed of real fund flows (creation/redemption, 13F). Anyone who shows you "money
flowing into X" from price/volume is estimating. Money Trace is explicit about its estimator:

```
agreement  = 0.5 * (where the close sits in the day's range, -1..+1) + 0.5 * sign(return)
conviction = min(1, |return| / ATR%)          # move size vs that instrument's normal range
flow       = dollar_volume * agreement * conviction
```

All three have to line up before a day counts as inflow: price closed up, closed near the high of its
range, and moved a lot relative to its own normal range. A flat day nets to roughly zero. A gap-down
that claws back to close on the high also nets to roughly zero — which is correct, because the tape
did not resolve.

It is a proxy for dollar pressure, not net cash entering a security (every trade has a buyer and a
seller). The report says so in the footer.

### RVOL

Today's dollar volume / 20-session median dollar volume. Above ~1.5x means real participation rather
than drift. Crypto volume from Yahoo is already quoted in USD, so it is not multiplied by price again.

### Share of move

`traded-dollar share x return`, normalised by the sum of absolute displacements. It answers "who
accounted for today's movement" without pretending to be index points. Traded-dollar weights are much
larger than true index weights for the biggest names (NVDA was 31% of traded dollars in the sample
session, far above its index weight), so calling this "index contribution" would be wrong.

### Risk appetite

A risk-on basket (SPY, IWM, HYG, KRE, XLY, BTC) versus a risk-off basket (TLT, GLD, DXY, VIX, XLP,
XLU). Each instrument's 5-session return is ranked against its own trailing year, then the two baskets
are differenced onto a 0-100 scale. 50 is neutral.

### Streaks and reversals

Built by diffing the stored snapshots, so the tool gets more useful the longer you run it. A "3d in"
streak means three consecutive sessions of same-sign estimated flow. On the first run there is no
history, so these sections are simply absent.

---

## Coverage

111 instruments, all verified to resolve:

- **Indexes** SPY, QQQ, IWM, DIA, RSP
- **Sectors** all 11 SPDRs
- **Themes** SMH, IGV, HACK, SKYY, AIQ, BOTZ, QTUM, GRID, NLR, URA, LIT, TAN, ICLN, COPX, GDX, XBI,
  ITA, JETS, KRE, XHB, XRT, XOP, ARKK
- **Macro** DXY, 5Y/10Y/30Y/13W yields, VIX, gold, silver, WTI, nat gas, copper
- **Credit** TLT, IEF, SHY, HYG, LQD, TIP
- **Global** EEM, EFA, FXI, KWEB, EWJ, EWZ, INDA, EWT, EWY
- **Stocks** 20 mega caps + 21 single names (banks, energy, defence-adjacent, power, quantum, crypto
  equity: VST, CEG, OKLO, SMR, IONQ, COIN, MSTR, HOOD, CRCL…)
- **Crypto** BTC, ETH, SOL, XRP, BNB

Add or remove anything in `moneytrace/config.py` (`_build()` for instruments, `TECH_STACKS` for theme
baskets). Dead symbols are dropped gracefully and reported in the snapshot's `meta.errors`.

---

## The AI brief

One OpenRouter call per day, using the cheapest strong model available at runtime from
`PREFERRED_MODELS` (currently `deepseek/deepseek-v4-flash` at $0.09/$0.18 per million tokens — about
**$0.001 per run**, so $50 of credit is decades of daily briefs).

The model never sees raw prices and never computes anything. It receives ~7k tokens of already-computed
JSON and writes prose: headline, three bullets, where money moved, who is driving, tech reads, stocks on
the radar, risks, tomorrow's watchlist.

Guardrails:

- Strict JSON schema, validated and coerced field by field.
- A claim sanitiser strips unsupported superlatives ("worst since…", "highest in months") because the
  payload does not contain that history. Percentile fields are provided so it can say "4th percentile of
  its past year" honestly instead.
- Definitions are passed with the data so "share of move" is not described as index points.
- If the model errors, returns unparseable JSON, or you have no credit, the run **still produces a full
  report** from deterministic templates. The footer names which path was used.

Pin a model with `--model`, or by setting `MODEL=` in `.env`.

---

## Automate it

The schedule below runs Tue-Sat at 07:30 IST, which is after the 16:00 ET US close, so Monday-Friday
sessions are all covered. It uses `--max-age-hours 6`: if a report for the session already exists, the
run exits immediately instead of paying for the same work twice.

### DeepSeek Harness schedule (active)

A task titled *"Run daily money-flow brief"* is active and delivers the digest into a session. It runs
the tool, then reads `reports/latest.md` and posts the condensed version. Manage it with
`schedule_list` / `schedule_edit`.

### Windows Task Scheduler (nothing installed)

**No OS-level task is registered.** If you ever want a fallback that runs without the harness, the
script is ready and only touches your own task folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_task.ps1   # opt in
schtasks /query /tn "Money Trace Daily" /fo LIST /v                    # check
Unregister-ScheduledTask -TaskName "Money Trace Daily" -Confirm:$false # undo
```

That runs `scripts/run_daily.ps1` Tue-Sat 07:30 and logs to `logs\`. If it is not installed, `run.cmd`
is the manual equivalent.

---

## Limitations, stated plainly

- **Prices are end-of-day**, from the last available Yahoo Finance close, cached 15 minutes. This is a
  post-close briefing tool, not a real-time tape.
- **Flow is estimated** from price and volume. It will occasionally disagree with actual fund-flow data.
- **No fundamentals, no news, no earnings calendar.** The brief describes what the tape did, not why.
  When the AI writes a reason, treat it as inference from the flow pattern, not a reported fact.
- **Contribution is activity share**, not index weight.
- Yahoo's public endpoint is unofficial and can rate-limit or change. A Stooq CSV fallback covers US
  ETFs/stocks; if both fail the symbol is skipped and listed in `meta.errors`.
- **Not investment advice.** No price targets, no recommendations.

---

## Run it on GitHub (Student Pack)

Short answer: **yes, but GitHub Pages cannot run Python.** Pages only serves static files, so it can
never fetch prices or call the model. GitHub Actions does the daily work; the repo is where the report
lives.

The split:

| Piece | What it does |
| --- | --- |
| GitHub Actions (`.github/workflows/daily.yml`) | Runs tests, fetches data, builds the brief, commits `reports/` and `data/snapshots/` |
| Repository | Stores the history; GitHub renders `reports/latest.md` as a formatted page |
| Pages (optional) | Needs a static HTML build — ask and I'll add one |

### Setup, three steps

1. Push the repo.
2. **Settings → Secrets and variables → Actions → New repository secret**: name it
   `OPENROUTER_API_KEY`, paste your key. Do **not** commit `.env`.
3. **Actions → Enable workflows**, then run `daily-brief` once with *Run workflow* to confirm.

It then runs Tue-Sat at 02:00 UTC (07:30 IST), after the US close. The 6-hour freshness guard is only
used by the local scheduler scripts — CI always builds, since a committed report would otherwise make
the first run look like a no-op.

### What the Student Pack actually buys you here

- **GitHub Pro** while you're enrolled: private repos, and roughly **3,000 Actions minutes/month** on
  private repos. **Public repos get free standard-runner minutes**, so a public repo needs no Pro at all.
- **Pages for private repos** (normally a Pro feature), if you later want a site.
- **Copilot** — genuinely useful for extending this.

This job uses about **1 minute per run**, ~25 minutes a month, and ~$0.001 of OpenRouter credit. Either
way it fits comfortably.

### Caveats worth knowing

- **Scheduled workflows are best-effort.** They can fire late under load, and GitHub disables them after
  60 days without repository activity. This job commits daily, which keeps it active — but if the market
  is closed for a long stretch, push a commit to keep it alive.
- **Datacenter IPs.** Yahoo's public endpoint sometimes rate-limits cloud IPs. The Stooq CSV fallback
  covers US ETFs and stocks; anything unreachable is listed in the snapshot's `meta.errors`.
- **Public repo = public reports.** Fine for a portfolio piece; use a private repo (Pro) if not.
- **Rotate the key** you pasted into chat before pushing, then put the new one straight into the secret.

## Layout

```
moneytrace/
  config.py    paths, 111-instrument universe, 12 tech stacks, model preferences, .env loader
  sources.py   Yahoo chart fetch, disk cache, Stooq fallback, parallel pull
  metrics.py   returns, dollar volume, RVOL, flow estimator, ATR, percentiles, cross-sectional ranks
  analysis.py  breadth, regime, sectors/rotation, drivers, stacks, streaks, snapshot assembly
  llm.py       OpenRouter client, model resolution, prompt, JSON validation, claim sanitiser, fallback
  render.py    markdown report
  cli.py       argparse entry point
tests/         28 unit tests: flow math, sanitiser, formatting, full pipeline, history streaks
reports/       daily markdown + latest
data/          snapshots (history), cache (gitignored)
scripts/       run_daily.ps1, register_task.ps1
run.cmd        double-click launcher
```

## Tests

```powershell
python -m unittest discover -s tests -t .
```

No network, no API key, ~0.03s. They pin the behaviour that is easy to break later:

- the flow estimator is positive on a strong close, near zero on a flat day, and near zero on a
  gap-down that closes at the high of its range (the bug that made the first version lie)
- crypto volume is treated as dollars, yields move in basis points, short histories don't crash
- the claim sanitiser cuts "worst day in a year" but keeps the number and the percentile
- the brief parser keeps `vehicles`/`tickers` as lists and never blanks short tickers
- a full synthetic snapshot renders with no `None` cells and valid right-aligned tables
- streaks and reversals compute correctly from stored snapshots

## Version control

The repo is initialised on `main` with a first commit. `.env` is gitignored — verify before pushing:

```powershell
git ls-files | Select-String "^\.env$"   # must print nothing
```

---

## Security

The OpenRouter key lives in `.env`, which is gitignored. Never commit it. If the key has been shared in
a chat or screenshot, rotate it at <https://openrouter.ai/keys> — the tool only needs a new line in
`.env`.
