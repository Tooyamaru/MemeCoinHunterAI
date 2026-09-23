# P01-RTI-09 — Bounded Read-Only Lifecycle API Contract Conformance

## 1. Status

COMPLETE / CLOSED / CI PASS

The owner approved P01-RTI-09 and authorized final specification
reconciliation plus limited implementation on 2026-09-23. This document is the
controlling specification for that implementation.

## 2. Purpose

P01-RTI-09 is a verification and compatibility gate over the already-closed
P01-RTI-06 detail transport and P01-RTI-08 collection transport. It establishes
combined contract-conformance evidence without adding a new runtime capability.

The only governed resource-family routes are:

```text
GET /api/v1/paper-lifecycle-results
GET /api/v1/paper-lifecycle-results/{lifecycle_result_digest}
```

P01-RTI-09 owns focused conformance tests and checkpoint evidence only. It does
not own application queries, persistence, validation, integrity, snapshots,
artifact ordering, catalog ordering, cursor semantics, HTTP business mapping,
or a new result vocabulary.

## 3. Existing owners remain authoritative

- P01-RTI-03 remains the digest-validation, persistence, integrity, immutable
  snapshot, and artifact-ordering owner.
- P01-RTI-05 remains the exact lifecycle-result application query owner.
- P01-RTI-06 remains the detail transport and its status/serialization owner.
- P01-RTI-07 remains the digest catalog, limit, cursor, ordering, page,
  storage-outcome, and result-digest owner.
- P01-RTI-08 remains the collection transport and its status/serialization
  owner.
- Existing request-ID middleware remains the request-correlation owner.
- Existing global exception handling remains the safe unexpected-error owner.

P01-RTI-03 through P01-RTI-08 behavior is frozen and must not be reopened or
redesigned.

## 4. Exact route and parameter contract

The generated OpenAPI lifecycle resource family must contain exactly the two
path templates listed in section 2 and only the `GET` operation on each.

The collection operation exposes exactly two optional query parameters:

- `limit`;
- `after_digest`.

The detail operation exposes exactly one required path parameter:

- `lifecycle_result_digest`.

No command, trigger, filter, search, sort, offset, page, latest, history,
analytics, projection, deletion, retry, repair, or alternate identity parameter
is authorized.

## 5. Exact advertised response contract

### 5.1 Collection route

The collection operation advertises exactly:

| Status | Schema |
| --- | --- |
| `200` | `PaperLifecycleDigestCatalogResponse` |
| `422` | `TransportErrorResponse` |
| `500` | `TransportErrorResponse` |
| `503` | `PaperLifecycleDigestCatalogResponse` |

The catalog schema requires exactly:

- `contract_version`;
- `outcome`;
- `reason_codes`;
- `limit`;
- `after_digest`;
- `lifecycle_result_digests`;
- `next_after_digest`;
- `result_digest`.

### 5.2 Detail route

The detail operation advertises exactly:

| Status | Schema |
| --- | --- |
| `200` | `PaperLifecycleReadResponse` |
| `404` | `PaperLifecycleReadResponse` |
| `409` | `PaperLifecycleReadResponse` |
| `422` | `TransportErrorResponse` |
| `500` | `TransportErrorResponse` |
| `503` | `PaperLifecycleReadResponse` |

The detail schema requires exactly:

- `contract_version`;
- `outcome`;
- `reason_codes`;
- `lifecycle_result_digest`;
- `result_digest`;
- `run`;
- `artifacts`.

The existing run and artifact component schemas remain exact RTI-06 transport
representations. They must not expose raw database identifiers or models.

### 5.3 Safe error schema

`TransportErrorResponse` contains only one required `error` object. That object
contains exactly:

- `code`;
- `message`;
- `request_id`.

No exception detail, traceback, SQL, filesystem path, secret, malformed input,
or stored payload may enter the safe `422` or `500` response.

## 6. Runtime conformance

Focused verification must establish that:

- collection requests invoke only the RTI-07 catalog dependency;
- detail requests invoke only the RTI-05 query dependency;
- the collection path is not interpreted as a detail identity;
- RTI-06 status mappings remain `200`, `404`, `409`, `422`, `500`, and `503`;
- RTI-08 status mappings remain `200`, `422`, `500`, and `503`;
- exact response fields, result digests, provenance, immutable snapshots, and
  artifact ordering pass through unchanged under their existing owners;
