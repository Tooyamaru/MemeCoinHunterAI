# Post-P01-RTI-08 Next-Gate Selection

**Status:** direction approved / superseded by the controlling P01-RTI-09
specification

**Verified baseline:** `main` and `origin/main` at
`2a5bee665d384f59c722873b9edfef96db7901db` on 2026-09-23; worktree clean
before this documentation checkpoint; P01-RTI-08 complete / closed / CI pass.

## 1. Selection constraints

This checkpoint selects one prospective bounded gate only. It does not
authorize implementation. P01-RTI-03 through P01-RTI-08 remain closed and
their behavior must not be redesigned.

The selected gate must not add or depend on G2, G3, G4, P09, provider runtime,
worker, scheduler, queue, wallet, execution, live trading, or dashboard/Hunter
Room. G2 remains blocked / unresolved / not authorized. No newer repository
decision makes any of those boundaries eligible.

The official candidate set is limited to existing read-only surfaces and work
expressly deferred by the RTI-03/04/06/07/08 specifications or master
governance. A deferred item is only a candidate for separate specification;
it is not implementation authorization.

## 2. Available bounded integration surface

The repository currently provides these closed, composable surfaces:

1. P01-RTI-03 owns canonical lifecycle digest validation, persistence reads,
   full-bundle integrity, immutable snapshots, and artifact ordering.
2. P01-RTI-04 owns one explicit caller-triggered persisted paper lifecycle,
   but it remains HTTP-independent and mutating.
3. P01-RTI-05 owns one application-level read by exact
   `lifecycle_result_digest` and delegates to RTI-03.
4. P01-RTI-06 owns the bounded read-only detail `GET` transport over RTI-05.
5. P01-RTI-07 owns deterministic digest-only catalog paging by `limit` and
   exclusive `after_digest`.
6. P01-RTI-08 owns the bounded read-only collection `GET` transport over
   RTI-07.
7. Existing FastAPI request-ID middleware and the safe global `500` handler
   provide transport correlation and bounded unexpected-error behavior.

The two closed read-only HTTP routes now form one resource family:

```text
GET /api/v1/paper-lifecycle-results
GET /api/v1/paper-lifecycle-results/{lifecycle_result_digest}
```

No current gate owns contract-family conformance across both routes. Focused
RTI-06 and RTI-08 tests prove their individual behavior, but there is no
single boundary that locks route separation, the exact advertised OpenAPI
surface, shared safe-error/header invariants, and absence of unsupported
operations across the combined resource family.

## 3. Official candidate assessment

