import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, space } from "../theme";

export type TabKey = "today" | "rotation" | "archive";

const TABS: { key: TabKey; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "rotation", label: "Rotation" },
  { key: "archive", label: "Archive" },
];

type Props = {
  value: TabKey;
  onChange: (tab: TabKey) => void;
};

export function TabBar({ value, onChange }: Props) {
  return (
    <View style={styles.bar}>
      {TABS.map((tab) => {
        const active = tab.key === value;
        return (
          <Pressable key={tab.key} style={styles.item} onPress={() => onChange(tab.key)}>
            <Text style={[styles.label, active && styles.labelActive]}>{tab.label}</Text>
            <View style={[styles.dot, active && styles.dotActive]} />
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: "row",
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    backgroundColor: colors.bg,
    paddingTop: space(2.5),
    paddingBottom: space(6),
  },
  item: {
    flex: 1,
    alignItems: "center",
    gap: space(1.5),
  },
  label: {
    color: colors.faint,
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.4,
  },
  labelActive: {
    color: colors.text,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: "transparent",
  },
  dotActive: {
    backgroundColor: colors.accent,
  },
});
