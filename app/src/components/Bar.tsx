import React from "react";
import { StyleSheet, View } from "react-native";

import { colors } from "../theme";

type Props = {
  /** 0..1 */
  value: number;
  color?: string;
  height?: number;
  trackColor?: string;
};

export function Bar({ value, color = colors.accent, height = 4, trackColor = colors.track }: Props) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
  const width = `${clamped * 100}%` as `${number}%`;
  return (
    <View style={[styles.track, { height, backgroundColor: trackColor }]}>
      <View style={{ width, height, backgroundColor: color, borderRadius: height / 2 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    width: "100%",
    borderRadius: 999,
    overflow: "hidden",
  },
});
