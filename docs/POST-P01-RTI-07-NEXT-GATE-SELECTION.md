# Post-P01-RTI-07 Next-Gate Selection

**Status:** direction approved / superseded by the controlling P01-RTI-08
specification

**Verified baseline:** `main` and `origin/main` at
`5c95818dfa01d48801d3255c0dfa6fb0a33a0c30` on 2026-09-23; worktree clean
before this documentation checkpoint; P01-RTI-07 complete / closed / CI pass.

## 1. Selection constraints

This checkpoint selected one prospective bounded gate only. The controller
later approved its direction and authorized final specification reconciliation
plus limited implementation under
`P01-RTI-08-BOUNDED-READ-ONLY-PERSISTED-LIFECYCLE-DIGEST-CATALOG-API-SPECIFICATION.md`.
The selected gate must not open or depend on G2,
G3, G4, P09, provider runtime, worker, scheduler, queue, wallet, execution,
live trading, or dashboard/Hunter Room. P01-RTI-03 through P01-RTI-07 remain
closed and their behavior must not be redesigned.

The official candidate set below is limited to work expressly deferred by the
P01-RTI-03, RTI-04, RTI-06, and RTI-07 specifications or by the master
blueprint. A deferred item is a candidate for separate specification, not an
authorization.

## 2. Candidate assessment

| Official candidate | Architecture readiness | Dependency readiness | Boundedness | Determinism | Testability | Observability | Governance risk | Blast radius | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Read-only HTTP transport for the RTI-07 digest catalog | High: existing FastAPI boundary and RTI-06 conventions are closed and proven | High: RTI-07 page contract, database runtime, request ID, and safe error handler exist | High if limited to one collection `GET` and existing query parameters | High: transport serializes the deterministic RTI-07 result without adding time, sorting, or state | High with dependency overrides and offline ASGI tests | High: existing `X-Request-ID`, status codes, safe 500, and `Cache-Control: no-store` | Low if it delegates only to RTI-07 and exposes no new lookup semantics | Small: one transport module/router registration and focused tests; no schema change | **Recommended** |
| Filtering or search | Low-medium: no governed filter vocabulary or secondary identity | Low: canonical semantics for token, outcome, date, or other filters are absent | Low unless split into multiple gates | Medium-low because query meaning and ordering are unresolved | Medium after policy decisions | Medium | High: can create accidental domain/search authority | Medium-high across application, repository, and transport | Defer |
| Latest or history lookup | Low | Low: `created_at` is operational metadata and no canonical latest/history policy exists | Medium in code, weak in semantics | Low: wall-clock/insertion ordering risks contradict current digest ordering | Medium | Medium | High: operational time may become domain truth | Medium | Defer |
| Richer result projection or analytics | Low-medium | Low: projection fields, interpretation ownership, and integrity guarantees are not governed | Low unless narrowly separated | Medium | Medium | Medium | High: may introduce economic or analytical interpretation | Medium-high | Defer |
| Retention, archival, or deletion | Low | Low: lifecycle, recovery, and audit-retention policy do not exist | Potentially bounded but destructive | Medium | Medium-low due recovery requirements | High requirement, currently unspecified | High: conflicts with append-only audit expectations | High | Defer |
| Paper-run/manual-trigger API over RTI-04 | Technically medium | Medium: RTI-04 exists, but transport request/error authority is unspecified | Medium | Medium-high for explicit input, but it creates state | High | High with request ID and persistence outcomes | High: opens mutation and paper-lifecycle invocation, excluded by current constraints | Medium-high | Ineligible |
| Upstream market-to-opportunity application/runtime composition | Low / blocked | Low: authoritative historical evidence, source authentication, source-time linkage, and market-to-signal policy remain unresolved | Low | Low until those authorities are fixed | Low-medium | Medium | High | High | Blocked / defer |
| Provider runtime, polling, or operational loop | Excluded | Blocked by provider and operational policy decisions | Low | Low because network/time/retry state enters behavior | Medium only after substantial infrastructure | High requirement | Explicitly prohibited | High | Ineligible |
| Worker, scheduler, queue, retry, or continuous paper loop | Excluded | Not authorized | Low | Low-medium due asynchronous state | Medium | High requirement | Explicitly prohibited | High | Ineligible |
| Dashboard or Hunter Room publication | Excluded | Requires separate presentation/read-model decisions | Low-medium | Medium | Medium | High requirement | Explicitly prohibited | High | Ineligible |
| Wallet, signing, broadcast, live trading, G2, G3, G4, or P09 | Blocked or unauthorized | Missing separate authorities and future gates | Outside this boundary | Outside this boundary | Outside this boundary | Critical requirement | Prohibited | Critical | Ineligible |

