import { Router, type IRouter, type Response } from "express";
import { ListCandidateTokensResponse } from "@workspace/api-zod";

export const DEXSCREENER_TOKEN_PROFILES_URL =
  "https://api.dexscreener.com/token-profiles/latest/v1";
export const MAX_CANDIDATE_ENTRIES = 50;
export const MAX_RESPONSE_BYTES = 1_048_576;
export const MAX_LINKS_PER_ENTRY = 20;
export const PROVIDER_TIMEOUT_MS = 10_000;
export const MAX_CONCURRENT_LISTINGS = 1;

const IDENTIFIER_RE = /^[A-Za-z0-9._~-]+$/;

export type CandidateProviderResponse = {
  endpoint: string;
  statusCode: number;
  responseBytes: number;
  receivedAt: string;
  body: string;
};

export type CandidateListingFetcher = () => Promise<CandidateProviderResponse>;

export class CandidateProviderError extends Error {
  constructor(
    message: string,
    readonly code:
      | "PROVIDER_TIMEOUT"
      | "PROVIDER_FAILURE"
      | "PROVIDER_HTTP_ERROR"
      | "PROVIDER_RESPONSE_TOO_LARGE",
    readonly statusCode?: number,
  ) {
    super(message);
    this.name = "CandidateProviderError";
  }
}

function errorResponse(
  res: Response,
  status: number,
  code: string,
  error: string,
  detail: string,
) {
  return res.status(status).json({ error, code, detail });
}

async function readBoundedBody(
  body: ReadableStream<Uint8Array> | null,
): Promise<{ text: string; bytes: number }> {
  if (!body) return { text: "", bytes: 0 };

  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let bytes = 0;
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      bytes += next.value.byteLength;
      if (bytes > MAX_RESPONSE_BYTES) {
        await reader.cancel();
        throw new CandidateProviderError(
          "DexScreener candidate response exceeded the configured limit.",
          "PROVIDER_RESPONSE_TOO_LARGE",
        );
      }
      chunks.push(next.value);
    }
  } finally {
    reader.releaseLock();
  }

  return {
    text: Buffer.concat(chunks.map((chunk) => Buffer.from(chunk))).toString("utf8"),
    bytes,
  };
}

export async function fetchLatestTokenProfiles(): Promise<CandidateProviderResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PROVIDER_TIMEOUT_MS);

  try {
    let response: globalThis.Response;
    try {
      response = await fetch(DEXSCREENER_TOKEN_PROFILES_URL, {
        method: "GET",
        headers: {
          Accept: "application/json",
          "User-Agent": "memecoin-inspection-candidate-listing/1",
        },
        signal: controller.signal,
      });
    } catch (cause) {
      if (controller.signal.aborted) {
        throw new CandidateProviderError(
          "DexScreener candidate request timed out.",
          "PROVIDER_TIMEOUT",
        );
      }
      throw new CandidateProviderError(
        "DexScreener candidate request failed.",
        "PROVIDER_FAILURE",
      );
    }

    const bounded = await readBoundedBody(response.body);
    if (!response.ok) {
      throw new CandidateProviderError(
        `DexScreener returned HTTP ${response.status}.`,
        "PROVIDER_HTTP_ERROR",
        response.status,
      );
    }

    return {
      endpoint: DEXSCREENER_TOKEN_PROFILES_URL,
      statusCode: response.status,
      responseBytes: bounded.bytes,
      receivedAt: new Date().toISOString(),
      body: bounded.text,
    };
  } catch (cause) {
    if (cause instanceof CandidateProviderError) throw cause;
    throw new CandidateProviderError(
      "DexScreener candidate response could not be read.",
      "PROVIDER_FAILURE",
    );
  } finally {
    clearTimeout(timeout);
  }
}

function optionalString(
  value: unknown,
  field: string,
  issues: string[],
): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value !== "string") {
    issues.push(`${field}_not_string`);
    return null;
  }
  return value;
}

function entryType(value: unknown): "object" | "array" | "null" | "string" | "number" | "boolean" {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value as "object" | "string" | "number" | "boolean";
}

function normalizeLinks(value: unknown, issues: string[]) {
  if (value === undefined || value === null) return null;
  if (!Array.isArray(value)) {
    issues.push("links_not_array");
    return null;
  }
  if (value.length > MAX_LINKS_PER_ENTRY) issues.push("links_bounded_to_20");
  return value.slice(0, MAX_LINKS_PER_ENTRY).map((link) => {
    if (!link || typeof link !== "object" || Array.isArray(link)) {
      issues.push("link_not_object");
      return { type: null, label: null, url: null };
    }
    const source = link as Record<string, unknown>;
    return {
      type: optionalString(source.type, "link_type", issues),
      label: optionalString(source.label, "link_label", issues),
      url: optionalString(source.url, "link_url", issues),
    };
  });
}

