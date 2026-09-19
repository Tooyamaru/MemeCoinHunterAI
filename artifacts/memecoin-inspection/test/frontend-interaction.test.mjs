import assert from "node:assert/strict";
import { createHash, randomBytes } from "node:crypto";
import { connect } from "node:net";
import test from "node:test";

const APP_URL = process.env.APP_URL ?? "http://127.0.0.1:80/";
const CHROMIUM_PATH = process.env.CHROMIUM_PATH ?? "/repl/tools/bin/chromium";

const successReceivedAt = "2026-09-17T03:00:00.000000Z";

function makeReport(pairs, receivedAt = successReceivedAt) {
  const report = {
    tool_version: "dexscreener-inspection-v1",
    source: "DexScreener",
    request: {
      endpoint: "https://api.dexscreener.com/token-pairs/v1/ethereum/0xsuccess",
      chain_id: "ethereum",
      token_address: "0xsuccess",
      attempts: 1,
      retry_count: 0,
      attempt_log: [
        {
          attempt: 1,
          status_code: 200,
          response_bytes: 42,
          received_at: receivedAt,
        },
      ],
    },
    receipt: {
      received_at: receivedAt,
      http_status: 200,
      response_bytes: 42,
    },
    payload: {
      raw_payload_sha256: null,
      pair_count: pairs.length,
      pairs,
    },
    evidence: {
      p08_acceptance: "NOT_ATTEMPTED",
      p08_observed_at: null,
      asset_age: { status: "UNAVAILABLE" },
      unavailable_fields: [],
    },
  };

  return {
    report,
    temporal_evidence: {
      contract_version: "p08-market-data-temporal-evidence-v1",
      source_id: "DexScreener",
      token_identity: "0xsuccess",
      chain_id: "ethereum",
      raw_payload_digest: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      p08_acceptance: "NOT_ATTEMPTED",
      records: pairs.map((pair, index) => ({
        contract_version: "p08-market-data-temporal-evidence-v1",
        source_id: "DexScreener",
        source_event_id: null,
        token_identity: "0xsuccess",
        chain_id: "ethereum",
        market_subject_id: `ethereum:${pair.pairAddress}`,
        occurrence_id: `${"a".repeat(63)}${index.toString(16)}`,
        source_observed_at: null,
        received_at: receivedAt ?? successReceivedAt,
        source_freshness: {
          status: "UNKNOWN",
          reason: "NO_DOCUMENTED_MARKET_FIELD_OBSERVATION_TIMESTAMP",
        },
        receipt_recency: {
          reference_time: "2026-09-17T03:00:12.000000Z",
          age_seconds: "12",
        },
        volume_window: {
          source_label: "h24",
          exact_window: null,
        },
        asset_age: {
          status: "UNAVAILABLE",
          amount: null,
          unit: null,
          reference_semantics: null,
          source_field: null,
          reason: "NO_DOCUMENTED_TOKEN_ORIGIN_SEMANTICS",
        },
        pair_created_at_source_value: pair.pairCreatedAt,
        raw_payload_digest: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        p08_acceptance: "NOT_ATTEMPTED",
      })),
    },
    evaluation_time: "2026-09-17T03:00:12.000000Z",
  };
}

