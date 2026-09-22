# P01-RTI-06 — Bounded Read-Only Paper Lifecycle Result API

## 1. Status

AUTHORIZED / IMPLEMENTED / LOCAL CHECKPOINT PASS / CI PENDING

The owner explicitly authorized this limited implementation against the merged
specification. The bounded transport is implemented and locally verified;
GitHub CI and merge are pending.

## 2. Purpose

P01-RTI-06 may expose one persisted paper lifecycle result to an explicit
caller by its canonical `lifecycle_result_digest`. It is a transport and
serialization boundary only.

The dependency direction is fixed:

```text
HTTP GET with lifecycle_result_digest
    -> P01-RTI-06 transport mapping
    -> PaperLifecycleQueryService.query(...)
    -> ControlledPaperPersistenceService.read(...)
    -> authoritative PaperLifecycleReadResult
```

P01-RTI-06 must not call a repository, SQLAlchemy model, or database session
directly. P01-RTI-05 remains the application query owner, and P01-RTI-03
remains the persistence, digest-validation, integrity, snapshot, and ordering
owner.

## 3. Authorized implementation boundary

The bounded implementation may add only:

- one versioned read-only HTTP route;
- explicit response schemas that serialize the existing immutable snapshots;
- dependency wiring from the existing application database runtime to
  `ControlledPaperPersistenceService` and `PaperLifecycleQueryService`;
- deterministic mapping of existing query outcomes and malformed input to
  HTTP responses;
- focused offline transport tests; and
- minimal exports and governance documentation.

It may not add a second query service, repository, digest validator, persistence
contract, lifecycle implementation, or result vocabulary.

## 4. Endpoint

The only proposed endpoint is:

```text
GET /api/v1/paper-lifecycle-results/{lifecycle_result_digest}
```

Properties:

- `GET` is the only authorized method;
- the path contains exactly one lookup identity;
- there are no query-parameter aliases or fallback identities;
- there is no collection/list endpoint;
- there is no pagination, search, filtering, sorting, or latest-result lookup;
- there is no `POST`, `PUT`, `PATCH`, `DELETE`, command, trigger, retry, repair,
  replay, or regeneration endpoint; and
- request correlation continues to use the existing `X-Request-ID`
  middleware.

The route must not be described as a public internet deployment. Authentication,
authorization policy, rate limiting, CORS expansion, gateway publication, and
external hosting remain separate future decisions. An implementation must not
weaken any existing deployment boundary.

## 5. Canonical input identity and validation ownership

`lifecycle_result_digest` is the only accepted lookup identity. Canonically it
is a lowercase 64-character SHA-256 digest.

The HTTP layer accepts the path segment as text and delegates it unchanged to
`PaperLifecycleQueryService.query(...)`. It must not introduce a regex,
normalizer, lowercase conversion, trimming, digest parser, or independent
SHA-256 validator. This preserves P01-RTI-03 as the single authoritative
validation owner through P01-RTI-05.

The transport must not look up or infer a result by:

- invocation ID;
- database row ID;
- admission, decision, paper-result, history, or observation digest;
- timestamp or latest/most-recent semantics;
- token, symbol, chain, pool, opportunity, or wallet identity; or
- any other secondary identifier.

## 6. Malformed-input contract

Malformed identity is distinct from a valid identity that is not stored.

When RTI-05 propagates RTI-03's authoritative
`ValueError("lifecycle_result_digest must be a digest")`, the transport maps it
to HTTP `422 Unprocessable Entity` with this safe error shape:

```json
{
  "error": {
    "code": "invalid_lifecycle_result_digest",
    "message": "lifecycle_result_digest must be a lowercase SHA-256 digest",
    "request_id": "<existing request correlation id>"
  }
}
```

The transport must not return `NOT_FOUND` for malformed input. It must not echo
the malformed value, a traceback, database detail, or internal exception text.
No other `ValueError` or unexpected exception may be broadly reclassified as
invalid input; unexpected failures remain owned by the existing safe internal
error boundary.

## 7. Authoritative output and serialization

The transport consumes the existing `PaperLifecycleReadResult`. It does not
create a parallel domain result. JSON serialization is a transport projection
only and must preserve the exact values supplied by RTI-05.

The response representation for all four query outcomes contains:

