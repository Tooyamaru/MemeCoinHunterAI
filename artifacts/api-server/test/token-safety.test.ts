import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import test from "node:test";
import express from "express";
import {
  createTokenSafetyRouter,
  type SafetyRunner,
} from "../src/routes/token-safety";

const responseBody = {
  assessment_version: "p03-safety-assessment-v1",
  identity: {
    chain_id: "ethereum",
    token_address: "0xabc",
  },
  source: {
    source_id: "GoPlus",
    endpoint:
      "https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses=0xabc",
    http_status: 200,
    response_bytes: 512,
    received_at: "2026-09-18T03:00:00.000Z",
    source_observed_at: null,
    source_freshness: "UNKNOWN",
  },
  evaluation: {
    status: "UNKNOWN",
    is_authoritative: false,
    evaluator_id: "p03-t03-eligibility-derivation",
    contract_version: "p03-t02-v1",
    evaluation_timestamp: "2026-09-18T03:00:00.000Z",
    input_evidence_digest:
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    domain_results: {
      MINT_FREEZE_AUTHORITY: "UNKNOWN",
    },
    evidence_references: [],
    reason_codes: ["UNKNOWN_DOMAIN"],
  },
  evidence: [],
  missing_evidence: [
    {
      domain: "MINT_FREEZE_AUTHORITY",
      requirement:
        "A documented provider safety field with a source observation timestamp.",
      reason: "Source observation time unavailable.",
    },
  ],
  limitations: [
    "This is non-authoritative safety evidence evaluation, not a safety guarantee.",
  ],
};

type DiagnosticRecord = Record<string, unknown>;

function startTestServer(
  runner: SafetyRunner,
  diagnostics: DiagnosticRecord[] = [],
): Promise<{ server: Server; url: string }> {
  const app = express();
  app.use((req, _res, next) => {
    Object.assign(req, {
      id: "test-request",
      log: {
        error(fields: DiagnosticRecord) {
          diagnostics.push(fields);
        },
      },
    });
    next();
  });
  app.use(express.json());
  app.use(createTokenSafetyRouter(runner));
  const server = createServer(app);

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      assert.ok(address && typeof address !== "string");
      resolve({
        server,
        url: `http://127.0.0.1:${address.port}/token-safety`,
      });
    });
  });
}

async function closeTestServer(server: Server): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

function providerFailure(code: string, message = "provider detail") {
  return Object.assign(new Error("bridge failed"), {
    code: 1,
    stdout: JSON.stringify({ error: { code, message } }),
  });
}

test("normal and incomplete assessments are returned without changing identity", async (t) => {
  for (const [name, body] of [
    ["normal", responseBody],
    [
      "incomplete",
      {
        ...responseBody,
        evaluation: {
          ...responseBody.evaluation,
          status: "UNKNOWN",
          reason_codes: ["MISSING_PROVIDER_FIELD"],
        },
        missing_evidence: [
          {
            domain: "MINT_FREEZE_AUTHORITY",
            requirement: "A source observation timestamp.",
            reason: "Unavailable.",
          },
        ],
      },
    ],
  ] as const) {
    await t.test(name, async () => {
      const calls: Array<{ chainId: string; tokenAddress: string }> = [];
      const { server, url } = await startTestServer(async (input) => {
        calls.push(input);
        return JSON.stringify(body);
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
        assert.deepEqual(await response.json(), body);
        assert.deepEqual(calls, [{ chainId: "ethereum", tokenAddress: "0xabc" }]);
      } finally {
        await closeTestServer(server);
      }
    });
  }
});

test("malformed, contradictory-identity, provider-error, and timeout cases fail closed", async (t) => {
  const cases: Array<[string, SafetyRunner, number, string]> = [
    ["malformed output", async () => "{", 502, "MALFORMED_SAFETY_OUTPUT"],
    [
      "contradictory identity",
      async () => {
        throw providerFailure(
          "PROVIDER_IDENTITY_MISMATCH",
          "returned another token identity",
        );
      },
      502,
      "SAFETY_PROVIDER_FAILURE",
    ],
    [
      "provider error",
      async () => {
        throw providerFailure("PROVIDER_RESPONSE_ERROR", "upstream rejected request");
      },
      502,
      "SAFETY_PROVIDER_FAILURE",
    ],
    [
      "timeout",
      async () => {
        throw Object.assign(new Error("timed out"), { code: "ETIMEDOUT" });
      },
      504,
      "SAFETY_ASSESSMENT_TIMEOUT",
    ],
  ];

  for (const [name, runner, status, code] of cases) {
    await t.test(name, async () => {
      const { server, url } = await startTestServer(runner);
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

test("unsupported chain is surfaced as a bounded integration limitation", async () => {
  const { server, url } = await startTestServer(async () => {
    throw providerFailure("UNSUPPORTED_CHAIN");
  });
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        chainId: "solana",
        tokenAddress: "mint",
      }),
    });
    assert.equal(response.status, 422);
    assert.equal((await response.json()).code, "UNSUPPORTED_CHAIN");
  } finally {
    await closeTestServer(server);
  }
});

test("invalid input is rejected before the safety runner is invoked", async () => {
  let calls = 0;
  const { server, url } = await startTestServer(async () => {
    calls += 1;
    return JSON.stringify(responseBody);
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
    assert.equal((await response.json()).code, "INVALID_INPUT");
    assert.equal(calls, 0);
  } finally {
    await closeTestServer(server);
  }
});