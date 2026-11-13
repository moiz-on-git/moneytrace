import React from "react";
import { StyleSheet, Text, View } from "react-native";

import { colors, space } from "../theme";

type Props = {
  title: string;
  right?: string;
};

export function SectionHeader({ title, right }: Props) {
  return (
    <View style={styles.row}>
      <Text style={styles.title}>{title.toUpperCase()}</Text>
      {right ? <Text style={styles.right}>{right}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    marginBottom: space(2.5),
    marginTop: space(1),
  },
  title: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1.6,
  },
  right: {
    color: colors.faint,
    fontSize: 11,
  },
});