function makeSafetyAssessment(tokenAddress = "0xsuccess") {
  return {
    assessment_version: "p03-safety-assessment-v1",
    identity: { chain_id: "ethereum", token_address: tokenAddress },
    source: {
      source_id: "GoPlus",
      endpoint: "https://api.gopluslabs.io/api/v1/token_security/1?contract_addresses=0xsuccess",
      http_status: 200,
      response_bytes: 512,
      received_at: successReceivedAt,
      source_observed_at: null,
      source_freshness: "UNKNOWN",
    },
    evaluation: {
      status: "UNKNOWN",
      is_authoritative: false,
      evaluator_id: "p03-t03-eligibility-derivation",
      contract_version: "p03-t02-v1",
      evaluation_timestamp: successReceivedAt,
      input_evidence_digest: "a".repeat(64),
      domain_results: { MINT_FREEZE_AUTHORITY: "UNKNOWN" },
      evidence_references: [],
      reason_codes: ["UNKNOWN_DOMAIN"],
    },
    evidence: [
      {
        domain: "MINT_FREEZE_AUTHORITY",
        status: "UNKNOWN",
        quality: "INCOMPLETE",
        freshness_status: "INCOMPLETE",
        observed_at: successReceivedAt,
        source_id: "GoPlus",
        method: "token-security-api",
        evidence_reference: "GoPlus:ethereum:0xsuccess:is_mintable",
        evidence_context: { provider_field: "is_mintable", provider_value: "0" },
        reason_codes: ["SOURCE_OBSERVATION_TIME_UNAVAILABLE"],
      },
    ],
    missing_evidence: [
      {
        domain: "MINT_FREEZE_AUTHORITY",
        requirement: "A documented provider safety field with a source observation timestamp.",
        reason: "The provider did not document a source observation timestamp.",
      },
    ],
    limitations: [
      "This is non-authoritative safety evidence evaluation, not a safety guarantee.",
    ],
  };
}

const successPair = {
  pairAddress: "0xpair",
  chainId: "ethereum",
  dexId: "mock-dex",
  url: "https://example.test/pair",
  baseToken: { address: "0xsuccess", name: "Mock Token", symbol: "MOCK" },
  quoteToken: { address: "0xusd", name: "USD Coin", symbol: "USDC" },
  priceNative: "0.000000000001",
  priceUsd: "0.000000000000000001",
  fdv: null,
  marketCap: "123.4500",
  liquidity: {
    m5: "1.0000",
    h1: null,
    h6: "3",
    h24: "4",
    usd: "5.0000",
    base: null,
    quote: "7",
  },
  volume: { m5: "8.0000", h1: null, h6: "10", h24: "11" },
  priceChange: { m5: "-1.25", h1: null, h6: "2.5", h24: "3.75" },
  txns: {
    m5: { buys: "12", sells: "13" },
    h1: null,
    h6: { buys: "14", sells: "15" },
    h24: { buys: "16", sells: "17" },
  },
  pairCreatedAt: null,
  inspection: {
    source_pair_created_at: null,
    field_provenance: {},
    findings: [{ code: "MOCK_FINDING", source_field: "fdv", value: null }],
  },
};

