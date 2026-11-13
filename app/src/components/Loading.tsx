import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { colors, space } from "../theme";

export function Loading({ label = "Loading the latest session" }: { label?: string }) {
  return (
    <View style={styles.wrap}>
      <ActivityIndicator color={colors.accent} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: space(3),
    padding: space(8),
  },
  label: {
    color: colors.muted,
    fontSize: 13,
  },
});
