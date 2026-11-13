import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import type { Crypto, Macro, Snapshot, Stack } from "../api";
import { Bar } from "../components/Bar";
import { Card } from "../components/Card";
import { FlowRow } from "../components/FlowRow";
import { Pill } from "../components/Pill";
import { SectionHeader } from "../components/SectionHeader";
import { bps, compactNumber, money, pct, toneColor } from "../format";
import { colors, space } from "../theme";

function quadrantTone(quadrant: string | null) {
  switch (quadrant) {
    case "leading":
      return "up" as const;
    case "accumulating":
      return "accent" as const;
    case "fading":
      return "warn" as const;
    case "lagging":
      return "down" as const;
    default:
      return "neutral" as const;
  }
}

function MacroCell({ item }: { item: Macro }) {
  const isRate = item.kind === "rate";
  const chg = isRate ? bps(item.chg_bps) : pct(item.chg);
  const raw = isRate ? item.chg_bps : item.chg;
  return (
    <View style={styles.macroCell}>
      <Text style={styles.macroLabel} numberOfLines={1}>
        {item.name}
      </Text>
      <Text style={styles.macroLevel}>{isRate ? `${item.level?.toFixed(2)}%` : compactNumber(item.level)}</Text>
      <Text style={[styles.macroChg, { color: toneColor(raw) }]}>{chg}</Text>
    </View>
  );
}

function CryptoCell({ item }: { item: Crypto }) {
  return (
    <View style={styles.macroCell}>
      <Text style={styles.macroLabel} numberOfLines={1}>
        {item.name}
      </Text>
      <Text style={styles.macroLevel}>
        {item.close === null ? "–" : `$${compactNumber(item.close, 0)}`}
      </Text>
      <Text style={[styles.macroChg, { color: toneColor(item.chg) }]}>{pct(item.chg)}</Text>
    </View>
  );
}

function StackCard({ stack }: { stack: Stack }) {
  return (
    <View style={styles.stack}>
      <View style={styles.stackTop}>
        <Text style={styles.stackLabel}>{stack.label}</Text>
        <Text style={[styles.stackChg, { color: toneColor(stack.chg) }]}>{pct(stack.chg)}</Text>
      </View>
      <View style={styles.stackMeta}>
        <Text style={styles.stackMetaText}>{pct(stack.chg5)} · 5d</Text>
        <Text style={styles.stackMetaText}>{money(stack.flow)} est.</Text>
        <Text style={styles.stackMetaText}>{Math.round(stack.breadth ?? 0)}% up</Text>
      </View>
      <Bar value={(stack.breadth ?? 0) / 100} color={toneColor(stack.chg)} height={3} />
      {stack.leader || stack.laggard ? (
        <View style={styles.stackFooter}>
          <Text style={styles.stackFootText}>
            <Text style={{ color: colors.up }}>{stack.leader?.symbol ?? "–"}</Text> {pct(stack.leader?.ret1 ?? null)}
          </Text>
          <Text style={styles.stackFootText}>
            <Text style={{ color: colors.down }}>{stack.laggard?.symbol ?? "–"}</Text> {pct(stack.laggard?.ret1 ?? null)}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

export function RotationScreen({ data }: { data: Snapshot }) {
  const movers = data.movers.slice(0, 8);
  const maxMoverFlow = Math.max(1, ...movers.map((m) => Math.abs(m.flow ?? 0)));

  return (
    <View style={styles.root}>
      <SectionHeader title="Sector rotation" right="1d · 5d · flow" />
      <Card style={styles.sectorCard}>
        {data.sectors.map((sector) => (
          <View key={sector.symbol} style={styles.sectorRow}>
            <View style={styles.sectorLeft}>
              <Text style={styles.sectorName}>{sector.name}</Text>
              <Pill label={(sector.quadrant ?? "n/a").toUpperCase()} tone={quadrantTone(sector.quadrant)} />
            </View>
            <Text style={[styles.sectorChg, { color: toneColor(sector.chg) }]}>{pct(sector.chg, 1)}</Text>
            <Text style={[styles.sectorChg, { color: toneColor(sector.chg5) }]}>{pct(sector.chg5, 1)}</Text>
            <Text style={styles.sectorFlow}>{money(sector.flow)}</Text>
          </View>
        ))}
      </Card>

      <SectionHeader title="Cross-asset" right="level · move" />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.strip}>
        {data.macro.map((item) => (
          <MacroCell key={item.symbol} item={item} />
        ))}
        {data.crypto.map((item) => (
          <CryptoCell key={item.symbol} item={item} />
        ))}
      </ScrollView>

      <SectionHeader title="Key technologies" right={`${data.stacks.length} stacks`} />
      <Card style={styles.stackCard}>
        {data.stacks.map((stack) => (
          <StackCard key={stack.label} stack={stack} />
        ))}
      </Card>

      <SectionHeader title="Unusual activity" right="2%+ on 1.2x volume" />
      <Card style={styles.moversCard}>
        {movers.map((mover) => (
          <FlowRow key={mover.symbol} item={mover} maxFlow={maxMoverFlow} />
        ))}
      </Card>

      <Text style={styles.footer}>
        Share of move is activity share, not index weight. Flows are estimated from price and volume.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: space(3),
  },
  sectorCard: {
    paddingVertical: space(2),
  },
  sectorRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: space(2),
    paddingVertical: space(2.5),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  sectorLeft: {
    flex: 1,
    gap: space(1),
  },
  sectorName: {
    color: colors.text,
    fontSize: 13.5,
    fontWeight: "600",
  },
  sectorChg: {
    width: 58,
    textAlign: "right",
    fontSize: 12,
    fontVariant: ["tabular-nums"],
  },
  sectorFlow: {
    width: 74,
    textAlign: "right",
    fontSize: 11,
    color: colors.muted,
    fontVariant: ["tabular-nums"],
  },
  strip: {
    gap: space(2),
    paddingRight: space(2),
  },
  macroCell: {
    backgroundColor: colors.cardAlt,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: 10,
    paddingVertical: space(2.5),
    paddingHorizontal: space(3),
    minWidth: 104,
    gap: space(0.5),
  },
  macroLabel: {
    color: colors.faint,
    fontSize: 10,
    letterSpacing: 0.4,
  },
  macroLevel: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  macroChg: {
    fontSize: 11,
    fontVariant: ["tabular-nums"],
  },
  stackCard: {
    gap: space(3),
  },
  stack: {
    gap: space(2),
    paddingBottom: space(3),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  stackTop: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
  },
  stackLabel: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "700",
    flex: 1,
    paddingRight: space(2),
  },
  stackChg: {
    fontSize: 13,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  stackMeta: {
    flexDirection: "row",
    gap: space(3),
  },
  stackMetaText: {
    color: colors.muted,
    fontSize: 11,
    fontVariant: ["tabular-nums"],
  },
  stackFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  stackFootText: {
    color: colors.muted,
    fontSize: 11,
    fontVariant: ["tabular-nums"],
  },
  moversCard: {
    paddingVertical: space(1),
  },
  footer: {
    color: colors.faint,
    fontSize: 10,
    lineHeight: 15,
    marginTop: space(4),
  },
});
