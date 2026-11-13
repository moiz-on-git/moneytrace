import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { colors, radius, space } from "../theme";

export type PillTone = "up" | "down" | "neutral" | "warn" | "accent";

const TONES: Record<PillTone, { fg: string; bg: string }> = {
  up: { fg: colors.up, bg: "rgba(46,212,122,0.12)" },
  down: { fg: colors.down, bg: "rgba(255,92,92,0.12)" },
  neutral: { fg: colors.muted, bg: "rgba(138,150,168,0.12)" },
  warn: { fg: colors.warn, bg: "rgba(245,181,68,0.12)" },
  accent: { fg: colors.accent, bg: "rgba(76,141,255,0.12)" },
};

export function Pill({ label, tone = "neutral" }: { label: string; tone?: PillTone }) {
  const palette = TONES[tone];
  return (
    <View style={[styles.pill, { backgroundColor: palette.bg }]}>
      <Text style={[styles.text, { color: palette.fg }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    paddingHorizontal: space(2.5),
    paddingVertical: space(1),
    borderRadius: radius.pill,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: 11,
    fontWeight: "600",
    letterSpacing: 0.4,
  },
});
