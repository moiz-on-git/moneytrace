# Money Trace

Where capital moved today, who moved it, and what to watch tomorrow — computed from market data every
morning, published as a static JSON API from this repo, read by a phone app.

No server to run. No paid data. No Python dependencies. About **$0.001 per day** in inference.

```
                 GitHub Actions (daily, 02:00 UTC)
                              │
                   backend/  python -m moneytrace run
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
 backend/reports/*.md   backend/data/snapshots   docs/v1/*.json
    human brief           raw metrics            public API
                                                        │
                                                        ▼
                                              app/  Expo client
```

The trick is that the "backend" is just files committed on a schedule. GitHub serves them; there is
nothing to host, keep warm, or pay for.

---

## What it does

1. **Where the money moved** — estimated dollar flow across 111 instruments: indexes, sectors, 23
   themes, 41 single stocks, credit, commodities, crypto.
2. **Who is driving it** — each name's share of the session's dollar-weighted move.
3. **Key technologies** — 12 tech stacks (AI compute, AI power, software, cyber, quantum, robotics,
   biotech, defense, crypto rails, energy transition, China tech, consumer) scored on price, flow
   and breadth.
4. **What changed** — rotation quadrants, breadth, a risk-appetite gauge, multi-session flow streaks,
   and an AI-written brief on top.

## Why the flow numbers are honest

No free feed provides true fund flows, so the backend estimates them and labels them as estimates:

```
agreement  = ½ (close position in the day's range) + ½ sign(return)
conviction = min(1, |return| / ATR)
flow       = dollar_volume × agreement × conviction
```

A flat day nets near zero. A gap-down that closes on its high also nets near zero, because the tape
didn't resolve. Read [`backend/README.md`](backend/README.md) for the full method, and why the first
naive version reported +$110B "flowing into" NVIDIA on a −4.3% day.

---

## Repo layout

```
backend/            the engine (see backend/README.md)
  moneytrace/         fetch · metrics · analysis · llm · render · publish
  tests/              28 tests, no network
  reports/            markdown briefs
  data/snapshots/     raw metrics history
docs/v1/            the public JSON API (generated, committed)
app/                Expo/React Native client (see app/README.md)
.github/workflows/  daily-brief — tests, build, commit, push
```

## Run the backend locally

```powershell
cd backend
python -m moneytrace run
```

Needs Python 3.10+ and an `OPENROUTER_API_KEY` in `backend/.env` (optional — without it the brief is
generated from templates).

## Run the app

```powershell
cd app
npm install
npm start
```

Then scan the QR with Expo Go. **Nothing is built or signed** — Expo Go loads the JS bundle.

Before it shows data, set your repo in [`app/src/config.ts`](app/src/config.ts):

```ts
export const REPO_OWNER = "your-github-username";
export const REPO_NAME = "money-trace";
```

## The API

Three static files, no auth, no rate limit beyond GitHub's own:

| Endpoint | Contents |
| --- | --- |
| `docs/v1/latest.json` | Latest session: brief, flows, sectors, drivers, stacks, macro, crypto |
| `docs/v1/sessions/<date>.json` | Same shape for a specific session |
| `docs/v1/index.json` | `{ latest, sessions: [...] }` for the archive list |

Served as `https://raw.githubusercontent.com/<owner>/<repo>/main/docs/v1/latest.json`, or through
GitHub Pages at `https://<owner>.github.io/<repo>/v1/latest.json` if you enable Pages on `/docs`.

Schema is versioned with `"schema": 1`. Types: [`app/src/api.ts`](app/src/api.ts) and
[`backend/moneytrace/publish.py`](backend/moneytrace/publish.py).

## Deploy it

1. Push this repo.
2. **Settings → Secrets and variables → Actions → New repository secret**: `OPENROUTER_API_KEY`.
   Never commit `.env` — it is gitignored, and CI reads the secret.
3. **Actions → Enable workflows**, then run `daily-brief` once.

It runs Tue–Sat at 02:00 UTC (07:30 IST), after the US close, and commits the report plus `docs/v1`.
Each run uses ~1 Actions minute and ~$0.001 of credit.

If you enable GitHub Pages on `/docs`, also flip `USE_PAGES = true` in the app config.

## Security

The OpenRouter key lives in `backend/.env` locally and in a repository secret on CI. It is never in
the repo:

```powershell
git ls-files | Select-String "^\.env$"   # must print nothing
```

If a key was ever pasted into a chat or a screenshot, rotate it at <https://openrouter.ai/keys>.

## Limitations

End-of-day prices, not real time. Flow is estimated from price and volume, not fund-flow data. No
news, fundamentals or earnings calendar. Public repo means public reports. **Not investment advice.**

## Docs

- [`backend/README.md`](backend/README.md) — methodology, commands, tests
- [`app/README.md`](app/README.md) — screens, config, data contract
