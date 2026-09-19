import assert from "node:assert/strict";
import test from "node:test";
import {
  composeOpportunityEvaluation,
  createOpportunityEvaluationRouter,
} from "../src/routes/opportunity-evaluation";
import type { OpportunityEvaluationInput } from "@workspace/api-zod";
import express from "express";
import { createServer, type Server } from "node:http";

const input = (overrides: Record<string, unknown> = {}) =>
  ({
    chainId: "ethereum",
    tokenAddress: "0xabc",
    pairIndex: 0,
    inspection: {
      report: {
        request: { chain_id: "ethereum", token_address: "0xabc" },
        receipt: { received_at: "2026-09-18T03:00:00.000Z" },
        payload: {
          pairs: [
            {
              pairAddress: "0xpair",
              chainId: "ethereum",
              baseToken: { address: "0xabc" },
              quoteToken: { address: "0xusd" },
            },
          ],
        },
      },
      temporal_evidence: {
        chain_id: "ethereum",
        token_identity: "0xabc",
        records: [
          {
            chain_id: "ethereum",
            token_identity: "0xabc",
            market_subject_id: "ethereum:0xpair",
            source_observed_at: null,
          },
        ],
      },
    },
    safety: {
      identity: { chain_id: "ethereum", token_address: "0xabc" },
      source: {
        received_at: "2026-09-18T03:00:00.000Z",
        source_observed_at: null,
      },
      evaluation: {
        status: "UNKNOWN",
        evidence_references: [],
      },
      evidence: [],
    },
    ...overrides,
  }) as unknown as OpportunityEvaluationInput;

test("composes a precise blocked result without requesting another provider report", () => {
  const result = composeOpportunityEvaluation(input());

  assert.equal(result.status, "BLOCKED");
  assert.equal(result.provider_requests, 0);
  assert.equal(result.identity.pair_address, "0xpair");
  assert.equal(result.safety.recomputed_status, "UNKNOWN");
  assert.deepEqual(
    result.blockers.map((blocker) => blocker.code),
    [
      "SAFETY_EVIDENCE_NOT_AUTHENTICATED",
      "SAFETY_SOURCE_OBSERVATION_TIME_UNAVAILABLE",
      "MARKET_SOURCE_OBSERVATION_TIME_UNAVAILABLE",
      "P03_ELIGIBILITY_UNKNOWN",
      "P04_SIGNAL_SNAPSHOT_UNAVAILABLE",
      "P04_FEATURE_SNAPSHOT_UNAVAILABLE",
      "P05_CANONICAL_INPUT_UNAVAILABLE",
    ],
  );
});

test("recomputes safety from evidence instead of trusting a favorable claim", () => {
  const result = composeOpportunityEvaluation(
    input({
      safety: {
        identity: { chain_id: "ethereum", token_address: "0xabc" },
        source: { received_at: "2026-09-18T03:00:00.000Z", source_observed_at: null },
        evaluation: { status: "ELIGIBLE", evidence_references: ["client-claim"] },
        evidence: [
          {
            status: "UNKNOWN",
            quality: "INCOMPLETE",
            freshness_status: "INCOMPLETE",
          },
        ],
      },
    }),
  );

  assert.equal(result.safety.claimed_status, "ELIGIBLE");
  assert.equal(result.safety.recomputed_status, "UNKNOWN");
  assert.ok(result.blockers.some((blocker) => blocker.code === "P03_ELIGIBILITY_UNKNOWN"));
});

test("rejects contradictory report identity before producing an evaluation", () => {
  const result = composeOpportunityEvaluation(
    input({
      safety: {
        identity: { chain_id: "ethereum", token_address: "0xother" },
        source: { received_at: "2026-09-18T03:00:00.000Z", source_observed_at: null },
        evaluation: { status: "UNKNOWN", evidence_references: [] },
        evidence: [],
      },
    }),
  );

  assert.deepEqual(result, {
    error: "REPORT_IDENTITY_MISMATCH",
    detail:
      "Chain and token identity must match across the request, inspection, temporal, and safety reports.",
  });
});

test("rejects a pair whose token identity is not represented by either token side", () => {
  const result = composeOpportunityEvaluation(
    input({
      inspection: {
        report: {
          request: { chain_id: "ethereum", token_address: "0xabc" },
          receipt: { received_at: "2026-09-18T03:00:00.000Z" },
          payload: {
            pairs: [
              {
                pairAddress: "0xpair",
                chainId: "ethereum",
                baseToken: { address: "0xother" },
                quoteToken: { address: "0xusd" },
              },
            ],
          },
        },
        temporal_evidence: {
          chain_id: "ethereum",
          token_identity: "0xabc",
          records: [
            {
              chain_id: "ethereum",
              token_identity: "0xabc",
              market_subject_id: "ethereum:0xpair",
              source_observed_at: null,
            },
          ],
        },
      },
    }),
  );

  assert.deepEqual(result, {
    error: "PAIR_IDENTITY_MISMATCH",
    detail:
      "The selected pair must preserve its exact chain, pair, token, and market-subject identity.",
  });
});

test("endpoint rejects malformed input server-side", async () => {
  const app = express();
  app.use(express.json());
  app.use(createOpportunityEvaluationRouter());
  const server = await new Promise<Server>((resolve) => {
    const created = createServer(app);
    created.listen(0, "127.0.0.1", () => resolve(created));
  });
  try {
    const address = server.address();
    assert.ok(address && typeof address !== "string");
    const response = await fetch(
      `http://127.0.0.1:${address.port}/opportunity-evaluations`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ chainId: "ethereum", pairIndex: 0 }),
      },
    );
    assert.equal(response.status, 400);
    assert.equal((await response.json()).code, "INVALID_INPUT");
  } finally {
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
});