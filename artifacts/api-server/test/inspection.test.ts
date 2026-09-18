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

const responseBody = {
  report,
  temporal_evidence: {
    contract_version: "p08-market-data-temporal-evidence-v1",
    source_id: "DexScreener",
    token_identity: "0xabc",
    chain_id: "ethereum",
    raw_payload_digest: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    p08_acceptance: "NOT_ATTEMPTED",
    records: [],
  },
  evaluation_time: "2026-09-17T03:00:12.000000Z",
};

type DiagnosticRecord = Record<string, unknown>;

function startTestServer(
  inspector: InspectorRunner,
  diagnostics: DiagnosticRecord[] = [],
): Promise<{
  server: Server;
  url: string;
}> {
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
    return JSON.stringify(responseBody);
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
    assert.deepEqual(await response.json(), responseBody);
    assert.deepEqual(calls, [{ chainId: "ethereum", tokenAddress: "0xabc" }]);
  } finally {
    await closeTestServer(server);
  }
});

test("invalid input is rejected before the inspector is invoked", async () => {
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
      "INVALID_INSPECTION_RESPONSE",
    ],
    [
      "negative pair count",
       async () =>
        JSON.stringify({
          ...responseBody,
          report: {
            ...report,
            payload: { ...report.payload, pair_count: -1 },
          },
        }),
      502,
       "INVALID_INSPECTION_RESPONSE",
    ],
    [
      "fractional pair count",
       async () =>
        JSON.stringify({
          ...responseBody,
          report: {
            ...report,
            payload: { ...report.payload, pair_count: 0.5 },
          },
        }),
      502,
       "INVALID_INSPECTION_RESPONSE",
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

test("structured bridge failures keep the public error generic and log bounded diagnostics", async () => {
  const diagnostics: DiagnosticRecord[] = [];
  let calls = 0;
  const { server, url } = await startTestServer(async () => {
    calls += 1;
    throw Object.assign(new Error("bridge failed"), {
      code: 1,
      stdout: JSON.stringify({
        error: {
          code: "ConnectionFailureError",
          message: "DexScreener connection failed",
        },
      }),
      stderr:
        "Traceback: /home/runner/workspace/core/data.py\nAuthorization: bearer-secret\nsecond line",
    });
  }, diagnostics);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chainId: "ethereum", tokenAddress: "0xabc" }),
    });

    assert.equal(response.status, 502);
    assert.deepEqual(await response.json(), {
      error: "The inspection could not be completed.",
      code: "INSPECTOR_FAILURE",
      detail: "The inspector or its upstream source returned a failure.",
    });
    assert.equal(calls, 1);
    assert.equal(diagnostics.length, 1);
    const diagnostic = diagnostics[0].inspection_diagnostic as DiagnosticRecord;
    assert.equal(diagnostic.request_id, "test-request");
    assert.equal(diagnostic.category, "upstream_connection_failure");
    assert.equal(diagnostic.child_code_kind, "exit_code");
    assert.equal(diagnostic.exit_code, 1);
    assert.equal(typeof diagnostic.stderr_bytes, "number");
    assert.equal(diagnostic.stderr_excerpt, "Traceback: [PATH]");
    assert.equal(typeof diagnostic.stdout_bytes, "number");
    assert.equal(diagnostic.bridge_error_code, "ConnectionFailureError");
    assert.equal(diagnostic.bridge_message, "DexScreener connection failed");
  } finally {
    await closeTestServer(server);
  }
});

test("empty, malformed, unexpected, and truncated child output is classified safely", async (t) => {
  const cases: Array<[string, unknown, string]> = [
    ["empty", "", "child_exit"],
    ["malformed", "{not-json", "malformed_stdout"],
    ["unexpected", JSON.stringify({ report: {} }), "unexpected_stdout"],
    ["unexpected bridge error", JSON.stringify({ error: { code: "Unknown", message: "x" } }), "unrecognized_bridge_error"],
    ["truncated", "x".repeat(4097), "truncated_stdout"],
  ];

  for (const [name, stdout, category] of cases) {
    await t.test(name, async () => {
      const diagnostics: DiagnosticRecord[] = [];
      const { server, url } = await startTestServer(async () => {
        throw Object.assign(new Error("bridge failed"), {
          code: 1,
          stdout,
          stderr: "stderr\ninjected-line",
        });
      }, diagnostics);

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ chainId: "ethereum", tokenAddress: "0xabc" }),
        });

        assert.equal(response.status, 502);
        assert.equal((await response.json()).code, "INSPECTOR_FAILURE");
        const diagnostic = diagnostics[0].inspection_diagnostic as DiagnosticRecord;
        assert.equal(diagnostic.category, category);
        assert.equal(diagnostic.stderr_excerpt, "stderr");
        assert.equal(String(diagnostic.stderr_excerpt).includes("\n"), false);
      } finally {
        await closeTestServer(server);
      }
    });
  }
});

test("launch, timeout, and output-limit failures retain safe classifications", async (t) => {
  const cases: Array<[string, InspectorRunner, string, Record<string, unknown>]> = [
    [
      "launch failure",
      async () => {
        throw Object.assign(new Error("spawn failed"), {
          code: "ENOENT",
          stderr: "spawn python3 ENOENT",
        });
      },
      "launch_error",
      { launch_error_code: "ENOENT" },
    ],
    [
      "timeout",
      async () => {
        throw Object.assign(new Error("timed out"), {
          code: "ETIMEDOUT",
          signal: "SIGTERM",
          killed: true,
        });
      },
      "timeout",
      { timeout_code: "ETIMEDOUT", signal: "SIGTERM", killed: true },
    ],
    [
      "output limit",
      async () => {
        throw Object.assign(new Error("output too large"), {
          code: "ERR_CHILD_PROCESS_STDIO_MAXBUFFER",
        });
      },
      "output_limit",
      { output_limit_code: "ERR_CHILD_PROCESS_STDIO_MAXBUFFER" },
    ],
  ];

  for (const [name, inspector, category, expected] of cases) {
    await t.test(name, async () => {
      const diagnostics: DiagnosticRecord[] = [];
      const { server, url } = await startTestServer(inspector, diagnostics);
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ chainId: "ethereum", tokenAddress: "0xabc" }),
        });

        const body = (await response.json()) as { code: string };
        assert.equal(body.code, category === "timeout" ? "INSPECTOR_TIMEOUT" : category === "output_limit" ? "INSPECTOR_OUTPUT_TOO_LARGE" : "INSPECTOR_FAILURE");
        const diagnostic = diagnostics[0].inspection_diagnostic as DiagnosticRecord;
        assert.equal(diagnostic.category, category);
        for (const [key, value] of Object.entries(expected)) {
          assert.equal(diagnostic[key], value);
        }
      } finally {
        await closeTestServer(server);
      }
    });
  }
});