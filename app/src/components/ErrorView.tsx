import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { ApiError } from "../api";
import { IS_CONFIGURED, REPO_NAME, REPO_OWNER } from "../config";
import { colors, radius, space } from "../theme";

type Props = {
  error: ApiError;
  onRetry: () => void;
};

export function ErrorView({ error, onRetry }: Props) {
  const title =
    error.kind === "config"
      ? "One line to configure"
      : error.kind === "network"
        ? "Can't reach GitHub"
        : error.kind === "parse"
          ? "Bad response"
          : "No data yet";

  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{error.message}</Text>

      {!IS_CONFIGURED ? (
        <View style={styles.steps}>
          <Text style={styles.step}>1. Open app/src/config.ts</Text>
          <Text style={styles.step}>2. Set REPO_OWNER to your GitHub username</Text>
          <Text style={styles.step}>3. Set REPO_NAME if you named the repo differently</Text>
          <Text style={styles.step}>4. Reload the app</Text>
          <Text style={styles.code}>
            {REPO_OWNER}/{REPO_NAME}
          </Text>
        </View>
      ) : (
        <View style={styles.steps}>
          <Text style={styles.step}>Check that docs/v1/latest.json exists in the repo.</Text>
          <Text style={styles.step}>Run the daily-brief workflow once from the Actions tab.</Text>
          <Text style={styles.step}>If the repo is private, raw.githubusercontent will 404 — use Pages.</Text>
        </View>
      )}

      <Pressable style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]} onPress={onRetry}>
        <Text style={styles.buttonText}>Try again</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    justifyContent: "center",
    padding: space(6),
    gap: space(3),
  },
  title: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "700",
  },
  message: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
  },
  steps: {
    backgroundColor: colors.card,
    borderRadius: radius.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: space(4),
    gap: space(1.5),
  },
  step: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 19,
  },
  code: {
    color: colors.accent,
    fontSize: 12,
    marginTop: space(1),
  },
  button: {
    alignSelf: "flex-start",
    backgroundColor: colors.accent,
    borderRadius: radius.pill,
    paddingHorizontal: space(5),
    paddingVertical: space(2.5),
  },
  buttonPressed: {
    opacity: 0.7,
  },
  buttonText: {
    color: "#06101F",
    fontWeight: "700",
    fontSize: 13,
  },
});