## 3. Recommended next bounded gate

### P01-RTI-08 — Bounded Read-Only Persisted Lifecycle Digest Catalog API

P01-RTI-08 should be specified as a transport-only boundary exposing the
existing P01-RTI-07 catalog through exactly one versioned collection `GET`:

```text
GET /api/v1/paper-lifecycle-results?limit=50&after_digest=<optional-digest>
```

The path intentionally shares the existing RTI-06 resource family:

- RTI-08 collection route: `/api/v1/paper-lifecycle-results`; and
- RTI-06 detail route:
  `/api/v1/paper-lifecycle-results/{lifecycle_result_digest}`.

P01-RTI-08 is the smallest repository-supported successor because RTI-07
explicitly reserved its HTTP transport as a separate future gate. It can reuse
the existing FastAPI lifecycle, database runtime, safe exception boundary,
request correlation, and no-store convention without changing application or
persistence semantics.

## 4. Specification outline for controller review

### 4.1 Purpose and ownership

- Add one read-only HTTP collection route over
  `PaperLifecycleDigestCatalogService`.
- P01-RTI-08 owns only query-parameter decoding, response serialization, and
  HTTP status mapping.
- P01-RTI-07 remains the application catalog, limit, cursor, ordering, page,
  storage-failure, immutability, and result-digest owner.
- P01-RTI-03 remains the canonical digest-syntax owner.
- P01-RTI-05/RTI-06 remain the detail-query/detail-transport owners.
- The transport must not call `PaperLifecycleRepository`, SQLAlchemy models,
  sessions, or RTI-04 directly.

### 4.2 Proposed endpoint and input

```text
GET /api/v1/paper-lifecycle-results
```

- Optional `limit`; omitted means the RTI-07 default `50`.
- Optional `after_digest`; passed unchanged as the RTI-07 cursor.
- No offset, page number, sort, filter, search, latest, history, timestamp,
  database ID, token, symbol, opportunity, or alternate digest parameter.
- FastAPI may decode supplied query text to an integer, but it must not
  duplicate RTI-07 range/default validation.
- RTI-07 application `ValueError` remains distinct from a successful empty
  page and maps to one safe `422` transport error.
- The full specification must fix one consistent safe `422` envelope for both
  structurally non-integer `limit` input and RTI-07 validation failures without
  echoing malformed values.

### 4.3 Proposed successful response

`PAGE` maps to HTTP `200` and serializes exactly:

- `contract_version`;
- `outcome` = `PAGE`;
- `reason_codes`;
- `limit`;
- `after_digest`;
- ordered `lifecycle_result_digests`;
- `next_after_digest`; and
- authoritative RTI-07 `result_digest`.

An empty catalog or cursor with no successor is still HTTP `200 PAGE`. The
transport adds no timestamp, total count, page number, generated links,
database metadata, integrity claim, lifecycle detail, artifact, or economic
interpretation.

### 4.4 Proposed error mapping

