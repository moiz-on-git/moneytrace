import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { colors, space } from "../theme";

type Props = {
  label: string;
  value: string;
  hint?: string;
  color?: string;
  align?: "left" | "center";
};

export function Stat({ label, value, hint, color, align = "left" }: Props) {
  return (
    <View style={[styles.wrap, align === "center" && styles.center]}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, color ? { color } : null]}>{value}</Text>
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    gap: space(0.5),
  },
  center: {
    alignItems: "center",
  },
  label: {
    color: colors.faint,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  value: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "600",
    fontVariant: ["tabular-nums"],
  },
  hint: {
    color: colors.muted,
    fontSize: 11,
  },
});
