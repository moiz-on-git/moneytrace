import React from "react";
import { StyleSheet, Text, View } from "react-native";

import type { Flow } from "../api";
import { money, pct, toneColor } from "../format";
import { colors, space } from "../theme";

type Props = {
  item: Flow;
  /** Largest absolute flow in the list, used to scale the underline. */
  maxFlow: number;
  showRvol?: boolean;
};

export function FlowRow({ item, maxFlow, showRvol = true }: Props) {
  const ratio = maxFlow > 0 ? Math.min(1, Math.abs(item.flow ?? 0) / maxFlow) : 0;
  const color = toneColor(item.chg);
  const width = `${ratio * 100}%` as `${number}%`;

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <View style={styles.left}>
          <View style={styles.symbolRow}>
            <Text style={styles.symbol}>{item.symbol}</Text>
            {showRvol && item.rvol !== null && item.rvol >= 1.5 ? (
              <Text style={styles.rvol}>{item.rvol.toFixed(1)}x</Text>
            ) : null}
          </View>
          <Text style={styles.name} numberOfLines={1}>
            {item.name}
          </Text>
        </View>
        <View style={styles.right}>
          <Text style={[styles.chg, { color }]}>{pct(item.chg)}</Text>
          <Text style={styles.flow}>{money(item.flow)}</Text>
        </View>
      </View>
      <View style={styles.underlineTrack}>
        <View
          style={[
            styles.underline,
            { width, backgroundColor: item.flow !== null && item.flow < 0 ? colors.down : colors.up },
          ]}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingVertical: space(2.5),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  left: {
    flex: 1,
    paddingRight: space(3),
  },
  symbolRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: space(1.5),
  },
  symbol: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700",
    letterSpacing: 0.3,
  },
  rvol: {
    color: colors.warn,
    fontSize: 10,
    fontWeight: "700",
    backgroundColor: "rgba(245,181,68,0.12)",
    paddingHorizontal: space(1.25),
    paddingVertical: space(0.25),
    borderRadius: 999,
    overflow: "hidden",
  },
  name: {
    color: colors.muted,
    fontSize: 12,
    marginTop: space(0.5),
  },
  right: {
    alignItems: "flex-end",
  },
  chg: {
    fontSize: 15,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  flow: {
    color: colors.muted,
    fontSize: 12,
    marginTop: space(0.5),
    fontVariant: ["tabular-nums"],
  },
  underlineTrack: {
    height: 2,
    marginTop: space(2),
    backgroundColor: colors.track,
    borderRadius: 999,
    overflow: "hidden",
  },
  underline: {
    height: 2,
    borderRadius: 999,
  },
});
