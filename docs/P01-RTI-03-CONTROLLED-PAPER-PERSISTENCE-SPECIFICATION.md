# P01-RTI-03 — Controlled Paper Persistence

**Status:** COMPLETE / CLOSED / CI PASS

**Phase:** P01 runtime integration over the existing P01-T03 persistence
foundation and completed P01-RTI-02 paper lifecycle

**Scope:** atomically retain one canonical P01-RTI-02 result and every artifact
that is actually present in that result

**Proposed:** 2026-09-22

## 1. Purpose

P01-RTI-02 produces a complete, deterministic, paper-only lifecycle in memory.
P01-RTI-03 proposes the first durable boundary for that output. It must make an
accepted lifecycle inspectable after process restart without changing any P05,
P06, Risk/Capital, P07, or P08 rule.

The persistence layer is a recorder, not a domain owner. It may validate,
serialize, insert, detect an exact retry, detect a storage conflict, and read
back stored records. It must not create or repair a lifecycle artifact, rerun a
decision, reinterpret an outcome, manufacture reconciliation evidence, or
authorize any trade.

The owner explicitly authorized the limited implementation on 2026-09-22.

## 2. Existing owners remain authoritative

- P01-RTI-01 owns controlled P05 → P06 → Risk/Capital → P07-T01 admission.
- P01-RTI-02 owns the one-shot P07-T02–T07 and P08-T01 composition result.
- Each P06/P07/P08 contract owns its artifact validation, canonical form, and
  digest.
- P01-T03 owns database runtime, sessions, transactions, URL handling,
  readiness, and migration infrastructure.
- P01-T04 owns the HTTP-independent application-service layering used to join
  domain and infrastructure boundaries.
- P01-RTI-03 owns only the durable append/read boundary for one already-created
  P01-RTI-02 result.

No persistence model becomes a replacement source of truth for a domain
contract. Stored payloads are immutable audit snapshots of the canonical
objects supplied to the boundary.

P01-RTI-03 is not a complete replay-input archive. P01-RTI-02 does not retain
its original `PaperFillInstruction` or `PaperLifecycleEvidence` as output
artifacts, so this task stores only the canonical result and predecessor
artifacts that P01-RTI-02 actually preserves. Any future requirement to replay
from the exact original instruction/evidence inputs requires a separately
approved P01-RTI-02 contract revision; persistence must not infer them.

## 3. Accepted input

The write boundary accepts exactly one `ControlledPaperLifecycleResult`.

Before opening a write transaction it must:

1. require the exact supported result type and P01-RTI-02 contract version;
2. rebuild or otherwise invoke the owner's canonical validation;
3. verify the result digest;
4. validate every artifact that is present through its owning contract;
5. verify every digest/link represented by the P01-RTI-02 result; and
6. construct the full persistence bundle in memory.

The boundary may persist all four canonical P01-RTI-02 outcomes:

- `OBSERVATION_PRODUCED` with the complete artifact chain;
- `RECONCILIATION_NOT_MATCHED` with artifacts only through P07-T05;
- `ADMISSION_NOT_READY` with admission evidence and no later artifacts; and
- `INVALID_INPUT` only when the supplied P01-RTI-02 result object itself is
  canonical and explicitly records that outcome.

An invalid, tampered, unsupported, or partially serialized outer result is not
stored.

## 4. Storage design

The proposed implementation adds two append-only tables.

### 4.1 `paper_lifecycle_runs`

One row represents one exact P01-RTI-02 result:

- `id`: database surrogate primary key;
- `lifecycle_result_digest`: lowercase SHA-256, unique and immutable;
- `lifecycle_contract_version`;
- `outcome`;
- `reason_codes_json`: canonical JSON array;
- `admission_digest`;
- nullable `decision_intent_digest`;
- nullable `simulation_input_digest`;
- nullable `fill_digest`;
- nullable `transition_digest`;
- nullable `ledger_digest`;
- nullable `reconciliation_digest`;
- nullable `paper_result_digest`;
- nullable `history_digest`;
- nullable `observation_digest`;
- `artifact_count`;
- `created_at`: database operational timestamp.

`created_at` is storage metadata only. It must not enter any P01/P06/P07/P08
digest, ordering rule, simulation time, or learning fact.

### 4.2 `paper_lifecycle_artifacts`

One row retains one artifact snapshot belonging to the run:

- `id`: database surrogate primary key;
- `run_id`: foreign key to `paper_lifecycle_runs.id` with delete restricted;
- `artifact_kind`: closed P01-RTI-03 vocabulary;
- `artifact_digest`;
- `payload_digest`: SHA-256 of the exact canonical payload bytes;
- `owner_contract_version`;
- `canonical_payload`: UTF-8 canonical JSON text;
- `ordinal`: deterministic order within the run; and
- `created_at`: database operational timestamp.

