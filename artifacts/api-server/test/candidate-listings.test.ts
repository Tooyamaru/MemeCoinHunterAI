import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import test from "node:test";
import express from "express";
import {
  CandidateProviderError,
  DEXSCREENER_TOKEN_PROFILES_URL,
  createCandidateListingsRouter,
  type CandidateListingFetcher,
  type CandidateProviderResponse,
} from "../src/routes/candidate-listings";

const receivedAt = "2026-09-18T03:00:00.000Z";

function providerResponse(body: unknown): CandidateProviderResponse {
  const serialized = typeof body === "string" ? body : JSON.stringify(body);
  return {
    endpoint: DEXSCREENER_TOKEN_PROFILES_URL,
    statusCode: 200,
    responseBytes: Buffer.byteLength(serialized),
    receivedAt,
    body: serialized,
  };
}

async function startTestServer(fetcher: CandidateListingFetcher): Promise<{
  server: Server;
  url: string;
}> {
  const app = express();
  app.use(createCandidateListingsRouter(fetcher));
  const server = createServer(app);
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      assert.ok(address && typeof address !== "string");
      resolve({
        server,
        url: `http://127.0.0.1:${address.port}/candidate-listings`,
      });
    });
  });
}

async function closeTestServer(server: Server): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

async function getListing(fetcher: CandidateListingFetcher) {
  const { server, url } = await startTestServer(fetcher);
  try {
    return await fetch(url);
  } finally {
    await closeTestServer(server);
  }
}

test("normal provider listing preserves order and identity metadata", async () => {
  let calls = 0;
  const response = await getListing(async () => {
    calls += 1;
    return providerResponse([
      {
        chainId: "solana",
        tokenAddress: "mint-A",
        url: "https://example.test/a",
        description: "Alpha",
        links: [{ type: "website", label: "Site", url: "https://example.test" }],
      },
      {
        chainId: "ethereum",
        tokenAddress: "0xabc",
        icon: null,
        header: null,
        description: null,
        links: null,
      },
    ]);
  });

  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(calls, 1);
  assert.equal(body.endpoint, DEXSCREENER_TOKEN_PROFILES_URL);
  assert.equal(body.admission_status, "NOT_ADMITTED");
  assert.equal(body.completeness, "BOUNDED_PROVIDER_LISTING");
  assert.deepEqual(
    body.candidates.map((candidate: { provider_index: number }) => candidate.provider_index),
    [0, 1],
  );
  assert.equal(body.candidates[0].tokenAddress, "mint-A");
  assert.equal(body.candidates[1].description, null);
  assert.equal(body.selectable_count, 2);
});

test("empty provider listing is a successful bounded result", async () => {
  const response = await getListing(async () => providerResponse([]));

  assert.equal(response.status, 200);
  const body = await response.json();
  assert.deepEqual(body.candidates, []);
  assert.equal(body.selectable_count, 0);
  assert.equal(body.invalid_count, 0);
  assert.equal(body.duplicate_count, 0);
});

test("duplicate, missing identity, and malformed entries remain visible in provider order", async () => {
  const response = await getListing(async () =>
    providerResponse([
      { chainId: "solana", tokenAddress: "mint-A", description: "first" },
      { chainId: "solana", tokenAddress: "mint-A", description: "duplicate" },
      { chainId: "solana", description: "missing token" },
      "not-an-entry",
    ]),
  );

  assert.equal(response.status, 200);
  const body = await response.json();
  assert.deepEqual(
    body.candidates.map((candidate: { provider_index: number }) => candidate.provider_index),
    [0, 1, 2, 3],
  );
  assert.equal(body.candidates[0].status, "SELECTABLE");
  assert.equal(body.candidates[1].status, "DUPLICATE");
  assert.equal(body.candidates[1].duplicate_of_index, 0);
  assert.equal(body.candidates[2].status, "MISSING_IDENTITY");
  assert.equal(body.candidates[2].tokenAddress, null);
  assert.equal(body.candidates[3].status, "INVALID");
  assert.equal(body.candidates[3].inspectable, false);
  assert.equal(body.duplicate_count, 1);
  assert.equal(body.invalid_count, 2);
});

test("malformed JSON fails closed without fabricating candidates", async () => {
  const response = await getListing(async () => providerResponse("{"));

  assert.equal(response.status, 502);
  assert.equal((await response.json()).code, "PROVIDER_MALFORMED_RESPONSE");
});

test("provider failure and timeout return structured bounded errors", async (t) => {
  await t.test("failure", async () => {
    const response = await getListing(async () => {
      throw new CandidateProviderError("failed", "PROVIDER_FAILURE");
    });
    assert.equal(response.status, 502);
    assert.equal((await response.json()).code, "PROVIDER_FAILURE");
  });

  await t.test("timeout", async () => {
    const response = await getListing(async () => {
      throw new CandidateProviderError("timed out", "PROVIDER_TIMEOUT");
    });
    assert.equal(response.status, 504);
    assert.equal((await response.json()).code, "PROVIDER_TIMEOUT");
  });
});