function frame(payload, opcode = 1) {
  const data = Buffer.from(payload);
  const mask = randomBytes(4);
  let header;

  if (data.length < 126) {
    header = Buffer.from([0x80 | opcode, 0x80 | data.length]);
  } else if (data.length < 65536) {
    header = Buffer.alloc(4);
    header[0] = 0x80 | opcode;
    header[1] = 0x80 | 126;
    header.writeUInt16BE(data.length, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x80 | opcode;
    header[1] = 0x80 | 127;
    header.writeBigUInt64BE(BigInt(data.length), 2);
  }

  const masked = Buffer.from(data);
  for (let index = 0; index < masked.length; index += 1) {
    masked[index] ^= mask[index % 4];
  }
  return Buffer.concat([header, mask, masked]);
}

class DevToolsConnection {
  #socket;
  #buffer = Buffer.alloc(0);
  #handshakeComplete = false;
  #nextId = 1;
  #pending = new Map();
  #listeners = new Map();

  constructor(webSocketUrl) {
    const url = new URL(webSocketUrl);
    this.#socket = connect(Number(url.port), url.hostname);
    this.#socket.on("data", (chunk) => this.#onData(chunk));
    this.#socket.on("error", (error) => {
      for (const { reject } of this.#pending.values()) reject(error);
      this.#pending.clear();
    });

    this.ready = new Promise((resolve, reject) => {
      this.#socket.once("connect", () => {
        const key = randomBytes(16).toString("base64");
        this.#socket.write(
          [
            `GET ${url.pathname} HTTP/1.1`,
            `Host: ${url.host}`,
            "Upgrade: websocket",
            "Connection: Upgrade",
            `Sec-WebSocket-Key: ${key}`,
            "Sec-WebSocket-Version: 13",
            "",
            "",
          ].join("\r\n"),
        );
      });
      this.#socket.once("error", reject);
      this.#resolveHandshake = resolve;
      this.#rejectHandshake = reject;
    });
  }

  #resolveHandshake;
  #rejectHandshake;

  on(method, listener) {
    const listeners = this.#listeners.get(method) ?? [];
    listeners.push(listener);
    this.#listeners.set(method, listeners);
  }

  async send(method, params = {}) {
    await this.ready;
    const id = this.#nextId++;
    const message = JSON.stringify({ id, method, params });
    this.#socket.write(frame(message));
    return new Promise((resolve, reject) => {
      this.#pending.set(id, { resolve, reject });
    });
  }

  close() {
    this.#socket.destroy();
  }

  #onData(chunk) {
    this.#buffer = Buffer.concat([this.#buffer, chunk]);

    if (!this.#handshakeComplete) {
      const headerEnd = this.#buffer.indexOf("\r\n\r\n");
      if (headerEnd < 0) return;
      const handshake = this.#buffer.subarray(0, headerEnd).toString();
      this.#buffer = this.#buffer.subarray(headerEnd + 4);
      if (!handshake.startsWith("HTTP/1.1 101")) {
        this.#rejectHandshake(new Error(`DevTools websocket handshake failed: ${handshake}`));
        return;
      }
      this.#handshakeComplete = true;
      this.#resolveHandshake();
    }

    while (this.#buffer.length >= 2) {
      const first = this.#buffer[0];
      const second = this.#buffer[1];
      let length = second & 0x7f;
      let offset = 2;

      if (length === 126) {
        if (this.#buffer.length < 4) return;
        length = this.#buffer.readUInt16BE(2);
        offset = 4;
      } else if (length === 127) {
        if (this.#buffer.length < 10) return;
        length = Number(this.#buffer.readBigUInt64BE(2));
        offset = 10;
      }

      const masked = (second & 0x80) !== 0;
      const maskOffset = masked ? 4 : 0;
      if (this.#buffer.length < offset + maskOffset + length) return;

      let payload = this.#buffer.subarray(
        offset + maskOffset,
        offset + maskOffset + length,
      );
      if (masked) {
        const mask = this.#buffer.subarray(offset, offset + 4);
        payload = Buffer.from(payload);
        for (let index = 0; index < payload.length; index += 1) {
          payload[index] ^= mask[index % 4];
        }
      }
      this.#buffer = this.#buffer.subarray(offset + maskOffset + length);

      const opcode = first & 0x0f;
      if (opcode === 0x9) {
        this.#socket.write(frame(payload, 0xa));
      } else if (opcode === 0x1) {
        this.#onMessage(JSON.parse(payload.toString()));
      } else if (opcode === 0x8) {
        this.close();
        return;
      }
    }
  }

  #onMessage(message) {
    if (message.id !== undefined) {
      const pending = this.#pending.get(message.id);
      if (!pending) return;
      this.#pending.delete(message.id);
      if (message.error) {
        pending.reject(new Error(JSON.stringify(message.error)));
      } else {
        pending.resolve(message.result);
      }
      return;
    }

    for (const listener of this.#listeners.get(message.method) ?? []) {
      listener(message.params);
    }
  }
}

async function waitForDebugger(child) {
  return new Promise((resolve, reject) => {
    let output = "";
    const onData = (chunk) => {
      output += chunk.toString();
      const match = output.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) resolve(match[1]);
    };
    child.stdout.on("data", onData);
    child.stderr.on("data", onData);
    child.once("error", reject);
    child.once("exit", (code) => {
      reject(new Error(`Chromium exited before DevTools was ready (${code})\n${output}`));
    });
  });
}