The table has unique keys on `(run_id, artifact_kind)` and
`(run_id, ordinal)`. `artifact_count` must be non-negative, ordinals must be
positive and contiguous, and all digest columns must use the lowercase
64-character SHA-256 form. The initial closed artifact-kind vocabulary is:

1. `ADMISSION_RESULT`;
2. `DECISION_INTENT`;
3. `RISK_CAPITAL_AUTHORIZATION`;
4. `SIMULATION_INPUT`;
5. `FILL_OUTCOME`;
6. `PRIOR_PAPER_STATE`;
7. `STATE_TRANSITION`;
8. `RESULTING_PAPER_STATE`;
9. `LEDGER_ENTRY`;
10. `RECONCILIATION_RESULT`;
11. `PAPER_SIMULATION_RESULT`;
12. `HISTORY_RESULT`; and
13. `OUTCOME_OBSERVATION`.

Only artifacts actually present in the canonical lifecycle result may be
inserted. `RESULTING_PAPER_STATE` is omitted only when `next_state` is `None`;
when a no-change transition explicitly retains the prior state as its next
state, that canonical state is stored. Absence is represented by absence of a
row, never by a fabricated empty artifact.

## 5. Canonical serialization

Persistence uses one versioned P01-RTI-03 serializer. It recursively converts
existing canonical representations as follows:

- mappings use lexicographically sorted string keys;
- tuples become JSON arrays without reordering;
- `Decimal` values use the owning contract's canonical decimal text;
- finite legacy float values already present in owner canonical forms retain
  Python's deterministic JSON number representation; NaN and infinity fail
  closed;
- timezone-aware datetimes use normalized UTC ISO-8601 text;
- enums use their contract values;
- booleans, integers, strings, and `null` retain their JSON meanings; and
- JSON output uses UTF-8, sorted keys, and compact separators.

The serializer must consume existing canonical representations or explicit
owner fields. It must not call `str(object)`, serialize mutable `__dict__`
state, use pickle, or silently coerce an unsupported value.

For contracts whose owner digest covers their canonical payload, the stored
payload must re-hash to that digest. For aggregate/projection records such as
the P07-T07 insertion result, P01-RTI-03 stores the exact explicit fields and
the owner-provided `history_digest`; it does not invent a new P07 digest.
Every artifact also stores a separate `payload_digest` over its exact UTF-8
canonical JSON bytes so corruption can be detected even when an owner identity
digest intentionally covers a different projection.

## 6. Atomicity and transaction boundary

One write attempt uses exactly one existing
`DatabaseRuntime.session_scope()` transaction.

The transaction must insert the run row and all expected artifact rows as one
unit. A serialization failure, validation failure, constraint failure,
connection failure, cancellation, or unexpected exception must leave neither a
partial run nor partial artifact set committed.

No network/provider call, domain evaluation, retry loop, sleep, polling, API
request, or worker action may occur inside the transaction.

## 7. Write result, idempotency, and conflict semantics

The immutable write result contains the P01-RTI-03 contract version, outcome,
lifecycle result digest when it was safely obtained, stored artifact count,
canonical reason codes, and a deterministic result digest. It does not expose
database surrogate IDs, timestamps, URLs, exception messages, SQL, or payload
contents.

It has exactly these outcomes:

- `STORED`: the complete bundle was inserted once;
- `ALREADY_STORED`: a row with the same lifecycle result digest exists and its
  full stored root fields, artifact kinds, artifact and payload digests,
  ordinals, contract versions, and canonical payload bytes exactly match the
  candidate bundle;
- `CONFLICT`: the same lifecycle result digest exists but any stored value or
  artifact differs;
- `INVALID_INPUT`: owner validation, linkage, digest, serialization, or closed
  vocabulary validation failed before a commit; and
- `STORAGE_UNAVAILABLE`: the database/session/transaction could not complete.

`ALREADY_STORED` is a successful idempotent retry, not a second insert.
`CONFLICT` must fail closed and preserve the existing rows unchanged. Hash
equality alone is not sufficient for `ALREADY_STORED`; the complete persisted
bundle must match. If concurrent writers race on the unique root digest, the
losing write transaction rolls back and a fresh bounded read transaction
compares the committed bundle before returning `ALREADY_STORED` or `CONFLICT`.

The first implementation has no automatic retry. A caller may explicitly retry
the same immutable result and receive `ALREADY_STORED`.

## 8. Read boundary

The repository provides only bounded reads:

- fetch one run bundle by `lifecycle_result_digest`; and
- fetch its artifact rows ordered by `ordinal`.