| RTI-07 / transport condition | HTTP status | Required behavior |
| --- | --- | --- |
| `PAGE`, including empty | `200 OK` | Exact deterministic page serialization |
| `STORAGE_UNAVAILABLE` | `503 Service Unavailable` | Preserve RTI-07 contract fields and safe reason code |
| Invalid `limit` or malformed `after_digest` | `422 Unprocessable Entity` | Safe fixed error envelope; no malformed value or internal detail |
| Unexpected exception | `500 Internal Server Error` | Existing safe global error boundary |

All responses must use `Cache-Control: no-store` and preserve the existing
`X-Request-ID` behavior. No storage exception, SQL, credential, payload,
traceback, or internal exception text may leak.

### 4.5 Ordering, cursor, and determinism

- The transport must preserve RTI-07 digest order without re-sorting.
- It must preserve `after_digest` and `next_after_digest` without generating a
  cursor, link, offset, or page token.
- It must preserve the RTI-07 `result_digest`, not calculate a transport digest.
- Equivalent requests over unchanged persisted state produce equivalent JSON
  bodies apart from request-correlation headers.
- No clock, randomness, provider, network lookup, filesystem order, current
  market state, decision rule, RTI-04 invocation, or ambient mutable state.

### 4.6 Read-only and observability requirements

- Exactly one RTI-07 query invocation per request.
- No insert, update, delete, upsert, repair, migration, artifact read, bundle
  validation, lifecycle reconstruction, or retry.
- Existing request-ID middleware remains the correlation owner.
- Logging must not include malformed cursor text, stored identities, database
  detail, canonical payloads, or secrets.
- No new metric, tracing backend, telemetry dependency, or public deployment
  decision is part of this gate.

### 4.7 Focused test outline

1. omitted parameters delegate RTI-07 defaults and return `200 PAGE`;
2. explicit valid `limit` and `after_digest` delegate exactly once;
3. ordered identities and continuation cursor are preserved unchanged;
4. empty page remains `200`, not `404`;
5. maximum `100` is accepted;
6. zero, negative, above-maximum, boolean-like, non-integer, uppercase,
   wrong-length, and non-hex inputs map safely to `422`;
7. `STORAGE_UNAVAILABLE` maps to `503` without semantic rewriting;
8. authoritative RTI-07 `result_digest` is preserved;
9. repeated unchanged requests have equivalent bodies;
10. all outcomes use `Cache-Control: no-store` and existing `X-Request-ID`;
11. unexpected exceptions use the existing safe `500` envelope;
12. no repository/session/model or RTI-04 dependency in the transport;
13. no artifact read, lifecycle/admission execution, mutation, or repair;
14. no provider/network, worker, scheduler, dashboard, wallet, execution,
    G2, G3, G4, or P09 dependency;
15. RTI-03 through RTI-07 focused regressions remain unchanged and green; and
16. existing RTI-06 detail route behavior remains unchanged.

### 4.8 Expected implementation shape if later authorized

- One small API transport module or the smallest convention-consistent
  extension under `backend/api/`.
- Explicit Pydantic response/error schemas for the existing RTI-07 result.
- Dependency wiring from `request.app.state.database` to
  `PaperLifecycleDigestCatalogService`.
- Minimal router registration and focused offline ASGI tests.
- No application/repository behavior change, model, migration, dependency,
  frontend, dashboard, or generated client.

## 5. Resolved controller decisions

The controller approved the single collection route and exact RTI-07 field
preservation. Invalid `limit` or `after_digest` uses one fixed safe `422`
`invalid_catalog_query` envelope without raw exception detail. `PAGE`, including
empty, maps to `200`; `STORAGE_UNAVAILABLE` maps to `503` with the bounded
RTI-07 body; unexpected exceptions use the existing safe `500`. All responses
use `Cache-Control: no-store` and existing `X-Request-ID`. Auth, rate limiting,
CORS changes, hosting, public deployment, API gateway, dashboard integration,
and every other excluded boundary remain future gates.