function normalizeEntry(value: unknown, providerIndex: number) {
  const type = entryType(value);
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {
      provider_index: providerIndex,
      provider_entry_type: type,
      chainId: null,
      tokenAddress: null,
      url: null,
      icon: null,
      header: null,
      description: null,
      links: null,
      status: "INVALID" as const,
      inspectable: false,
      duplicate_of_index: null,
      issues: ["entry_must_be_object"],
    };
  }

  const source = value as Record<string, unknown>;
  const issues: string[] = [];
  const chainId = optionalString(source.chainId, "chainId", issues);
  const tokenAddress = optionalString(source.tokenAddress, "tokenAddress", issues);
  const entry = {
    provider_index: providerIndex,
    provider_entry_type: type,
    chainId,
    tokenAddress,
    url: optionalString(source.url, "url", issues),
    icon: optionalString(source.icon, "icon", issues),
    header: optionalString(source.header, "header", issues),
    description: optionalString(source.description, "description", issues),
    links: normalizeLinks(source.links, issues),
    status: "MISSING_IDENTITY" as
      | "SELECTABLE"
      | "DUPLICATE"
      | "MISSING_IDENTITY"
      | "INVALID",
    inspectable: false,
    duplicate_of_index: null as number | null,
    issues,
  };

  if (!chainId || !tokenAddress) {
    entry.status = "MISSING_IDENTITY";
    entry.issues.push("chainId_and_tokenAddress_required");
    return entry;
  }
  if (
    chainId.length > 64 ||
    tokenAddress.length > 128 ||
    !IDENTIFIER_RE.test(chainId) ||
    !IDENTIFIER_RE.test(tokenAddress)
  ) {
    entry.status = "INVALID";
    entry.issues.push("chainId_or_tokenAddress_invalid");
    return entry;
  }

  entry.status = "SELECTABLE";
  entry.inspectable = true;
  return entry;
}

function buildListing(provider: CandidateProviderResponse, payload: unknown) {
  if (!Array.isArray(payload)) {
    throw new CandidateProviderError(
      "DexScreener candidate response was not a list.",
      "PROVIDER_FAILURE",
    );
  }
  if (payload.length > MAX_CANDIDATE_ENTRIES) {
    throw new CandidateProviderError(
      "DexScreener returned more candidates than the bounded listing allows.",
      "PROVIDER_FAILURE",
    );
  }

  const candidates = payload.map((value, index) => normalizeEntry(value, index));
  const firstIdentity = new Map<string, number>();
  for (const candidate of candidates) {
    if (!candidate.inspectable || !candidate.chainId || !candidate.tokenAddress) continue;
    const identity = `${candidate.chainId}\u0000${candidate.tokenAddress}`;
    const first = firstIdentity.get(identity);
    if (first !== undefined) {
      candidate.status = "DUPLICATE";
      candidate.duplicate_of_index = first;
    } else {
      firstIdentity.set(identity, candidate.provider_index);
    }
  }

  const result = {
    source: "DexScreener" as const,
    endpoint: provider.endpoint,
    selection_basis: "Provider order from the documented latest token-profiles listing.",
    admission_status: "NOT_ADMITTED" as const,
    completeness: "BOUNDED_PROVIDER_LISTING" as const,
    limit: MAX_CANDIDATE_ENTRIES,
    received_at: provider.receivedAt,
    http_status: provider.statusCode,
    response_bytes: provider.responseBytes,
    truncated: false,
    candidates,
    selectable_count: candidates.filter((candidate) => candidate.inspectable).length,
    invalid_count: candidates.filter((candidate) => !candidate.inspectable).length,
    duplicate_count: candidates.filter((candidate) => candidate.status === "DUPLICATE").length,
  };
  const validated = ListCandidateTokensResponse.safeParse(result);
  if (!validated.success) {
    throw new CandidateProviderError(
      "The normalized candidate listing did not match its published contract.",
      "PROVIDER_FAILURE",
    );
  }
  return validated.data;
}

export function createCandidateListingsRouter(
  fetcher: CandidateListingFetcher = fetchLatestTokenProfiles,
): IRouter {
  const router: IRouter = Router();
  let activeListings = 0;

  router.get("/candidate-listings", async (_req, res) => {
    if (activeListings >= MAX_CONCURRENT_LISTINGS) {
      return errorResponse(
        res,
        429,
        "CANDIDATE_LISTING_BUSY",
        "Candidate listing capacity is currently full.",
        "Wait for the active provider request to finish.",
      );
    }

    activeListings += 1;
    try {
      let provider: CandidateProviderResponse;
      try {
        provider = await fetcher();
      } catch (cause) {
        const failure =
          cause instanceof CandidateProviderError
            ? cause
            : new CandidateProviderError(
                "DexScreener candidate request failed.",
                "PROVIDER_FAILURE",
              );
        if (failure.code === "PROVIDER_TIMEOUT") {
          return errorResponse(
            res,
            504,
            failure.code,
            "The candidate listing timed out.",
            "DexScreener did not return a complete bounded listing in time.",
          );
        }
        return errorResponse(
          res,
          502,
          failure.code,
          "The candidate listing could not be completed.",
          "The documented provider listing was unavailable or invalid.",
        );
      }

      let payload: unknown;
      try {
        payload = JSON.parse(provider.body);
      } catch {
        return errorResponse(
          res,
          502,
          "PROVIDER_MALFORMED_RESPONSE",
          "The candidate listing returned malformed data.",
          "DexScreener did not return valid JSON.",
        );
      }

      try {
        return res.status(200).json(buildListing(provider, payload));
      } catch (cause) {
        const failure =
          cause instanceof CandidateProviderError
            ? cause
            : new CandidateProviderError(
                "The candidate listing could not be normalized.",
                "PROVIDER_FAILURE",
              );
        return errorResponse(
          res,
          502,
          failure.code === "PROVIDER_FAILURE"
            ? "INVALID_PROVIDER_LISTING"
            : failure.code,
          "The candidate listing could not be completed.",
          "The provider response did not match the bounded candidate-listing contract.",
        );
      }
    } finally {
      activeListings -= 1;
    }
  });

  return router;
}

export default createCandidateListingsRouter();