async function startBrowser() {
  const child = (await import("node:child_process")).spawn(CHROMIUM_PATH, [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--remote-debugging-port=0",
    `--user-data-dir=/tmp/memecoin-inspection-${process.pid}`,
    "about:blank",
  ]);
  const browserUrl = await waitForDebugger(child);
  const browser = new DevToolsConnection(browserUrl);
  await browser.ready;
  const browserPort = new URL(browserUrl).port;
  const targetResponse = await fetch(
    `http://127.0.0.1:${browserPort}/json/new?${encodeURIComponent("about:blank")}`,
    { method: "PUT" },
  );
  assert.equal(targetResponse.status, 200);
  const target = await targetResponse.json();
  browser.close();

  const page = new DevToolsConnection(target.webSocketDebuggerUrl);
  await page.ready;
  return {
    page,
    close() {
      page.close();
      child.kill("SIGTERM");
    },
  };
}

async function evaluate(page, expression) {
  const result = await page.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? "Browser evaluation failed");
  }
  return result.result?.value;
}

async function waitFor(condition, timeout = 5000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await condition()) return;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error("Timed out waiting for browser condition");
}

function responseBody(body) {
  return Buffer.from(JSON.stringify(body)).toString("base64");
}

async function fulfill(page, request, status, body) {
  await page.send("Fetch.fulfillRequest", {
    requestId: request.requestId,
    responseCode: status,
    responseHeaders: [
      { name: "content-type", value: "application/json" },
      { name: "content-length", value: String(Buffer.byteLength(JSON.stringify(body))) },
    ],
    body: responseBody(body),
  });
}

