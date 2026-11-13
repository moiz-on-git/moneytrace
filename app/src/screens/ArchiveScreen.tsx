import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import type { ApiError, ArchiveIndex, Snapshot } from "../api";
import { getSession } from "../api";
import { Card } from "../components/Card";
import { FlowRow } from "../components/FlowRow";
import { Pill } from "../components/Pill";
import { SectionHeader } from "../components/SectionHeader";
import { money, pct, prettyDate, toneColor } from "../format";
import { colors, radius, space } from "../theme";

function regimeTone(regime: string | null) {
  if (regime === "risk-on") return "up" as const;
  if (regime === "risk-off") return "down" as const;
  return "warn" as const;
}

export function ArchiveScreen({ index }: { index: ArchiveIndex }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = useCallback(() => {
    setSelected(null);
    setDetail(null);
    setError(null);
  }, []);

  useEffect(() => {
    if (!selected) return;
    const date = selected;
    let alive = true;
    setLoading(true);
    setError(null);
    setDetail(null);

    getSession(date)
      .then((snapshot) => {
        if (alive) setDetail(snapshot);
      })
      .catch((err: ApiError) => {
        if (alive) setError(err.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [selected]);

  const maxFlow = detail
    ? Math.max(1, ...detail.flows.in.concat(detail.flows.out).map((f) => Math.abs(f.flow ?? 0)))
    : 1;

  return (
    <View style={styles.root}>
      <SectionHeader title="Archive" right={`${index.sessions.length} sessions`} />
      <Card style={styles.list}>
        {index.sessions.map((entry) => (
          <Pressable
            key={entry.date}
            onPress={() => setSelected(entry.date)}
            style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
          >
            <View style={styles.rowTop}>
              <Text style={styles.date}>{prettyDate(entry.date)}</Text>
              <Pill label={(entry.regime ?? "n/a").toUpperCase()} tone={regimeTone(entry.regime)} />
              <Text style={[styles.spy, { color: toneColor(entry.spy) }]}>{pct(entry.spy)}</Text>
            </View>
            <Text style={styles.headline} numberOfLines={2}>
              {entry.headline || "No headline"}
            </Text>
          </Pressable>
        ))}
      </Card>

      <Modal visible={selected !== null} animationType="slide" transparent onRequestClose={close}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <View>
                <Text style={styles.modalTitle}>{prettyDate(selected)}</Text>
                <Text style={styles.modalSub}>{selected}</Text>
              </View>
              <Pressable onPress={close} hitSlop={12} style={styles.closeButton}>
                <Text style={styles.closeText}>Close</Text>
              </Pressable>
            </View>

            {loading ? (
              <View style={styles.modalBody}>
                <ActivityIndicator color={colors.accent} />
              </View>
            ) : error ? (
              <View style={styles.modalBody}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            ) : detail ? (
              <ScrollView contentContainerStyle={styles.modalScroll} showsVerticalScrollIndicator={false}>
                <Text style={styles.modalHeadline}>{detail.headline}</Text>

                {detail.brief.tldr && detail.brief.tldr.length > 0 ? (
                  <View style={styles.tldr}>
                    {detail.brief.tldr.map((line, i) => (
                      <Text key={i} style={styles.tldrLine}>
                        · {line}
                      </Text>
                    ))}
                  </View>
                ) : null}

                <View style={styles.modalStats}>
                  <View style={styles.modalStat}>
                    <Text style={styles.modalStatLabel}>SPY</Text>
                    <Text style={[styles.modalStatValue, { color: toneColor(detail.tape[0]?.chg ?? null) }]}>
                      {pct(detail.tape[0]?.chg ?? null)}
                    </Text>
                  </View>
                  <View style={styles.modalStat}>
                    <Text style={styles.modalStatLabel}>Breadth</Text>
                    <Text style={styles.modalStatValue}>{detail.breadth ? `${detail.breadth.pct_up}%` : "–"}</Text>
                  </View>
                  <View style={styles.modalStat}>
                    <Text style={styles.modalStatLabel}>Regime</Text>
                    <Text style={styles.modalStatValue}>
                      {detail.regime ? `${Math.round(detail.regime.score)}` : "–"}
                    </Text>
                  </View>
                </View>

                <Text style={styles.modalSection}>Top inflows</Text>
                {detail.flows.in.slice(0, 3).map((item) => (
                  <FlowRow key={`d-in-${item.symbol}`} item={item} maxFlow={maxFlow} />
                ))}

                <Text style={styles.modalSection}>Top outflows</Text>
                {detail.flows.out.slice(0, 3).map((item) => (
                  <FlowRow key={`d-out-${item.symbol}`} item={item} maxFlow={maxFlow} />
                ))}

                <Text style={styles.modalFooter}>{money(detail.flows.in[0]?.flow ?? 0)} largest estimated inflow</Text>
              </ScrollView>
            ) : null}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: space(3),
  },
  list: {
    paddingVertical: space(1),
  },
  row: {
    paddingVertical: space(3),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    gap: space(1.5),
  },
  rowPressed: {
    opacity: 0.6,
  },
  rowTop: {
    flexDirection: "row",
    alignItems: "center",
    gap: space(2),
  },
  date: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "700",
    flex: 1,
  },
  spy: {
    fontSize: 12,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  headline: {
    color: colors.muted,
    fontSize: 12,
    lineHeight: 17,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "flex-end",
  },
  modalCard: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    maxHeight: "88%",
    paddingTop: space(5),
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: space(5),
    paddingBottom: space(3),
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  modalTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "700",
  },
  modalSub: {
    color: colors.faint,
    fontSize: 11,
    marginTop: space(0.5),
  },
  closeButton: {
    backgroundColor: colors.card,
    paddingHorizontal: space(3),
    paddingVertical: space(1.5),
    borderRadius: radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  closeText: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: "600",
  },
  modalBody: {
    padding: space(6),
    alignItems: "center",
  },
  modalScroll: {
    padding: space(5),
    paddingBottom: space(10),
    gap: space(2),
  },
  modalHeadline: {
    color: colors.text,
    fontSize: 18,
    lineHeight: 24,
    fontWeight: "700",
  },
  tldr: {
    gap: space(1.5),
    marginTop: space(2),
  },
  tldrLine: {
    color: colors.muted,
    fontSize: 12.5,
    lineHeight: 18,
  },
  modalStats: {
    flexDirection: "row",
    marginTop: space(3),
    backgroundColor: colors.card,
    borderRadius: radius.card,
    padding: space(3),
  },
  modalStat: {
    flex: 1,
    alignItems: "center",
    gap: space(0.5),
  },
  modalStatLabel: {
    color: colors.faint,
    fontSize: 10,
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  modalStatValue: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  modalSection: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 1.4,
    textTransform: "uppercase",
    marginTop: space(4),
  },
  modalFooter: {
    color: colors.faint,
    fontSize: 10,
    marginTop: space(5),
  },
  errorText: {
    color: colors.down,
    fontSize: 13,
    textAlign: "center",
  },
});