| Field | JSON type | Source |
|---|---:|---|
| `contract_version` | string | `PaperLifecycleReadResult.contract_version` |
| `outcome` | string | existing `PaperLifecycleReadOutcome` value |
| `reason_codes` | array of strings | existing ordered reason codes |
| `lifecycle_result_digest` | string | exact requested canonical identity |
| `result_digest` | string | existing read-result digest |
| `run` | object or null | existing immutable run snapshot |
| `artifacts` | array | existing ordered artifact snapshots |

The transport uses JSON arrays for existing tuples without reordering them.
It must not recalculate digests, parse or rewrite `canonical_payload`, rename
owner fields, infer omitted artifacts, or expose SQLAlchemy/database models.

### 7.1 Run snapshot

For `FOUND`, `run` serializes the existing
`PaperLifecycleRunSnapshot.canonical_representation` fields:

- `contract_version`;
- `outcome`;
- `reason_codes`;
- `admission_digest`;
- nullable `fill_digest`, `transition_digest`, `ledger_digest`,
  `reconciliation_digest`, `paper_result_digest`, `history_digest`, and
  `observation_digest`;
- `lifecycle_result_digest`;
- nullable `decision_intent_digest` and `simulation_input_digest`; and
- `artifact_count`.

No economic labels or interpretations may be added.

### 7.2 Artifact snapshots

For `FOUND`, each artifact serializes the existing
`PaperLifecycleArtifactSnapshot.canonical_representation` fields:

- `artifact_kind`;
- `artifact_digest`;
- `payload_digest`;
- `owner_contract_version`;
- `canonical_payload`; and
- `ordinal`.

Artifacts retain RTI-03's ascending ordinal order. `canonical_payload` remains
the exact canonical JSON string from the application contract; the transport
must not parse it into a second mutable object or redact/reconstruct individual
owner fields. No raw database columns or row identifiers are exposed.

## 8. Outcome-to-HTTP mapping

| RTI-05 result | HTTP status | Response body |
|---|---:|---|
| `FOUND` | `200 OK` | complete read-result representation with run and ordered artifacts |
| `NOT_FOUND` | `404 Not Found` | read-result representation with existing reason codes, `run: null`, and `artifacts: []` |
| `CORRUPT` | `409 Conflict` | read-result representation with existing reason codes, `run: null`, and `artifacts: []` |
| `STORAGE_UNAVAILABLE` | `503 Service Unavailable` | read-result representation with existing reason codes, `run: null`, and `artifacts: []` |
| malformed digest | `422 Unprocessable Entity` | safe transport error from section 6 |
| unexpected internal failure | `500 Internal Server Error` | existing safe error envelope |

`CORRUPT` uses `409` because the requested canonical identity exists but its
authoritative stored bundle cannot satisfy the read contract. The route must
not convert it into `404`, `200`, or a repaired representation.

`STORAGE_UNAVAILABLE` uses `503`; it must not be converted into `NOT_FOUND`.
This specification does not add `Retry-After`, automatic retry, fallback
storage, or health-state mutation.

## 9. HTTP representation rules

- The success media type is `application/json`.
- Existing enum values are serialized as their exact uppercase strings.
- Nullable fields remain JSON `null`; they are not omitted or invented.
- Empty reason codes and artifacts are JSON arrays.
- The route returns the existing `X-Request-ID` response header.
- Responses must include `Cache-Control: no-store`; shared/proxy caching and
  conditional `ETag` behavior are not authorized by this gate.
- Transport timestamps, server time, generated-at fields, links, pagination
  metadata, market data, prices, P&L, ROI, or derived summaries are forbidden.
- OpenAPI documentation may describe only this exact read contract. It must
  not advertise command, execution, provider, or future-phase endpoints.

## 10. Read-only and deterministic guarantees

For one canonical digest and unchanged authoritative persisted state, the HTTP
status and JSON result fields are deterministic. The correlation ID is
transport metadata and does not enter domain or result digests.

The route performs no:

- insert, update, delete, upsert, migration, or database repair;
- lifecycle reconstruction, artifact regeneration, or corruption correction;
- RTI-04 invocation or paper-run triggering;
- admission, decision, risk, fill, reconciliation, history, observation, or
  learning execution;
- provider, market, RPC, DEX, filesystem, random, or wall-clock lookup;
- scheduler, worker, queue, polling, retry, or background task; or
- wallet, key, signing, broadcast, settlement, or live-trading action.

## 11. Application wiring constraints

Any later implementation must reuse the `DatabaseRuntime` already owned by the
FastAPI lifespan. It may construct or inject the existing RTI-03 persistence
service and RTI-05 query service, but it must not start a second database
runtime or store request-specific mutable global state.