test("the rendered inspection flow uses one mocked request and rejects stale UI results", async (t) => {
  const browser = await startBrowser();
  t.after(() => browser.close());
  const { page } = browser;
  const requests = [];
  const candidateRequests = [];
  const safetyRequests = [];
  const pausedRequests = [];
  const pausedSafetyRequests = [];
  const queuedResponses = [];
  const requestWaiters = [];
  const safetyRequestWaiters = [];

  page.on("Fetch.requestPaused", async (request) => {
    if (request.request.url.endsWith("/api/candidate-listings")) {
      candidateRequests.push(request);
      await fulfill(page, request, 200, {
        source: "DexScreener",
        endpoint: "https://api.dexscreener.com/token-profiles/latest/v1",
        selection_basis: "Provider order from the documented latest token-profiles listing.",
        admission_status: "NOT_ADMITTED",
        completeness: "BOUNDED_PROVIDER_LISTING",
        limit: 50,
        received_at: successReceivedAt,
        http_status: 200,
        response_bytes: 123,
        truncated: false,
        candidates: [
          {
            provider_index: 0,
            provider_entry_type: "object",
            chainId: "ethereum",
            tokenAddress: "0xcandidate",
            url: "https://example.test/profile",
            icon: null,
            header: null,
            description: "Candidate Alpha",
            links: null,
            status: "SELECTABLE",
            inspectable: true,
            duplicate_of_index: null,
            issues: [],
          },
        ],
        selectable_count: 1,
        invalid_count: 0,
        duplicate_count: 0,
      });
      return;
    }
    if (request.request.url.endsWith("/api/token-safety")) {
      safetyRequests.push(request);
      for (const resolve of safetyRequestWaiters.splice(0)) resolve(request);
      pausedSafetyRequests.push(request);
      return;
    }
    if (!request.request.url.endsWith("/api/inspections")) {
      await page.send("Fetch.continueRequest", { requestId: request.requestId });
      return;
    }

    requests.push(request);
    for (const resolve of requestWaiters.splice(0)) resolve(request);
    const response = queuedResponses.shift();
    if (response) {
      await fulfill(page, request, response.status, response.body);
    } else {
      pausedRequests.push(request);
    }
  });

  await page.send("Runtime.enable");
  await page.send("Page.enable");
  await page.send("Fetch.enable", {
    patterns: [{ urlPattern: "*", requestStage: "Request" }],
  });
  await page.send("Page.navigate", { url: APP_URL });
  await waitFor(() => evaluate(page, "Boolean(document.querySelector('input[placeholder=\"0x...\"]'))"));
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(requests.length, 0, "the app must not inspect automatically on page load");
  assert.equal(candidateRequests.length, 0, "the app must not load candidates automatically on page load");
  assert.equal(safetyRequests.length, 0, "the app must not check safety automatically on page load");

  const bodyText = () => evaluate(page, "document.body.innerText");
  await evaluate(
    page,
    `Array.from(document.querySelectorAll("button")).find((button) => button.textContent.includes("Load candidates")).click()`,
  );
  await waitFor(async () => (await bodyText()).includes("Candidate Alpha"));
  assert.equal(candidateRequests.length, 1, "candidate discovery must use one explicit request");
  assert.equal(requests.length, 0, "loading candidates must not inspect a token");

  await evaluate(
    page,
    `Array.from(document.querySelectorAll("button")).find((button) => button.textContent.includes("Select for inspection")).click()`,
  );
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.equal(candidateRequests.length, 1, "selecting a candidate must not reload the listing");
  assert.equal(requests.length, 0, "selecting a candidate must not inspect automatically");
  assert.deepEqual(
    await evaluate(
      page,
      `({
        chainId: document.querySelector('input[placeholder="ethereum"]').value,
        tokenAddress: document.querySelector('input[placeholder="0x..."]').value
      })`,
    ),
    { chainId: "ethereum", tokenAddress: "0xcandidate" },
  );

  const setToken = async (value) => {
    await evaluate(
      page,
      `(() => {
        const input = document.querySelector('input[placeholder="0x..."]');
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
        setter.call(input, ${JSON.stringify(value)});
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      })()`,
    );
  };
  const submit = () =>
    evaluate(page, `document.querySelector('button[type="submit"]').click()`);
  const nextRequest = (expectedCount) =>
    requests.length >= expectedCount
      ? Promise.resolve(requests[expectedCount - 1])
      : new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error("Timed out waiting for inspection request")), 5000);
          requestWaiters.push((request) => {
            clearTimeout(timer);
            resolve(request);
          });
        });

  await setToken("0xsuccess");
  await submit();
  const firstRequest = await nextRequest(1);
  assert.deepEqual(JSON.parse(firstRequest.request.postData), {
    chainId: "ethereum",
    tokenAddress: "0xsuccess",
  });
  assert.equal(
    await evaluate(page, "document.querySelector('button[type=\"submit\"]').disabled"),
    true,
    "a pending request must disable the submit button",
  );
  await submit();
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.equal(requests.length, 1, "a pending request must block duplicate submissions");
  assert.match(await bodyText(), /Inspecting…/);
  pausedRequests.shift();
  await fulfill(page, firstRequest, 200, makeReport([successPair]));
  await waitFor(async () => (await bodyText()).includes("MOCK / USDC"));
  await evaluate(
    page,
    `document.querySelectorAll("details").forEach((details) => { details.open = true; })`,
  );

  const expectedReceivedAt = await evaluate(
    page,
    `new Date(${JSON.stringify(successReceivedAt)}).toLocaleString()`,
  );
  const successText = await bodyText();
  assert.match(successText, /0\.000000000000000001 USD/);
  assert.match(successText, /123\.4500 USD/);
  assert.match(successText, /Activity summary/);
  assert.match(successText, /Total transactions/);
  assert.match(successText, /33/);
  assert.match(successText, /48\.5%/);
  assert.match(successText, /Current USD liquidity/);
  assert.match(successText, /5\.0000 USD/);
  assert.match(successText, /Source-reported 24h volume/);
  assert.match(successText, /DATA AVAILABILITY/);
  assert.match(successText, /Unavailable/);
  assert.match(successText, /-1\.25 %/);
  assert.ok(successText.includes(expectedReceivedAt), "receipt time should be formatted and visible");
  assert.match(successText, /Source observation time/);
  assert.match(successText, /Source freshness/);
  assert.match(successText, /Receipt age at evaluation/i);
  assert.match(successText, /12 seconds/);
  assert.match(successText, /Evaluation timestamp/);

  await evaluate(
    page,
    `Array.from(document.querySelectorAll("button")).find((button) => button.textContent.includes("Check token safety")).click()`,
  );
  const nextSafetyRequest = (expectedCount) =>
    safetyRequests.length >= expectedCount
      ? Promise.resolve(safetyRequests[expectedCount - 1])
      : new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error("Timed out waiting for safety request")), 5000);
          safetyRequestWaiters.push((request) => {
            clearTimeout(timer);
            resolve(request);
          });
        });
  const firstSafetyRequest = await nextSafetyRequest(1);
  assert.deepEqual(JSON.parse(firstSafetyRequest.request.postData), {
    chainId: "ethereum",
    tokenAddress: "0xsuccess",
  });
  await fulfill(page, firstSafetyRequest, 200, makeSafetyAssessment());
  await waitFor(async () => (await bodyText()).toLowerCase().includes("token safety assessment"));
  assert.match(await bodyText(), /Source-backed findings/);
  assert.match(await bodyText(), /Unknown: evidence is incomplete/);
  assert.match(await bodyText(), /not a safety guarantee/i);

  await evaluate(
    page,
    `Array.from(document.querySelectorAll("button")).find((button) => button.textContent.includes("Check token safety")).click()`,
  );
  const staleSafetyRequest = await nextSafetyRequest(2);
  await setToken("0xchanged-before-safety-result");
  await fulfill(page, staleSafetyRequest, 200, makeSafetyAssessment());
  assert.ok(
    !(await bodyText()).toLowerCase().includes("token safety assessment"),
    "a safety response for the previous token must not render",
  );

  await setToken("0xstale");
  await submit();
  const staleRequest = await nextRequest(2);
  await setToken("0xnew");
  await fulfill(page, staleRequest, 200, makeReport([successPair]));
  await waitFor(async () => !(await bodyText()).includes("Inspecting…"));
  const afterStaleText = await bodyText();
  assert.ok(!afterStaleText.includes("MOCK / USDC"), "an older response must not render for changed input");
  assert.ok(afterStaleText.includes("No inspection yet"), "changed input should return to the empty state");

  queuedResponses.push({
    status: 200,
    body: makeReport([], successReceivedAt),
  });
  await submit();
  await nextRequest(3);
  await waitFor(async () => (await bodyText()).includes("No pairs returned"));
  const emptyText = await bodyText();
  assert.match(emptyText, /0 pairs returned/);
  assert.match(emptyText, /No pairs returned/);
  assert.match(emptyText, /no pair-level temporal records/i);
  assert.ok(emptyText.includes(expectedReceivedAt), "empty report must preserve receipt time");
  assert.match(emptyText, /Source observation time: Unavailable/i);
  assert.match(emptyText, /Source freshness: Unknown/i);

  await setToken("0xerror");
  queuedResponses.push({
    status: 502,
    body: {
      error: "The inspection returned an invalid report.",
      code: "INVALID_INSPECTOR_REPORT",
      detail: "The mocked inspector response was invalid.",
    },
  });
  await submit();
  await nextRequest(4);
  await waitFor(async () => (await bodyText()).includes("Inspection unavailable"));
  assert.ok((await bodyText()).includes("Inspection unavailable"));
});