The immutable read result contains `FOUND`, `NOT_FOUND`, `CORRUPT`, or
`STORAGE_UNAVAILABLE`, canonical reason codes, the root snapshot when valid,
the ordered artifact snapshots when valid, and a deterministic result digest.
It is a persistence snapshot, not a reconstructed executable domain object.
Missing root or artifact rows, duplicate kinds, non-contiguous ordinals,
artifact-count disagreement, digest disagreement, unsupported contract
versions, or malformed/non-canonical JSON must return `CORRUPT`. Reads must not
repair, delete, rewrite, or reinterpret stored data.

Listing, filtering, pagination, dashboard queries, analytics projections,
retention, archival, and deletion are deferred to separate tasks.

## 9. Failure and recovery rules

- Database failures are returned through bounded persistence outcomes without
  leaking URLs, credentials, payload contents, or stack traces.
- Rollback remains owned by the existing session boundary.
- A process restart may repeat the same write safely and receive
  `ALREADY_STORED`.
- There is no background recovery worker, queue, outbox, or scheduled retry in
  P01-RTI-03.
- There is no update or delete operation for paper lifecycle records in this
  task.
- Migration downgrade may remove the two new tables in development/test
  environments, but runtime code exposes no destructive operation.

## 10. Security and economic boundary

Canonical payloads must not contain database credentials, environment values,
private keys, seed phrases, wallet credentials, signing material, provider
secrets, HTTP headers, or raw exception text.

Persisting a lifecycle does not mean:

- the trade happened on-chain;
- capital was committed;
- profit/loss was realized;
- reconciliation established external truth;
- a wallet, position, or settlement exists outside paper state; or
- P08 learning may change a model or strategy.

The Risk Governor remains above the Decision Engine. P01-RTI-03 has no decision,
risk, execution, settlement, or learning authority.

## 11. Explicit exclusions

This task adds no:

- API route or WebSocket publication;
- scheduler, worker registration, loop, retry, polling, or queue;
- provider, RPC, DEX, or chain access;
- dashboard or Hunter Room data feed;
- wallet, signing, broadcast, live order, or settlement behavior;
- economic WIN/LOSS, ROI, or profit calculation;
- strategy/model update or P09 behavior;
- G2, G3, or G4 implementation;
- Redis, cache, object storage, or second database library; or
- migration execution against a live database.

## 12. Proposed implementation surface

The authorized implementation is limited to:

- `backend/core/models.py` for the two append-only SQLAlchemy models;
- `backend/core/repositories.py` for bounded write/read operations;
- `backend/application/paper_lifecycle_persistence.py` for validation,
  serialization, bundle construction, persistence outcomes, and coordination
  through the existing database session boundary;
- `backend/application/__init__.py` for minimal exports;
- one new Alembic migration after `0001_system_metadata`;
- `tests/test_controlled_paper_persistence.py`;
- narrowly required persistence-foundation regression tests; and
- minimal updates to `docs/PERSISTENCE.md`, `PROJECT_STATE.md`, and
  `docs/CHANGELOG.md`.

No dependency, settings, API, worker, frontend, provider, wallet, execution, or
learning-owner file is included.

## 13. Verification gate

Offline tests must prove:

1. a complete `OBSERVATION_PRODUCED` lifecycle stores one root and its exact
   ordered artifact set;
2. admission-not-ready and reconciliation-not-matched outcomes store only the
   artifacts that canonically exist;
3. an identical retry returns `ALREADY_STORED` without adding rows;
4. any differing stored field or payload under the same digest returns
   `CONFLICT` and changes nothing;
5. tampered owner digests, links, types, JSON values, or contract versions
   return `INVALID_INPUT` without opening or committing a partial write;
6. a forced failure after the root insert rolls back the root and all artifact
   rows;
7. readback preserves exact payload bytes, artifact order, owner versions, and
   digests;
8. corrupt or incomplete stored bundles fail closed on read;
9. concurrent attempts produce one stored bundle and one deterministic
   idempotent result, never two bundles;
10. SQLite test behavior and PostgreSQL-oriented constraints remain portable;
11. existing database readiness, session, repository, migration, P01-RTI-01,
    P01-RTI-02, P07, and P08 tests remain green; and
12. no external I/O, API, scheduler, wallet, execution, G2, G3, G4, or P09
    behavior is reachable.

Focused tests, persistence-foundation regressions, relevant P01/P07/P08
regressions, the full Python suite, migration metadata checks, module
compilation, TypeScript checks/builds, and `git diff --check` must pass before
merge.

## 14. Exit and following gate

P01-RTI-03 provides durable paper-lifecycle audit records only. GitHub Actions
run #36 passed both required jobs, and PR #11 was squash-merged to `main` at
`43ab170`. It does not create an operational runtime.

The next gate is the separately specified P01-RTI-04 application-service
boundary for one caller-triggered persisted paper run. Its implementation is
not authorized by this document. Scheduler,
continuous market selection, dashboard publication, Hunter Room integration,
wallet access, live execution, G2, G3, G4, and P09 remain future work.
