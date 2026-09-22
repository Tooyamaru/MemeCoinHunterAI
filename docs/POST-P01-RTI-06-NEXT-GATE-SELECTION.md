# Post-P01-RTI-06 Next-Gate Selection

**Status:** direction approved / superseded by the controlling P01-RTI-07
specification

**Verified baseline:** `main` and `origin/main` at
`c0900572b50dee1d7e9e3a819740c03e54ed7c64` on 2026-09-22; worktree clean
before this documentation checkpoint; P01-RTI-06 complete / closed / CI pass.

## 1. Selection constraints

This checkpoint selected one possible bounded gate only. The controller later
approved its direction and authorized final specification reconciliation plus
limited implementation under
`P01-RTI-07-BOUNDED-READ-ONLY-PERSISTED-LIFECYCLE-DIGEST-CATALOG-SPECIFICATION.md`.
The selected gate must not open or depend on provider runtime,
wallet, live trading, execution, worker, scheduler, dashboard/Hunter Room,
G2, G3, G4, or P09. Completed P01-RTI-03 through P01-RTI-06 behavior remains
closed.

Repository evidence limits the official post-RTI-06 candidate set to work that
was expressly deferred by the P01-RTI-03, RTI-04, and RTI-06 specifications or
by the master blueprint. A deferred item is a candidate for separate
specification, not an authorization.

## 2. Candidate assessment

| Candidate named or deferred by repository | Readiness | Dependencies | Governance risk | Boundedness / determinism / testability | Blast radius | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| Read-only persisted-result listing or pagination | Medium-high | Existing append-only run table, digest index, database/session boundary, RTI-03 identity rules | Low if limited to identities; medium if expanded into history, analytics, or validation | Strong when page size is capped, order is canonical digest order, cursor is explicit, and no clock/default “latest” behavior exists | Small: repository read plus one application contract; no model or migration expected | **Recommended as a digest catalog only** |
| Filtering, search, or latest-result lookup | Medium | A listing boundary plus new query semantics | Medium-high: secondary identities and operational timestamps can become accidental domain authority | Search/filter vocabulary is not governed; “latest” depends on operational time and concurrent state | Medium | Defer |
| HTTP transport for a future collection query | Low now | An approved application-level catalog contract must exist first | Medium if transport and storage semantics are designed together | Testable, but premature before the query owner and page contract are closed | Medium | Defer behind the recommended gate |
| API/manual trigger over P01-RTI-04 | Technically medium | RTI-04 request/result contract and transport mapping | High: opens a mutation and paper-lifecycle invocation surface; excluded by the current no-execution constraint | One-shot behavior can be tested, but request validation and side-effect failures enlarge the gate | Medium-high | Ineligible for this selection |
| Upstream market-to-opportunity runtime composition | Low / blocked | Authoritative producer, authenticated historical-price evidence, approved market-to-signal policy, source-time linkage | High: missing authority decisions could be improvised into code | Cannot yet be specified deterministically from repository-owned evidence | High | Blocked / defer |
| Dashboard or Hunter Room publication | Not assessed for implementation | Read models and presentation contract | Explicitly excluded | Would add UI/publication state beyond this checkpoint | High | Ineligible |
| Provider runtime or continuous polling | Blocked and excluded | Provider owner, runtime policy, freshness and retry semantics | Explicitly excluded | Network and ambient time enlarge nondeterminism | High | Ineligible |
| Worker, scheduler, queue, retry loop, or continuous paper loop | Excluded | Operational runtime composition | Explicitly excluded | Adds asynchronous state and operational policy | High | Ineligible |
| Wallet, signing, broadcast, live trading, G2, G3, G4, or P09 | Blocked or unauthorized | Separate unresolved authorities and future gates | Prohibited | Outside the paper-only read boundary | Critical | Ineligible |

## 3. Recommended next bounded gate

### P01-RTI-07 — Bounded Read-Only Persisted Lifecycle Digest Catalog

P01-RTI-07 should be specified as an HTTP-independent application query that
returns only a bounded, deterministic page of canonical
`lifecycle_result_digest` identities already present in the append-only
P01-RTI-03 store.

This is the smallest useful successor to the exact-digest RTI-05/RTI-06 path:
it permits callers to discover canonical identities without inventing a
secondary lookup key, exposing database rows, invoking RTI-04, or publishing a
dashboard. Detail retrieval remains owned by P01-RTI-05 and its existing
RTI-06 transport.

The recommendation is narrower than the broad listing, filtering, pagination,
and analytics work deferred by RTI-03. It authorizes none of those neighboring
features.

## 4. Specification outline for controller review

### 4.1 Purpose and ownership