- supported success and error responses preserve `Cache-Control: no-store`
  and existing `X-Request-ID`; and
- repeated unchanged requests remain equivalent apart from request
  correlation metadata.

## 7. Forbidden endpoint and mutation conformance

`POST`, `PUT`, `PATCH`, and `DELETE` against either governed route must return
method rejection and must not invoke the catalog, detail query, or lifecycle
owner.

Command-style or nested forbidden paths must not be advertised by OpenAPI,
must not resolve as authorized operations, and must not invoke catalog, detail
query, RTI-04, lifecycle, or admission owners.

The existing detail path necessarily treats one arbitrary path segment as a
candidate `lifecycle_result_digest`; malformed identity handling remains the
closed RTI-06/RTI-03 `422` contract and is not a command endpoint.

## 8. No-production-code-change rule

The default implementation consists only of:

- one focused contract-conformance test module; and
- checkpoint/governance documentation.

Production code must not change when the existing API conforms. If focused
tests reveal an actual mismatch between generated OpenAPI metadata and the
closed RTI-06/RTI-08 runtime contract, only a metadata-only or minimal
corrective change may be considered. It must preserve all application and
runtime semantics and document the exact discrepancy. Any semantic mismatch
outside that narrow correction is a blocker and must return to controller
review.

## 9. Determinism and test isolation

- OpenAPI assertions use the local application schema only.
- Runtime tests use offline ASGI transport and dependency overrides.
- No external provider, network, wall clock, randomness, filesystem ordering,
  or live database is required.
- No insert, update, delete, upsert, repair, migration, artifact regeneration,
  lifecycle execution, or RTI-04 invocation occurs.
- Existing result digests may be asserted but are not recalculated by a new
  transport owner.

## 10. Required verification

Focused tests must prove:

1. exact lifecycle OpenAPI paths and `GET` methods;
2. exact collection and detail parameters;
3. exact advertised response statuses and component schemas;
4. exact required fields for catalog, detail, run, artifact, and safe error
   components;
5. collection/detail route separation and owner isolation;
6. representative existing runtime mapping for `200`, `404`, `409`, `422`,
   `500`, and `503`;
7. safe error bodies and no internal-detail leakage;
8. existing `Cache-Control: no-store` and `X-Request-ID` behavior;
9. mutation methods invoke no owner;
10. forbidden nested paths invoke no owner;
11. no unauthorized lifecycle command is advertised; and
12. no production code change is present when the contract already conforms.

Relevant RTI-06 and RTI-08 regressions, combined P01-RTI regressions, the full
Python suite, module compilation, whitespace checks, TypeScript typechecks and
workspace builds, and standard GitHub CI must pass before closure.

## 11. Forbidden scope

P01-RTI-09 must not add:

- endpoint, HTTP method, parameter, lookup identity, response field, outcome,
  application service, repository, model, migration, or dependency;
- command API, manual trigger, filter, search, latest/history, analytics,
  projection, retention, archival, deletion, `ETag`, cache relaxation,
  generated client, WebSocket, subscription, or telemetry backend;
- authentication, authorization, rate limiting, CORS change, hosting, public
  deployment, API gateway, or dashboard integration;
- provider, polling, worker, scheduler, queue, retry loop, wallet, signing,
  broadcast, execution, live trading, realization, settlement, economic
  authority, G2, G3, G4, or P09; or
- any behavior change to RTI-03 through RTI-08.

Completion of P01-RTI-09 selects or authorizes no subsequent gate.

## 12. Implementation checkpoint

The generated OpenAPI and runtime behavior conform to this specification, so
no production code change was required. One focused contract-conformance test
module was added. Fifteen focused tests, 32 relevant RTI-06/08 regressions, 119
combined P01-RTI-01 through RTI-09 regressions, and the full 1,489-test Python
3.13 suite pass. Module compilation, whitespace checks, TypeScript typechecks,
and workspace builds also pass. GitHub Actions run #69 passed both required
jobs, and PR #24 was squash-merged to `main` at `986f298`.
