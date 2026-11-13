import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";

import type { TapeItem } from "../api";
import { pct, toneColor } from "../format";
import { colors, radius, space } from "../theme";

export function TapeStrip({ items }: { items: TapeItem[] }) {
  if (items.length === 0) return null;

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.content}
    >
      {items.map((item) => (
        <View key={item.symbol} style={styles.cell}>
          <Text style={styles.symbol}>{item.symbol}</Text>
          <Text style={[styles.chg, { color: toneColor(item.chg) }]}>{pct(item.chg)}</Text>
          <Text style={styles.week}>{pct(item.chg5, 1)} · 5d</Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: space(2),
    paddingRight: space(2),
  },
  cell: {
    backgroundColor: colors.cardAlt,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingVertical: space(2.5),
    paddingHorizontal: space(3),
    minWidth: 92,
    gap: space(0.5),
  },
  symbol: {
    color: colors.muted,
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 1,
  },
  chg: {
    fontSize: 16,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  week: {
    color: colors.faint,
    fontSize: 10,
    fontVariant: ["tabular-nums"],
  },
});
