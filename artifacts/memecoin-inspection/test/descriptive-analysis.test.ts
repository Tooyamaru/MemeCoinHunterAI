import assert from "node:assert/strict";
import test from "node:test";
import type { InspectionPair } from "@workspace/api-client-react";
import {
  summarizeActivity,
  summarizeAvailability,
} from "../src/descriptive-analysis";

function pair(overrides: Partial<InspectionPair> = {}): InspectionPair {
  return {
    priceUsd: "1.25",
    liquidity: { usd: "500.00", base: "10", quote: "20" },
    volume: { h24: "1000" },
    txns: { h24: { buys: "16", sells: "17" } },
    pairCreatedAt: "1700000000000",
    inspection: { field_provenance: {}, findings: [] },
    ...overrides,
  };
}

test("summarizes normal and one-sided-zero 24h counts", () => {
  assert.deepEqual(summarizeActivity(pair()).buyShare, {
    status: "available",
    value: "48.5%",
  });
  assert.equal(
    summarizeActivity(pair({ txns: { h24: { buys: "0", sells: "10" } } })).buyShare.value,
    "0.0%",
  );
});

test("keeps all-zero counts explicit instead of dividing by zero", () => {
  const summary = summarizeActivity(
    pair({ txns: { h24: { buys: "0", sells: "0" } } }),
  );
  assert.equal(summary.total.value, "0");
  assert.equal(summary.buyShare.status, "unavailable");
  assert.equal(summary.buyShare.detail, "Unavailable — no transactions");
});

test("does not turn missing, null, malformed, or negative counts into zero", () => {
  for (const txns of [
    undefined,
    { h24: null },
    { h24: { buys: null, sells: null } },
    { h24: { buys: "not-a-number", sells: "2" } },
    { h24: { buys: "-1", sells: "2" } },
  ]) {
    const summary = summarizeActivity(pair({ txns }));
    assert.notEqual(summary.total.value, "0");
    assert.notEqual(summary.buyShare.value, "0.0%");
  }
  assert.equal(
    summarizeActivity(pair({ txns: undefined })).total.status,
    "unavailable",
  );
  assert.equal(
    summarizeActivity(pair({ txns: { h24: { buys: "bad", sells: "2" } } })).total.status,
    "invalid",
  );
});

test("preserves very large integers and rounds percentage deterministically", () => {
  const largeBuys = "1" + "0".repeat(30);
  const summary = summarizeActivity(
    pair({ txns: { h24: { buys: largeBuys, sells: "1" } } }),
  );
  assert.equal(summary.buys.value, "1,000,000,000,000,000,000,000,000,000,000");
  assert.equal(summary.total.value, "1,000,000,000,000,000,000,000,000,000,001");
  assert.equal(
    summarizeActivity(pair({ txns: { h24: { buys: "1", sells: "63" } } })).buyShare.value,
    "1.6%",
  );
});

test("distinguishes available, unavailable, and invalid descriptive fields", () => {
  const summaries = summarizeAvailability(
    pair({
      priceUsd: "not-a-number",
      liquidity: null,
      volume: { h24: null },
      pairCreatedAt: null,
    }),
  );
  assert.deepEqual(
    summaries.map(({ label, metric }) => [label, metric.status]),
    [
      ["USD price", "invalid"],
      ["Current USD liquidity", "unavailable"],
      ["Source-reported 24h volume", "unavailable"],
      ["Source-reported 24h buy/sell counts", "available"],
      ["Pair creation time", "unavailable"],
    ],
  );
  assert.equal(summaries[1].metric.value, null);
});

test("uses an invalid numeric finding when the source value is otherwise string-shaped", () => {
  const summaries = summarizeAvailability(
    pair({
      inspection: {
        field_provenance: {},
        findings: [
          {
            code: "INVALID_NUMERIC_FIELD",
            source_field: "pairs[0].liquidity.usd",
            value: "NaN",
          },
        ],
      },
    }),
  );
  assert.equal(summaries[1].metric.status, "invalid");
});