import React from "react";
import { StyleSheet, Text, View } from "react-native";

import type { Snapshot } from "../api";
import { Bar } from "../components/Bar";
import { Card } from "../components/Card";
import { FlowRow } from "../components/FlowRow";
import { Pill } from "../components/Pill";
import { SectionHeader } from "../components/SectionHeader";
import { Stat } from "../components/Stat";
import { TapeStrip } from "../components/TapeStrip";
import { money, pct, prettyDate, regimeColor, timeAgo, toneColor } from "../format";
import { colors, space } from "../theme";

export function TodayScreen({ data }: { data: Snapshot }) {
  const inflow = data.flows.in.slice(0, 4);
  const outflow = data.flows.out.slice(0, 4);
  const maxFlow = Math.max(1, ...inflow.concat(outflow).map((f) => Math.abs(f.flow ?? 0)));

  const breadth = data.breadth;
  const regime = data.regime;
  const brief = data.brief;
  const tldr = brief.tldr ?? [];
  const watch = brief.watch_tomorrow ?? [];
  const risks = brief.risks ?? [];

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Text style={styles.wordmark}>MONEY TRACE</Text>
        <Text style={styles.session}>
          {prettyDate(data.session.date)} · {data.session.status ?? "session"} · {timeAgo(data.session.generated_at)}
        </Text>
      </View>

      <Text style={styles.headline}>{data.headline || "No headline for this session."}</Text>

      {regime ? (
        <Card style={styles.regimeCard}>
          <View style={styles.regimeTop}>
            <View>
              <Text style={styles.caption}>RISK APPETITE</Text>
              <Text style={[styles.regimeScore, { color: regimeColor(regime.tone) }]}>
                {Math.round(regime.score)}
                <Text style={styles.regimeOutOf}> / 100</Text>
              </Text>
            </View>
            <Pill label={regime.tone.toUpperCase()} tone={regime.tone === "risk-on" ? "up" : regime.tone === "risk-off" ? "down" : "warn"} />
          </View>
          <Bar value={regime.score / 100} color={regimeColor(regime.tone)} height={6} />
        </Card>
      ) : null}

      {breadth ? (
        <Card style={styles.breadth}>
          <Stat label="Advancing" value={`${breadth.pct_up}%`} hint={`${breadth.advancers} up / ${breadth.decliners} down`} />
          <Stat label="Above 20d" value={`${breadth.pct_above20}%`} hint={`${breadth.n} instruments`} />
          <Stat
            label="Median"
            value={pct(breadth.median_move)}
            color={toneColor(breadth.median_move)}
            hint="stock move"
          />
        </Card>
      ) : null}

      <View style={styles.tape}>
        <TapeStrip items={data.tape} />
      </View>

      {tldr.length > 0 ? (
        <Card style={styles.tldrCard}>
          {tldr.map((line, index) => (
            <View key={index} style={styles.tldrRow}>
              <Text style={styles.bullet}>·</Text>
              <Text style={styles.tldrText}>{line}</Text>
            </View>
          ))}
        </Card>
      ) : null}

      <SectionHeader title="Where money moved" right={`${data.meta.instruments ?? 0} instruments`} />
      <Card style={styles.flows}>
        <Text style={styles.groupLabel}>IN</Text>
        {inflow.map((item) => (
          <FlowRow key={`in-${item.symbol}`} item={item} maxFlow={maxFlow} />
        ))}
        <Text style={[styles.groupLabel, styles.groupLabelOut]}>OUT</Text>
        {outflow.map((item) => (
          <FlowRow key={`out-${item.symbol}`} item={item} maxFlow={maxFlow} />
        ))}
      </Card>

      {data.drivers.length > 0 ? (
        <>
          <SectionHeader title="Who is driving" right="share of move" />
          <Card>
            {data.drivers.slice(0, 5).map((driver) => (
              <View key={driver.symbol} style={styles.driver}>
                <View style={styles.driverTop}>
                  <Text style={styles.driverSymbol}>{driver.symbol}</Text>
                  <Text style={[styles.driverChg, { color: toneColor(driver.chg) }]}>{pct(driver.chg)}</Text>
                  <Text style={styles.driverShare}>{driver.share?.toFixed(1)}%</Text>
                </View>
                <Bar
                  value={(driver.share ?? 0) / 100}
                  color={driver.chg !== null && driver.chg < 0 ? colors.down : colors.up}
                  height={3}
                />
              </View>
            ))}
          </Card>
        </>
      ) : null}

      {data.streaks.length > 0 ? (
        <>
          <SectionHeader title="Persistent flow" right="multi-session" />
          <Card>
            {data.streaks.slice(0, 4).map((streak) => (
              <View key={streak.symbol} style={styles.streakRow}>
                <Text style={styles.streakSymbol}>{streak.symbol}</Text>
                <Text style={styles.streakName} numberOfLines={1}>
                  {streak.name}
                </Text>
                <Text style={[styles.streakDays, { color: streak.days > 0 ? colors.up : colors.down }]}>
                  {Math.abs(streak.days)}d {streak.days > 0 ? "in" : "out"}
                </Text>
                <Text style={styles.streakCum}>{money(streak.cum)}</Text>
              </View>
            ))}
          </Card>
        </>
      ) : null}

      {watch.length > 0 || risks.length > 0 ? (
        <>
          <SectionHeader title="Watch next" />
          <Card style={styles.watchCard}>
            {watch.map((line, index) => (
              <View key={`w-${index}`} style={styles.watchRow}>
                <Text style={styles.watchIndex}>{String(index + 1).padStart(2, "0")}</Text>
                <Text style={styles.watchText}>{line}</Text>
              </View>
            ))}
            {risks.map((line, index) => (
              <View key={`r-${index}`} style={styles.watchRow}>
                <Text style={[styles.watchIndex, styles.riskIndex]}>!</Text>
                <Text style={[styles.watchText, styles.riskText]}>{line}</Text>
              </View>
            ))}
          </Card>
        </>
      ) : null}

      <Text style={styles.footer}>
        {data.meta.model ? `Written by ${data.meta.model}` : "Written from templates"} · {data.disclaimer}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: space(3),
  },
  header: {
    gap: space(1),
    marginBottom: space(1),
  },
  wordmark: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 3,
  },
  session: {
    color: colors.faint,
    fontSize: 12,
  },
  headline: {
    color: colors.text,
    fontSize: 22,
    lineHeight: 29,
    fontWeight: "700",
    letterSpacing: -0.2,
    marginBottom: space(1),
  },
  caption: {
    color: colors.faint,
    fontSize: 10,
    letterSpacing: 1.2,
    marginBottom: space(1),
  },
  regimeCard: {
    gap: space(3),
  },
  regimeTop: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
  },
  regimeScore: {
    fontSize: 28,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
  },
  regimeOutOf: {
    fontSize: 13,
    fontWeight: "500",
    color: colors.faint,
  },
  breadth: {
    flexDirection: "row",
    gap: space(3),
  },
  tape: {
    marginHorizontal: -space(4),
    paddingHorizontal: space(4),
  },
  tldrCard: {
    gap: space(2.5),
  },
  tldrRow: {
    flexDirection: "row",
    gap: space(2),
  },
  bullet: {
    color: colors.accent,
    fontSize: 16,
    lineHeight: 20,
  },
  tldrText: {
    flex: 1,
    color: colors.text,
    fontSize: 13.5,
    lineHeight: 20,
  },
  flows: {
    paddingVertical: space(1),
  },
  groupLabel: {
    color: colors.up,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.4,
    marginTop: space(2),
  },
  groupLabelOut: {
    color: colors.down,
    marginTop: space(4),
  },
  driver: {
    gap: space(1.5),
    marginBottom: space(3),
  },
  driverTop: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: space(2),
  },
  driverSymbol: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "700",
  },
  driverChg: {
    flex: 1,
    fontSize: 12,
    fontVariant: ["tabular-nums"],
  },
  driverShare: {
    color: colors.muted,
    fontSize: 12,
    fontVariant: ["tabular-nums"],
  },
  streakRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: space(2),
    paddingVertical: space(2),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  streakSymbol: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "700",
    width: 64,
  },
  streakName: {
    flex: 1,
    color: colors.muted,
    fontSize: 11,
  },
  streakDays: {
    fontSize: 11,
    fontWeight: "700",
    width: 52,
    textAlign: "right",
  },
  streakCum: {
    color: colors.muted,
    fontSize: 11,
    width: 62,
    textAlign: "right",
    fontVariant: ["tabular-nums"],
  },
  watchCard: {
    gap: space(2.5),
  },
  watchRow: {
    flexDirection: "row",
    gap: space(2.5),
  },
  watchIndex: {
    color: colors.accent,
    fontSize: 11,
    fontWeight: "800",
    width: 18,
    fontVariant: ["tabular-nums"],
  },
  riskIndex: {
    color: colors.warn,
  },
  watchText: {
    flex: 1,
    color: colors.text,
    fontSize: 13,
    lineHeight: 19,
  },
  riskText: {
    color: colors.muted,
  },
  footer: {
    color: colors.faint,
    fontSize: 10,
    lineHeight: 15,
    marginTop: space(4),
  },
});
