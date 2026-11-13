import { colors } from "./theme";

/** +1.23% / -0.45% / dash */
export function pct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(digits)}%`;
}

/** +10bp */
export function bps(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded}bp`;
}

/** +$19.3B / -$4.33B */
export function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  const sign = value < 0 ? "-" : "+";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

export function compactNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "–";
  if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return value.toFixed(digits);
}

export function toneColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return colors.flat;
  if (value > 0) return colors.up;
  if (value < 0) return colors.down;
  return colors.flat;
}

export function regimeColor(tone: string | null | undefined): string {
  switch ((tone || "").toLowerCase()) {
    case "risk-on":
      return colors.up;
    case "risk-off":
      return colors.down;
    default:
      return colors.warn;
  }
}

/** "2026-11-12" -> "Thu 12 Nov" */
export function prettyDate(iso: string | null | undefined): string {
  if (!iso) return "–";
  const parsed = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

/** ISO timestamp -> "3h ago" */
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "";
  const hours = (Date.now() - parsed.getTime()) / 36e5;
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m ago`;
  if (hours < 24) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