| Candidate | Architecture readiness | Dependency readiness | Boundedness | Determinism | Testability | Observability | Governance risk | Blast radius | Sequencing value | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Read-only API contract conformance across RTI-06 and RTI-08 | High: both transports and contracts are closed | High: no new runtime owner or dependency | High: verification-only over two existing `GET` routes | High: fixed schemas, statuses, and headers | High: offline ASGI and OpenAPI assertions | High: locks request ID, no-store, and safe errors | Low if no runtime semantics change | Very small: specification and focused tests; metadata correction only if separately authorized | High: stabilizes the only available external read contract before any security/deployment decision | **Recommended** |
| Conditional retrieval / `ETag` | Medium-high: authoritative result digests exist | High technically | Medium-high | High | High | Medium | Medium-high: current contracts require `no-store` and RTI-06 expressly excludes conditional `ETag` | Small-medium across both transports | Low until a cache/deployment policy exists | Defer |
| Filtering or search | Low-medium: catalog exists but no filter authority | Low: no governed filter vocabulary or secondary identity | Low unless split repeatedly | Medium-low | Medium after policy decisions | Medium | High: may create accidental domain/search authority | Medium-high across application, repository, and transport | Low before a concrete caller exists | Defer |
| Latest or history lookup | Low | Low: operational timestamps are not canonical domain ordering | Medium in code, weak in semantics | Low due time/insertion-order ambiguity | Medium | Medium | High: operational time could become domain truth | Medium | Low | Defer |
| Richer projection, manifest, or analytics | Low-medium | Low: field ownership and integrity claims are unresolved | Medium only if narrowed | Medium | Medium | Medium | High: risks parallel snapshot or economic interpretation authority | Medium-high | Low without an authorized consumer | Defer |
| Retention, archival, or deletion | Low | Low: retention and recovery policy absent | Medium but destructive | Medium | Medium-low | High requirement | High: conflicts with append-only audit expectations | High | Low | Defer |
| Authentication / caller access control | Medium-low | Low: caller identity and access policy do not exist | Medium | Medium-high | Medium | High requirement | Medium-high: security policy must precede code | Medium | High before public exposure, but public exposure is not authorized | Defer pending security decision |
| Rate limiting / abuse prevention | Low-medium | Low: no identity, deployment topology, quota, or time-window policy | Medium | Low-medium due clock/state | Medium | High requirement | Medium-high | Medium | Low before auth/deployment | Defer |
| CORS, hosting, public deployment, or API gateway | Low for the current governed state | Low: environment and exposure policy unresolved | Low unless separated | Operational | Medium | Critical | High | High | Premature | Ineligible now |
| Paper-run/manual-trigger API over RTI-04 | Technically medium | Medium | Medium | Medium-high for explicit input, but it creates state | High | High requirement | High: opens mutation and lifecycle invocation | Medium-high | Premature | Ineligible now |
| Upstream market-to-opportunity runtime composition | Low / blocked | Low: source-time linkage and market-to-signal ownership remain unresolved | Low | Low | Low-medium | Medium | High | High | High eventually, not ready now | Blocked / defer |
| Provider runtime, polling, worker, scheduler, queue, retry, or continuous loop | Excluded | Not authorized | Low | Low-medium | Medium after infrastructure decisions | High requirement | Explicitly prohibited | High | Premature | Ineligible |
| Dashboard / Hunter Room publication | Excluded | Requires separate presentation/read-model authority | Low-medium | Medium | Medium | High requirement | Explicitly prohibited | High | Premature | Ineligible |
| Wallet, signing, broadcast, execution, live trading, G2, G3, G4, or P09 | Blocked or unauthorized | Missing future authorities | Outside this selection | Outside this selection | Outside this selection | Critical | Prohibited | Critical | Not available | Ineligible |

## 4. Recommended next bounded gate

### P01-RTI-09 — Bounded Read-Only Lifecycle API Contract Conformance

P01-RTI-09 should be a verification and compatibility gate over the already
closed RTI-06 detail route and RTI-08 collection route. It must not create a
third route, a new application service, a new result vocabulary, or new
runtime behavior.

This is the best next sequence because it:

- uses only closed dependencies;
- adds no market, economic, mutation, background, or deployment authority;
- makes the combined read-only transport contract mechanically reviewable;
- detects accidental route ambiguity or OpenAPI drift before later consumers;
- consolidates shared header and safe-error invariants without reopening the
  individual RTI-06 or RTI-08 semantics; and
- leaves auth, deployment, dashboard, and every operational gate separate.

## 5. Specification outline for controller review

### 5.1 Purpose

Define and verify the exact combined contract of the existing read-only
lifecycle result API family. The gate owns conformance evidence only.

It does not own persistence, application queries, validation, integrity,
ordering, pagination, serialization meaning, authentication, caching policy,
deployment, or a new transport capability.

### 5.2 In-scope routes

Only these already-existing routes are in scope:

```text
GET /api/v1/paper-lifecycle-results
GET /api/v1/paper-lifecycle-results/{lifecycle_result_digest}
```

The collection route remains owned by RTI-08 and delegates only to RTI-07.
The detail route remains owned by RTI-06 and delegates only to RTI-05, with
RTI-03 retaining validation, persistence, integrity, snapshots, and artifact
ordering.

### 5.3 Contract conformance requirements

The prospective gate should lock:

1. the exact two path templates and `GET` methods;
2. collection query parameters `limit` and `after_digest` only;
3. detail path identity `lifecycle_result_digest` only;
4. exact RTI-08 eight-field response schema for `200` and `503` catalog
   results;
5. exact RTI-06 response schema and immutable nested snapshot representation;
6. existing status mappings for RTI-06 and RTI-08 without reinterpretation;
7. fixed safe `422` envelopes for each route family;
8. the existing safe global `500` envelope;
9. `Cache-Control: no-store` and existing `X-Request-ID` on every supported
   success and error class;
