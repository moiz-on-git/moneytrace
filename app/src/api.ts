import { API_BASE, IS_CONFIGURED, REQUEST_TIMEOUT_MS } from "./config";

/* ------------------------------------------------------------------ types */
/* These mirror backend/moneytrace/publish.py. Keep them in sync. */

export type Flow = {
  symbol: string;
  name: string;
  group: string;
  chg: number | null;
  flow: number | null;
  rvol: number | null;
  chg5: number | null;
};

export type Sector = {
  symbol: string;
  name: string;
  chg: number | null;
  chg5: number | null;
  chg20: number | null;
  flow: number | null;
  flow5: number | null;
  rvol: number | null;
  rs5: number | null;
  quadrant: string | null;
};

export type Driver = {
  symbol: string;
  name: string;
  group: string;
  chg: number | null;
  share: number | null;
  weight: number | null;
  flow: number | null;
  rvol: number | null;
};

export type Leader = { symbol: string; ret1: number };

export type Stack = {
  label: string;
  chg: number | null;
  chg5: number | null;
  flow: number | null;
  breadth: number | null;
  tickers: string[];
  leader: Leader | null;
  laggard: Leader | null;
};

export type Macro = {
  symbol: string;
  name: string;
  kind: string;
  level: number | null;
  chg: number | null;
  chg5: number | null;
  chg20: number | null;
  chg_bps: number | null;
  chg5_bps: number | null;
  chg20_bps: number | null;
};

export type Crypto = {
  symbol: string;
  name: string;
  close: number | null;
  chg: number | null;
  chg5: number | null;
  chg20: number | null;
  flow: number | null;
  rvol: number | null;
};

export type Streak = { symbol: string; name: string; days: number; cum: number | null };

export type TapeItem = { symbol: string; name: string; close: number | null; chg: number | null; chg5: number | null };

export type GroupFlow = { group: string; flow: number | null; avg_chg: number | null; dv: number | null };

export type Brief = {
  regime?: string;
  headline?: string;
  tldr?: string[];
  where_money_moved?: { direction: string; theme: string; evidence: string; vehicles: string[] }[];
  who_is_driving?: { name: string; why: string }[];
  key_tech?: { tech: string; signal: string; tickers: string[] }[];
  stocks?: { ticker: string; note: string }[];
  risks?: string[];
  watch_tomorrow?: string[];
  generated_by?: string;
};

export type Regime = { score: number; tone: string; risk_on_rank?: number; risk_off_rank?: number } | null;

export type Breadth = {
  n: number;
  advancers: number;
  decliners: number;
  pct_up: number;
  pct_above20: number;
  median_move: number;
  dollar_breadth?: number | null;
} | null;

export type Snapshot = {
  schema: number;
  session: { date: string; status: string | null; timezone: string | null; generated_at: string | null };
  headline: string;
  regime: Regime;
  breadth: Breadth;
  tape: TapeItem[];
  groups: GroupFlow[];
  flows: { in: Flow[]; out: Flow[] };
  sectors: Sector[];
  drivers: Driver[];
  stacks: Stack[];
  macro: Macro[];
  crypto: Crypto[];
  movers: Flow[];
  streaks: Streak[];
  brief: Brief;
  meta: { instruments: number | null; history_sessions: number | null; model: string | null; cost_usd: number | null };
  disclaimer: string;
};

export type ArchiveEntry = {
  date: string;
  headline: string;
  regime: string | null;
  regime_score: number | null;
  spy: number | null;
  pct_up: number | null;
};

export type ArchiveIndex = {
  schema: number;
  updated_at: string | null;
  latest: string;
  sessions: ArchiveEntry[];
};

/* ----------------------------------------------------------------- errors */

export type FailureKind = "config" | "network" | "http" | "parse";

export class ApiError extends Error {
  kind: FailureKind;

  constructor(kind: FailureKind, message: string) {
    super(message);
    this.kind = kind;
    this.name = "ApiError";
  }
}

/* ------------------------------------------------------------------ fetch */

async function fetchJSON<T>(path: string, bustCache = false): Promise<T> {
  if (!IS_CONFIGURED) {
    throw new ApiError("config", "Set REPO_OWNER in app/src/config.ts to your GitHub username.");
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const url = `${API_BASE}${path}${bustCache ? `?cb=${Date.now()}` : ""}`;

  try {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new ApiError(
          "http",
          "No data at that URL yet. Push the repo, then run the daily-brief workflow once.",
        );
      }
      throw new ApiError("http", `GitHub returned ${response.status}.`);
    }

    const text = await response.text();
    try {
      return JSON.parse(text) as T;
    } catch {
      throw new ApiError("parse", "The response was not valid JSON.");
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if ((error as Error).name === "AbortError") {
      throw new ApiError("network", "Request timed out. Check your connection.");
    }
    throw new ApiError("network", "Could not reach GitHub. Check your connection.");
  } finally {
    clearTimeout(timer);
  }
}

export const getLatest = (bustCache = false) => fetchJSON<Snapshot>("/latest.json", bustCache);
export const getIndex = (bustCache = false) => fetchJSON<ArchiveIndex>("/index.json", bustCache);
export const getSession = (date: string) => fetchJSON<Snapshot>(`/sessions/${date}.json`);