- Add one application-level, read-only identity catalog.
- P01-RTI-07 owns catalog query orchestration and its immutable page contract.
- P01-RTI-03 remains persistence and canonical digest-validation owner.
- P01-RTI-05 remains the owner of complete single-result reads.
- P01-RTI-06 remains the only current HTTP result-detail route and is unchanged.
- The repository may gain one bounded identity-read operation; it must not
  become a second repository or a result-integrity implementation.

### 4.2 Proposed input boundary

- A required, explicitly bounded `limit`; the full specification must choose a
  small maximum and reject booleans, zero, negatives, and values over that
  maximum.
- An optional `after_lifecycle_result_digest` cursor.
- No offset, page number, timestamp, token, symbol, opportunity ID, invocation
  ID, database row ID, admission digest, paper-result digest, or other fallback
  lookup.
- Cursor validation must reuse or delegate the authoritative RTI-03 digest
  semantics. A copied SHA-256 regex or a second validator is forbidden.

### 4.3 Proposed output boundary

- One immutable, versioned page result.
- Entries contain only canonical `lifecycle_result_digest` values.
- Entries are ordered strictly by ascending digest text, using the existing
  indexed canonical identity; database ID and `created_at` are never exposed.
- The result includes an explicit continuation value only when another page
  exists; it contains no count of all records and no generated timestamp.
- A deterministic result digest covers the contract version, ordered identities,
  requested bound/cursor, continuation value, and bounded outcome.
- Candidate outcome vocabulary should be limited to `FOUND`, `EMPTY`, and
  `STORAGE_UNAVAILABLE`; exact names and failure reason codes require approval
  in the full specification.

### 4.4 Read and integrity semantics

- The catalog asserts only that an identity is present in the append-only root
  store; it does not certify the complete lifecycle bundle as valid.
- Complete snapshot, artifact, corruption, provenance, and ordering validation
  remains available only through P01-RTI-05 for an explicitly selected digest.
- The full specification must make this distinction explicit so catalog
  presence is never treated as `PaperLifecycleReadOutcome.FOUND`.
- No deep bundle fan-out or N+1 artifact reads belong in this gate.

### 4.5 Determinism and concurrency

- For identical input and unchanged persisted state, output is identical.
- Ordering is digest-lexicographic, never insertion order, filesystem order, or
  operational timestamp order.
- Keyset continuation uses the last returned canonical digest and an exclusive
  comparison; offset pagination is forbidden.
- Concurrent append behavior must be specified without claiming snapshot
  isolation beyond the existing database transaction. Already-returned pages
  are immutable values; later calls may observe newly appended identities.
- No wall clock, randomness, provider, network, mutable policy, or RTI-04 call.

### 4.6 Read-only and failure requirements

- No insert, update, delete, upsert, repair, migration, regeneration, or
  lifecycle reconstruction.
- Storage failures fail closed through one safe bounded result and do not leak
  database URLs, credentials, SQL, payloads, or stack traces.
- Malformed cursors remain invalid input and must not be converted to an empty
  page.
- Empty storage and a cursor with no following identities must have explicit,
  deterministic semantics in the full specification.

### 4.7 Focused test outline

1. empty store;
2. one and multiple canonical identities;
3. required limit lower/upper bounds and invalid values;
4. canonical digest ordering independent of insertion order and timestamps;
5. exclusive keyset continuation without duplicates or gaps in unchanged state;
6. malformed uppercase, wrong-length, and non-hex cursor delegation/rejection;
7. deterministic repeated reads;
8. immutable output and deterministic result digest;
9. storage-unavailable fail-closed behavior without internal leakage;
10. no artifact/deep-bundle read and no integrity-semantic claim;
11. no insert, update, delete, repair, or migration;
12. no P01-RTI-04/lifecycle/admission invocation;
13. no provider, network, worker, scheduler, dashboard, wallet, execution,
    G2, G3, G4, or P09 dependency;
14. unchanged RTI-03, RTI-04, RTI-05, and RTI-06 regressions.

### 4.8 Expected implementation shape if later authorized

- One small immutable application contract and service under
  `backend/application/`.
- One bounded repository identity-read method using the existing
  `paper_lifecycle_runs.lifecycle_result_digest` index.
- Focused tests plus existing RTI regression.
- No database model, migration, external dependency, route, public schema, or
  frontend change.

## 5. Resolved controller decisions

The controller approved the identity-only P01-RTI-07 direction with default
limit `50`, hard maximum `100`, ascending digest ordering, exclusive
`after_digest` keyset continuation, successful empty pages, closed `PAGE` and
`STORAGE_UNAVAILABLE` outcomes, application validation failures for malformed
input, and a canonical deterministic result digest. Authorization covers only
the application/repository read boundary. HTTP remains a separate future gate.