10. route separation so the collection path is never treated as a malformed
    detail identity;
11. rejection of unsupported mutation methods without invoking RTI-04,
    RTI-05, or RTI-07; and
12. OpenAPI advertisement of only the already-authorized read contracts.

### 5.4 No-runtime-change rule

The default implementation expectation is specification plus focused contract
tests. No production code change is permitted merely for symmetry or cleanup.

If focused conformance tests reveal that generated OpenAPI metadata does not
match the already-governed runtime contract, any later authorized correction
must be metadata-only and must preserve runtime status, body, header,
delegation, and validation behavior. A semantic discrepancy is a blocker and
must return to controller review rather than being silently repaired under
this gate.

### 5.5 Determinism and read-only guarantees

- Tests use offline ASGI clients and dependency overrides only.
- No provider, network, wall clock, randomness, filesystem ordering, or live
  database is required.
- No insert, update, delete, upsert, repair, migration, artifact regeneration,
  lifecycle execution, or RTI-04 invocation occurs.
- Existing authoritative result digests are asserted but never recalculated by
  a new transport owner.
- No `ETag`, `If-None-Match`, cache relaxation, timestamp, link, total count,
  generated client, or telemetry backend is added.

### 5.6 Focused test outline

1. OpenAPI contains both exact read-only paths and no lifecycle command path.
2. Collection OpenAPI exposes only optional `limit` and `after_digest`.
3. Detail OpenAPI exposes only required `lifecycle_result_digest`.
4. Advertised response schemas/statuses match the closed RTI-06 contract.
5. Advertised response schemas/statuses match the closed RTI-08 contract.
6. Collection and detail route resolution remain unambiguous.
7. Representative `200`, `404`, `409`, `422`, `500`, and `503` responses
   retain their existing bodies and headers where applicable.
8. Empty catalog remains `200 PAGE`; unknown valid detail remains `404
   NOT_FOUND`; malformed inputs remain distinct safe `422` errors.
9. Existing result digests, provenance, snapshots, and artifact ordering pass
   through unchanged.
10. Repeated unchanged requests remain equivalent apart from request IDs.
11. Unsupported mutation methods invoke no query or lifecycle owner.
12. No direct repository/session/model access is introduced.
13. RTI-03 through RTI-08 focused regressions remain unchanged and green.
14. Full required Python, static, typecheck, build, whitespace, and CI checks
    pass at the implementation checkpoint.

### 5.7 Forbidden scope

P01-RTI-09 must not add:

- a new endpoint, method, query parameter, lookup identity, response field, or
  result outcome;
- filter, search, latest/history, projection, analytics, retention, archival,
  deletion, `ETag`, link, timestamp, total count, streaming, subscription, or
  generated client behavior;
- authentication, authorization, rate limiting, CORS change, hosting, public
  deployment, API gateway, or dashboard integration;
- model, migration, repository, application service, or dependency;
- provider, polling, worker, scheduler, queue, retry loop, wallet, signing,
  broadcast, execution, live trading, economic authority, G2, G3, G4, or P09;
  or
- any semantic modification or reopening of RTI-03 through RTI-08.

### 5.8 Expected implementation shape if later authorized

- one focused API contract-conformance test module;
- governance/checkpoint documentation;
- no production code change by default; and
- at most a metadata-only transport correction if the controller explicitly
  authorizes it after a documented discrepancy is found.

## 6. Controller decisions required

Before implementation, the controller should confirm:

1. P01-RTI-09 is accepted as a conformance/assurance gate rather than a new
   feature gate;
2. runtime behavior and production code are frozen unless a documented
   metadata-only mismatch is discovered;
3. generated OpenAPI is part of the governed contract surface;
4. no SDK/client generation is included; and
5. completion of RTI-09 selects or authorizes no subsequent gate.

The controller approved P01-RTI-09 as a conformance/assurance gate, froze
runtime behavior unless a real contract discrepancy requires a minimal
correction, confirmed generated OpenAPI as part of the governed surface,
excluded SDK/client generation, and authorized limited implementation. The
controlling implementation specification is
`P01-RTI-09-BOUNDED-READ-ONLY-LIFECYCLE-API-CONTRACT-CONFORMANCE-SPECIFICATION.md`.
