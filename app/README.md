# Money Trace — app

React Native (Expo) client for the Money Trace backend. Reads a static JSON API from this same repo.
**Source only — nothing here is compiled, built, or signed.**

## Screens

| Tab | What it shows |
| --- | --- |
| **Today** | Headline, AI brief bullets, risk-appetite gauge, breadth, index tape, largest estimated inflows/outflows, who drove the session, multi-day flow streaks, tomorrow's watchlist |
| **Rotation** | Sector rotation quadrants, cross-asset strip (yields, dollar, VIX, commodities, credit, crypto), 12 tech stacks with breadth and leaders, unusual activity |
| **Archive** | Every stored session, tap for the day's brief and top flows |

## Run it

```powershell
cd app
npm install
npm start
```

Then scan the QR code with **Expo Go** (Android/iOS) or press `w` for the web preview. No Xcode, no
Android SDK, no signing — Expo Go loads the JS bundle directly.

To typecheck only (optional):

```powershell
npm run typecheck
```

## Configure it first

Open [`src/config.ts`](src/config.ts) and set your repo:

```ts
export const REPO_OWNER = "your-github-username";
export const REPO_NAME = "money-trace";
```

Default data source: `https://raw.githubusercontent.com/<owner>/<repo>/main/docs/v1`.

If your repo is **private**, `raw.githubusercontent` returns 404 for anonymous requests. Enable
Pages (Settings → Pages → Deploy from a branch → `main` / `docs`), then set `USE_PAGES = true` in the
same file. Pages serves the same files at `https://<owner>.github.io/<repo>/v1`.

## Data contract

`docs/v1/latest.json` and `docs/v1/sessions/<date>.json` share one shape:

```
schema           1
session          { date, status, timezone, generated_at }
headline, regime { score, tone }, breadth { pct_up, ... }
tape[]           indexes
groups[]         net flow by asset class
flows            { in: [], out: [] }
sectors[]        rotation + quadrant
drivers[]        share of the session's dollar-weighted move
stacks[]         tech themes with breadth, leader, laggard
macro[], crypto[] levels and moves
movers[]         unusual activity
streaks[]        multi-session flow persistence
brief            { headline, tldr[], key_tech[], risks[], watch_tomorrow[] }
meta             { instruments, history_sessions, model, cost_usd }
disclaimer
```

`docs/v1/index.json` lists every session for the Archive tab.

Types live in [`src/api.ts`](src/api.ts) and mirror `backend/moneytrace/publish.py`. Change both together.

## Structure

```
App.tsx                 state, tabs, pull-to-refresh, error/loading
src/config.ts           repo + API base
src/api.ts              types, fetch, error taxonomy
src/theme.ts            colours, spacing
src/format.ts           percent / dollar / basis-point formatting
src/components/         Card, Stat, SectionHeader, Pill, Bar, FlowRow, TapeStrip, ErrorView, Loading, TabBar
src/screens/            TodayScreen, RotationScreen, ArchiveScreen
```

## Notes

- No state library, no navigation library, no chart library — three tabs and `useState`.
- Pull down to refresh; the app appends a cache-buster so GitHub's 5-minute cache does not serve yesterday.
- Everything is dark-mode first.
