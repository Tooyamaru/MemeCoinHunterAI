import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import test from "node:test";
import express from "express";
import { createInspectionRouter, type InspectorRunner } from "../src/routes/inspection";

const report = {
  tool_version: "dexscreener-inspection-v1",
  source: "DexScreener",
  request: {
    endpoint: "https://api.dexscreener.com/token-pairs/v1/ethereum/0xabc",
    chain_id: "ethereum",
    token_address: "0xabc",
    attempts: 1,
    retry_count: 0,
    attempt_log: [
      {
        attempt: 1,
        status_code: 200,
        response_bytes: 2,
        received_at: "2026-09-17T03:00:00.000000Z",
      },
    ],
  },
  receipt: {
    received_at: "2026-09-17T03:00:00.000000Z",
    http_status: 200,
    response_bytes: 2,
  },
  payload: {
    raw_payload_sha256: null,
    pair_count: 0,
    pairs: [],
  },
  evidence: {
    p08_acceptance: "NOT_ATTEMPTED",
    p08_observed_at: null,
    asset_age: {
      status: "UNAVAILABLE",
    },
    unavailable_fields: [],
  },
};

function startTestServer(inspector: InspectorRunner): Promise<{
  server: Server;
  url: string;
}> {
  const app = express();
  app.use(express.json());
  app.use(createInspectionRouter(inspector));
  const server = createServer(app);

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      assert.ok(address && typeof address !== "string");
      resolve({
        server,
        url: `http://127.0.0.1:${address.port}/inspections`,
      });
    });
  });
}

async function closeTestServer(server: Server): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

test("success returns the validated report through the endpoint", async () => {
  const calls: Array<{ chainId: string; tokenAddress: string }> = [];
  const { server, url } = await startTestServer(async (input) => {
    calls.push(input);
    return JSON.stringify(report);
  });

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        chainId: "ethereum",
        tokenAddress: "0xabc",
      }),
    });

    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), report);
    assert.deepEqual(calls, [{ chainId: "ethereum", tokenAddress: "0xabc" }]);
  } finally {
    await closeTestServer(server);
  }
});

test("invalid input is rejected before the inspector is invoked", async () => {
  let calls = 0;
  const { server, url } = await startTestServer(async () => {
    calls += 1;
    return JSON.stringify(report);
  });

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        chainId: "ethereum/../../",
        tokenAddress: "0xabc",
      }),
    });

    assert.equal(response.status, 400);
    assert.deepEqual(await response.json(), {
      error: "Inspection request is invalid.",
      code: "INVALID_INPUT",
      detail: "Provide a chainId and tokenAddress using only URL-safe identifier characters.",
    });
    assert.equal(calls, 0);
  } finally {
    await closeTestServer(server);
  }
});

test("malformed and invalid inspector output fail closed", async (t) => {
  const cases: Array<[string, InspectorRunner, number, string]> = [
    ["malformed JSON", async () => "{", 502, "MALFORMED_INSPECTOR_OUTPUT"],
    [
      "invalid report",
      async () => JSON.stringify({ payload: { pairs: [] } }),
      502,
      "INVALID_INSPECTOR_REPORT",
    ],
    [
      "negative pair count",
      async () =>
        JSON.stringify({
          ...report,
          payload: { ...report.payload, pair_count: -1 },
        }),
      502,
      "INVALID_INSPECTOR_REPORT",
    ],
    [
      "fractional pair count",
      async () =>
        JSON.stringify({
          ...report,
          payload: { ...report.payload, pair_count: 0.5 },
        }),
      502,
      "INVALID_INSPECTOR_REPORT",
    ],
    [
      "process failure",
      async () => {
        throw Object.assign(new Error("bridge failed"), { code: 1 });
      },
      502,
      "INSPECTOR_FAILURE",
    ],
    [
      "timeout",
      async () => {
        throw Object.assign(new Error("timed out"), { code: "ETIMEDOUT" });
      },
      504,
      "INSPECTOR_TIMEOUT",
    ],
  ];

  for (const [name, inspector, status, code] of cases) {
    await t.test(name, async () => {
      const { server, url } = await startTestServer(inspector);
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            chainId: "ethereum",
            tokenAddress: "0xabc",
          }),
        });

        assert.equal(response.status, status);
        const body = (await response.json()) as { code: string };
        assert.equal(body.code, code);
      } finally {
        await closeTestServer(server);
      }
    });
  }
});