# P01-RTI-08 — Bounded Read-Only Persisted Lifecycle Digest Catalog API

## 1. Status

IMPLEMENTED / LOCAL VERIFICATION PASS / CI PENDING

The owner approved P01-RTI-08 and authorized final specification
reconciliation plus limited implementation on 2026-09-23. This document is the
controlling specification for that implementation.

## 2. Purpose and dependency direction

P01-RTI-08 exposes the closed P01-RTI-07 digest catalog through one bounded,
read-only HTTP collection route. It is a transport and serialization boundary
only.

```text
GET with optional limit and after_digest
    -> P01-RTI-08 transport
    -> PaperLifecycleDigestCatalogService.query(...)
    -> authoritative P01-RTI-07 result
```

The transport must not call `PaperLifecycleRepository`, a SQLAlchemy model, a
database session, P01-RTI-04, or another lifecycle boundary directly.

## 3. Ownership

- P01-RTI-08 owns query-text decoding, HTTP response serialization, status
  mapping, and safe transport errors only.
- P01-RTI-07 remains the application catalog and the sole owner of default and
  maximum limit, cursor validation, ordering, page semantics, storage outcomes,
  result immutability, and `result_digest`.
- P01-RTI-03 remains the canonical lifecycle digest-syntax owner through
  RTI-07.
- P01-RTI-05 and RTI-06 remain the single-result application query and detail
  transport owners.
- P01-RTI-03 through RTI-07 behavior remains closed and unchanged.

## 4. Endpoint

The only authorized endpoint is:

```text
GET /api/v1/paper-lifecycle-results?limit=<optional>&after_digest=<optional>
```

The collection path intentionally shares the RTI-06 resource family while
remaining distinct from the RTI-06 detail route:

```text
GET /api/v1/paper-lifecycle-results/{lifecycle_result_digest}
```

No `POST`, `PUT`, `PATCH`, `DELETE`, trigger, command, retry, repair, replay, or
regeneration endpoint is authorized.

## 5. Input and validation

- Omitted `limit` delegates the P01-RTI-07 default of `50`.
- A supplied `limit` is decoded from query text to an integer, then delegated
  to RTI-07 for its authoritative `1..100` application validation.
- Omitted `after_digest` delegates `None`.
- A supplied `after_digest` is passed unchanged to RTI-07.
- The transport does not implement a digest regex, normalization, lowercase
  conversion, trimming, or independent range validator.

There is no offset, page number, sort, filter, search, latest, history,
timestamp, database ID, token, symbol, pool, opportunity, wallet, alternate
digest identity, or other lookup parameter.

Structural integer decoding failure or any RTI-07 input `ValueError` maps to a
single safe HTTP `422 Unprocessable Entity` envelope:

```json
{
  "error": {
    "code": "invalid_catalog_query",
    "message": "limit or after_digest is invalid",
    "request_id": "<existing request ID>"
  }
}
```

The response must not contain the malformed value, raw Python exception,
validator internals, traceback, SQL, credentials, or stored data. Invalid
input is never converted to an empty `PAGE` or `STORAGE_UNAVAILABLE`.

## 6. Exact response schema

Both `PAGE` and `STORAGE_UNAVAILABLE` serialize exactly these authoritative
P01-RTI-07 fields:

| Field | JSON type | Source |
| --- | --- | --- |
| `contract_version` | string | RTI-07 result |
| `outcome` | string | `PAGE` or `STORAGE_UNAVAILABLE` |
| `reason_codes` | array of strings | RTI-07 result |
| `limit` | integer | validated RTI-07 result |
| `after_digest` | string or null | RTI-07 result |
| `lifecycle_result_digests` | array of strings | ordered RTI-07 tuple |
| `next_after_digest` | string or null | RTI-07 result |
| `result_digest` | lowercase SHA-256 string | authoritative RTI-07 digest |

The transport must not add `total_count`, page number, generated links,
timestamps, latest/history semantics, filters, search, database metadata,
artifacts, bundle detail, `FOUND`, economic fields, or interpretations.

## 7. HTTP mapping

| Condition | HTTP status | Body |
| --- | --- | --- |
| RTI-07 `PAGE`, including an empty page | `200 OK` | Exact eight-field catalog response |
| RTI-07 `STORAGE_UNAVAILABLE` | `503 Service Unavailable` | Exact eight-field catalog response with safe bounded reason code and no entries |
| Invalid `limit` or `after_digest` | `422 Unprocessable Entity` | Fixed safe `invalid_catalog_query` envelope |
| Unexpected exception | `500 Internal Server Error` | Existing safe global error envelope |

