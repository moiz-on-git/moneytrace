import React, { useCallback, useEffect, useState } from "react";
import { Platform, RefreshControl, ScrollView, StatusBar, StyleSheet, Text, View } from "react-native";

import { ApiError, getIndex, getLatest } from "./src/api";
import type { ArchiveIndex, Snapshot } from "./src/api";
import { ErrorView } from "./src/components/ErrorView";
import { Loading } from "./src/components/Loading";
import { TabBar } from "./src/components/TabBar";
import type { TabKey } from "./src/components/TabBar";
import { ArchiveScreen } from "./src/screens/ArchiveScreen";
import { RotationScreen } from "./src/screens/RotationScreen";
import { TodayScreen } from "./src/screens/TodayScreen";
import { colors, space } from "./src/theme";

const TOP_PADDING = Platform.OS === "android" ? StatusBar.currentHeight ?? 24 : 56;

export default function App() {
  const [tab, setTab] = useState<TabKey>("today");
  const [data, setData] = useState<Snapshot | null>(null);
  const [index, setIndex] = useState<ArchiveIndex | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (bustCache: boolean) => {
    setError(null);
    try {
      const latest = await getLatest(bustCache);
      setData(latest);
      try {
        const archive = await getIndex(bustCache);
        setIndex(archive);
      } catch {
        // The archive tab is optional; the rest of the app still works.
      }
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError("network", "Unexpected error."));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load(false);
  }, [load]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    void load(true);
  }, [load]);

  const onRetry = useCallback(() => {
    setLoading(true);
    void load(true);
  }, [load]);

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={colors.bg} />
      <View style={{ height: TOP_PADDING }} />

      {loading && !data ? <Loading /> : null}

      {!loading && error && !data ? <ErrorView error={error} onRetry={onRetry} /> : null}

      {data ? (
        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={colors.muted}
              colors={[colors.accent]}
              progressBackgroundColor={colors.card}
            />
          }
        >
          {tab === "today" ? <TodayScreen data={data} /> : null}
          {tab === "rotation" ? <RotationScreen data={data} /> : null}
          {tab === "archive" ? (
            index ? (
              <ArchiveScreen index={index} />
            ) : (
              <Text style={styles.empty}>Archive has not been published yet.</Text>
            )
          ) : null}
        </ScrollView>
      ) : null}

      <TabBar value={tab} onChange={setTab} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    paddingHorizontal: space(4),
    paddingTop: space(3),
    paddingBottom: space(8),
  },
  empty: {
    color: colors.muted,
    fontSize: 13,
    paddingVertical: space(6),
  },
});