The route must depend on `PaperLifecycleQueryService`, not
`ControlledPaperPersistenceService` directly. The transport may serialize the
returned immutable result and map its outcome; it may not inspect storage or
re-evaluate integrity independently.

The existing `/health` and `/ready` semantics remain unchanged. Query-level
`STORAGE_UNAVAILABLE` is represented by the endpoint's `503` response and does
not mutate runtime readiness.

## 12. Security and observability

- No secret, credential, connection string, traceback, SQL text, filesystem
  path, or internal exception detail may appear in a response.
- Logs may include request method, route template, status, request ID, outcome,
  and canonical lifecycle digest; they must not include canonical artifact
  payloads or secret values.
- The existing request-ID middleware remains the sole correlation mechanism.
- The endpoint is observational only and must not be used as proof of economic
  realization, settlement, on-chain truth, or execution.
- Public exposure, caller identity, access-control policy, abuse prevention,
  and retention policy require separate deployment/security authorization.

## 13. Focused implementation test requirements

Focused offline tests must prove:

1. one exact valid persisted digest returns `200` and delegates once to RTI-05;
2. `FOUND` preserves lifecycle identity, contract versions, result digest,
   provenance, canonical payload strings, and artifact order;
3. an unknown valid digest returns `404` with the unchanged `NOT_FOUND`
   vocabulary and identity;
4. malformed, uppercase, wrong-length, and non-hex inputs return `422` and are
   never mapped to `NOT_FOUND`;
5. the transport introduces no independent digest regex or normalizer;
6. `CORRUPT` returns `409` without snapshots, mutation, or repair;
7. `STORAGE_UNAVAILABLE` returns `503` and is not collapsed into `404`;
8. unexpected exceptions return the existing safe `500` envelope without
   internal details;
9. response schemas never expose raw models or database row IDs;
10. repeated reads over unchanged state have equivalent status and domain JSON;
11. request IDs are preserved/generated without entering result digests;
12. only `SELECT` statements occur and corrupted storage remains unchanged;
13. unsupported mutation methods cannot invoke RTI-05 or persistence writes;
14. no RTI-04, admission, lifecycle, provider, network, scheduler, worker,
   queue, wallet, execution, G2, G3, G4, or P09 dependency is reachable; and
15. existing `/health`, `/ready`, RTI-03, RTI-04, and RTI-05 regressions remain
   unchanged and pass.

The transport tests must not duplicate RTI-03's deep corruption suite or
RTI-05's application-delegation suite beyond representative boundary cases.

## 14. Implemented shape

The implementation is limited to:

- `backend/api/paper_lifecycle_results.py` for explicit response schemas,
  dependency wiring, serialization, and outcome mapping;
- minimal router registration and safe-error response headers in
  `backend/api/main.py`;
- `tests/test_paper_lifecycle_results_api.py` for focused offline transport
  verification; and
- governance updates.

No database migration, model, repository, third-party dependency, frontend,
dashboard, or generated client is required by this specification.

## 15. Explicitly forbidden scope

P01-RTI-06 does not authorize:

- a paper-run creation or RTI-04 trigger endpoint;
- list/latest/history/search endpoints;
- dashboard or Hunter Room integration;
- WebSocket, streaming, webhook, or subscription behavior;
- provider runtime, market polling, automatic selection, scheduler, worker,
  queue, retry loop, or continuous operation;
- decision, risk/capital, execution, wallet, signing, broadcast, live trading,
  realization, settlement, accounting, P&L, ROI, WIN/LOSS, or strategy labels;
- G2, G3, G4, P09, or any subsequent phase; or
- modification or reopening of P01-RTI-03, RTI-04, or RTI-05 behavior.

P08-G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3, G4, and P09 remain
NOT AUTHORIZED.

## 16. Implementation checkpoint

The owner authorized the limited P01-RTI-06 implementation against this
document. Fourteen focused transport tests, 12 RTI-05 regressions, 65 combined
P01-RTI-01 through P01-RTI-06 regressions, and the full 1,435-test Python 3.13
suite pass. Module compilation, whitespace checks, TypeScript typechecks, and
all workspace builds pass. One pre-existing Starlette warning and the known
frontend sourcemap warning remain non-blocking. GitHub CI and merge are pending.

No gate after P01-RTI-06 is selected or authorized by this specification.