The transport may branch on the closed RTI-07 outcome only to choose HTTP
status. It must not reinterpret, rename, or recalculate application results.

## 8. Headers and observability

Every response, including `200`, `422`, `500`, and `503`, must contain:

```text
Cache-Control: no-store
X-Request-ID: <existing request correlation ID>
```

The existing request-ID middleware remains the correlation owner. The route
must not introduce a second request-ID generator. Logging must not add malformed
query values, lifecycle identities, canonical payloads, storage internals, or
secrets. New metrics, tracing backends, and telemetry dependencies are outside
scope.

## 9. Ordering, cursor, and determinism

P01-RTI-08 preserves the RTI-07 lexicographic digest order exactly. It neither
re-sorts identities nor creates a cursor. `after_digest`,
`next_after_digest`, and `result_digest` are serialized unchanged.

Equivalent requests over unchanged persisted state produce equivalent JSON
bodies. Request IDs are correlation headers/error-envelope values and do not
enter the RTI-07 result digest. No wall clock, randomness, provider, network
lookup, filesystem order, current market, decision policy, RTI-04 invocation,
worker, scheduler, or ambient mutable state is introduced.

## 10. Read-only boundary

Each valid request invokes `PaperLifecycleDigestCatalogService.query(...)` at
most once. P01-RTI-08 performs no insert, update, delete, upsert, repair,
migration, artifact read, root snapshot construction, bundle validation,
lifecycle reconstruction, automatic retry, or integrity claim.

Catalog presence remains only root-identity presence. It is not
`PaperLifecycleReadOutcome.FOUND`. Complete detail and integrity lookup remains
owned by P01-RTI-05/P01-RTI-03 through the unchanged RTI-06 detail route.

## 11. Authorized implementation shape

The limited implementation may add only:

- the smallest convention-consistent catalog response schema, dependency
  wiring, and collection `GET` under `backend/api/`;
- router registration only if required by the chosen module shape;
- focused offline ASGI transport tests; and
- governance documentation and exports only where necessary.

No model, migration, repository change, application-service change,
third-party dependency, frontend, generated client, authentication,
authorization, rate limiting, CORS change, hosting, public deployment, API
gateway, or dashboard integration is authorized.

## 12. Verification requirements

Focused tests must establish:

1. omitted parameters delegate RTI-07 defaults and return `200 PAGE`;
2. explicit valid `limit` and `after_digest` delegate exactly once;
3. exact eight-field serialization and authoritative `result_digest`;
4. identity ordering and continuation are preserved without re-sorting;
5. empty page remains `200`, not `404`;
6. maximum `100` is accepted;
7. invalid integer text, zero, negative, above-maximum, uppercase, wrong-length,
   and non-hex input return the fixed safe `422` envelope;
8. `STORAGE_UNAVAILABLE` returns `503` with the exact bounded result body;
9. repeated unchanged requests have equivalent bodies;
10. `Cache-Control: no-store` and existing `X-Request-ID` appear on every
    response class;
11. unexpected exceptions use the existing safe `500` boundary;
12. mutation methods are rejected and never invoke RTI-07;
13. no repository/session/model, RTI-04, artifact, lifecycle, admission,
    provider, worker, scheduler, queue, wallet, execution, G2, G3, G4, or P09
    dependency exists in the transport; and
14. RTI-03 through RTI-07 regressions and the RTI-06 detail route remain green.

Focused tests, relevant RTI regressions, the full Python suite, module
compilation, whitespace checks, TypeScript typechecks/builds, and standard
GitHub CI must pass before closure.

## 13. Forbidden scope and following gate

P01-RTI-08 adds no provider runtime, polling, automatic selection, worker,
scheduler, queue, retry loop, dashboard/Hunter Room, wallet, signing,
broadcast, execution, live trading, realization, settlement, accounting,
economic authority, G2, G3, G4, or P09 behavior.

Filtering, search, latest/history lookup, richer projections, analytics,
retention, archival, deletion, auth, rate limiting, CORS changes, hosting,
public deployment, API gateway, and dashboard integration remain separate
future gates. Completion selects or authorizes no subsequent gate.

## 14. Implementation checkpoint

The bounded route, response schema, dependency wiring, and focused transport
tests are implemented without changing RTI-03 through RTI-07 behavior.
Eighteen focused tests, 35 relevant RTI-06/07 regressions, 104 combined
P01-RTI-01 through RTI-08 regressions, and the full 1,474-test Python 3.13
suite pass. Module compilation, whitespace checks, TypeScript typechecks, and
workspace builds also pass. GitHub CI and merge remain pending.
