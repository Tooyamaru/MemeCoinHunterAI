# P04-T10 — Feature Snapshot History Boundary

**Status:** SPECIFICATION READY / IMPLEMENTATION PRESENT / AUDIT NOT CLAIMED  
**Phase:** P04 — Market & Signal Intelligence  
**Task:** P04-T10  
**Specification type:** Architecture and implementation-boundary specification  
**Contract version:** `p04-t10-v1`  
**Provider posture:** Provider-neutral; deterministic; local/in-memory; no external I/O

## 1. Task identity

P04-T10 is the **Feature Snapshot History Boundary**. It defines the
point-in-time, immutable representation of an already-created P04-T09 feature
calculation result and the deterministic local history that holds such
snapshots.

This document is the authoritative specification for the T10 boundary. It
documents the implementation that exists in the repository; it does not by
itself assert that the implementation has passed its final audit.

T10 does not authorize a new feature family, a provider, an API, persistence,
network behavior, prediction, scoring, trading, or execution.

## 2. Architectural purpose

P04-T09 produces an immutable feature-calculation result from accepted,
point-in-time inputs. A calculation result is an analytical output, but a
later consumer needs a stable record of exactly what that result said at the
calculation boundary. T10 provides that record without recalculating or
refreshing it.

The snapshot boundary exists to:

- preserve the result as it existed at its reference time;
- preserve the input and upstream provenance required for replay;
- prevent later data from overwriting or changing an earlier result;
- prevent look-ahead and future-data leakage when a result is consumed later;
- provide a canonical representation and digest for identity and comparison;
- distinguish a valid snapshot from an invalid input without silently repairing
  or substituting data; and
- provide deterministic duplicate detection and retrieval for local history.

The snapshot is a factual, analytical record. It is not a signal, score,
prediction, opportunity, decision, authorization, order, or trade instruction.

## 3. Boundary

The T10 boundary is:

```text
accepted P04-T09 FeatureCalculationResult
        ↓
T10 validation and revalidation
        ↓
immutable FeatureCalculationSnapshot
        ↓
deterministic FeatureCalculationSnapshotHistory
```

T10 accepts a P04-T09 `FeatureCalculationResult`, verifies that the result is
still a valid canonical T09 result, and captures its meaningful fields in a
`FeatureCalculationSnapshot`.

T10 **does not recalculate the feature**. It does not inspect raw market data,
select observations, recompute a formula, change a value, apply a freshness
threshold, or replace an upstream result. The value and status are copied only
after T09 result validation succeeds.

Snapshot creation is fail-closed. Invalid, tampered, structurally malformed,
non-canonical, future-inconsistent, or linkage-inconsistent T09 results do not
produce a snapshot.

## 4. Dependencies and allowed provenance

### 4.1 Required dependency

T10 depends directly on the P04-T09 result contract:

- P04-T09 Feature Definition & Calculation Boundary;
- T09 contract version `p04-t09-v1`;
- `FeatureCalculationResult` and its canonical representation;
- T09 feature status, reason-code, input-reference, upstream-reference, and
  snapshot-linkage semantics; and
- the T09 result representation digest and result identity.

T10 is not a second calculation boundary. A change to a formula or feature
definition belongs to T09 or to a separately approved feature specification,
not to T10.

### 4.2 Carried P02 provenance

T10 preserves, but does not originate or reinterpret, provenance established
by the relevant P02 contracts:

- P02-T07 accepted market-observation evidence;
- P02-T08 immutable market-state references, including state version and
  state digest; and
- P02-T09 provider-neutral market-intelligence observation and accepted-result
  contracts.

The snapshot may carry P02 contract versions, observation identities, source
and subject identity, timestamps, and upstream state references because those
fields are part of the accepted T09 result. T10 must not manufacture a P02
reference or weaken a P02 provenance invariant.

### 4.3 P04 relationship

P04-T06 and P04-T07 establish downstream signal snapshot and history patterns
that are compatible with point-in-time provenance. T10 does not require a
runtime dependency on signal snapshots or signal history, and it does not
mutate them. A future downstream consumer may carry the T10 linkage as an
input reference while preserving its own contract and digest.

No provider adapter, API, database, migration, worker, AI/LLM service,
network client, or new third-party dependency is an allowed T10 dependency.

## 5. Entry criteria

T10 may be treated as an authorized implementation boundary only when:

1. The P04-T09 result contract is available and versioned.
2. The supplied input is an actual `FeatureCalculationResult`, not a raw
   provider payload, generic mapping, or unvalidated substitute.
3. The T09 result can be revalidated without external lookup or wall-clock
   access.
4. The T09 result preserves its canonical representation, representation
   digest, result identity, input references, upstream references, and
   snapshot linkage.
5. The T09 contract version is explicitly supported.
6. T10 remains limited to capture, validation, immutable representation,
   deterministic local history, and focused tests.
7. No implementation change is used to hide a documentation or audit gap.

## 6. Scope

T10 includes:

1. An immutable `FeatureCalculationSnapshot` representation.
2. A snapshot factory that accepts an already-created T09 result.
3. An explicit snapshot result wrapper for valid and invalid input outcomes.
4. Revalidation of T09 status, contract version, fields, canonical
   representation, identity, digests, timestamps, inputs, and linkage.
5. Canonical UTC timestamp and finite `Decimal` representation rules.
6. Immutable snapshot read representations.
7. A deterministic, in-memory snapshot history.
8. Duplicate detection by snapshot representation digest.
9. Deterministic retrieval ordering and history digest calculation.
10. Explicit invalid-input outcomes that do not mutate history.
11. Focused tests for all behavior listed in this specification.

The scope is local and provider-neutral. T10 does not imply durable storage or
historical retention outside the process.

## 7. FeatureCalculationSnapshot contract

`FeatureCalculationSnapshot` is a frozen representation of one valid,
canonical T09 result. It preserves the following fields.

| Field | Contract meaning |
| --- | --- |
| `calculation_result_id` | Identity of the captured T09 calculation result. |
| `status` | The original T09 `FeatureCalculationStatus`; T10 does not reinterpret it. |
| `reason_codes` | The T09 reason set, normalized as sorted unique non-empty text. |
| `feature_id` | Stable identifier of the calculated feature. |
| `feature_version` | Explicit version of the feature definition. |
| `calculation_contract_version` | The consumed T09 contract version; currently `p04-t09-v1`. |
| `value` | The finite `Decimal` value only when status is `CALCULATED`; otherwise null. |
| `value_unit` | Unit of the feature value when calculated; otherwise null. |
| `price_unit` | The source price unit, when present in the T09 result. |
| `quote_asset` | The source quote asset, when present in the T09 result. |
| `source_id` | Source identity carried by T09. |
| `chain_id` | Chain identity carried by T09. |
| `token_identity` | Token identity carried by T09. |
| `market_subject_id` | Market-subject identity carried by T09. |
| `reference_time` | Explicit calculation reference time, normalized to UTC when present. |
| `freshness_policy` | The explicit T09 freshness policy, preserved without alteration. |
| `evaluation_id` | Deterministic evaluation identity when supplied by T09. |
| `inputs` | Ordered immutable T09 input references used or inspected by the result. |
| `upstream_references` | Immutable P02 state/provenance references carried by T09. |
| `input_set_digest` | Digest of the canonical input-reference set. |
| `snapshot_linkage` | Immutable linkage joining reference time, inputs, upstream references, P02 version, and T09 result digest. |
| `result_representation_digest` | Canonical representation digest of the captured T09 result. |
| `contract_version` | T10 snapshot contract version; currently `p04-t10-v1`. |

The snapshot preserves both a calculated result and a T09 non-success result.
For every non-`CALCULATED` status, `value` and `value_unit` must be null.
T10 must not turn `UNKNOWN`, `INVALID`, or `UNSUPPORTED` into a numeric value.

The snapshot exposes a canonical representation and a representation digest.
The canonical representation includes all meaningful fields above, including
the T10 contract version and nested linkage material.

## 8. Snapshot creation and result wrapper

The explicit snapshot operation returns a
`FeatureCalculationSnapshotResult`. Its observable fields are:

- `snapshot_status`;
- `snapshotted`;
- `snapshot`, nullable;
- `reason_codes`;
- `calculation_result_id`, when safely recoverable from the input;
- `result_representation_digest`, when safely recoverable from the input; and
- `contract_version`.

The wrapper has two outcomes:

### 8.1 `SNAPSHOTTED`

`SNAPSHOTTED` means that:

- the input was a valid canonical `FeatureCalculationResult`;
- its T09 contract version was supported;
- its value/status relationship was valid;
- its canonical representation and digest were valid;
- its identity and input digest were valid;
- its timestamps and future-data constraints were valid;
- its upstream references and snapshot linkage were consistent; and
- an immutable `FeatureCalculationSnapshot` was produced.

`snapshotted` is true and `snapshot` is non-null. The wrapper has no reason
codes for this successful outcome.

### 8.2 `INVALID_INPUT`

`INVALID_INPUT` means that no snapshot was produced. `snapshotted` is false
and `snapshot` is null. The standard invalid-input reason is
`INVALID_CALCULATION_RESULT`; the reason set is normalized and must never be
used as a pretext for constructing a partial snapshot.

The direct convenience operation may raise a deterministic validation error
when the explicit result is invalid. The explicit result-wrapper operation is
the fail-closed observable outcome for callers that need to handle invalid
input without exception-driven control flow.

## 9. Snapshot validation rules

T10 must validate or revalidate the following before creating a snapshot.

### 9.1 T09 contract version

The captured result must declare the supported P04-T09 contract version
`p04-t09-v1`. Unsupported or missing versions are invalid input. T10 must not
assume that a future or unknown version is compatible.

The snapshot’s `calculation_contract_version` must equal the result’s T09
contract version, and its own `contract_version` must identify T10.

### 9.2 Canonical result and status

The result must be a canonical `FeatureCalculationResult` with:

- a valid normalized `FeatureCalculationStatus`;
- non-empty feature identity and feature version;
- normalized reason codes;
- valid value/status correspondence;
- valid input and upstream-reference collections;
- valid snapshot linkage; and
- a representation digest that matches the canonical result representation.

`CALCULATED` requires a finite `Decimal` and a non-empty `value_unit`.
`UNKNOWN`, `INVALID`, and `UNSUPPORTED` require no value and no value unit.

### 9.3 Immutable representation

The snapshot is immutable after creation. Its dataclass state, input tuples,
upstream-reference tuples, linkage, and canonical read representation must not
be alterable through the public object.

Nested canonical mappings and sequences exposed to callers are immutable read
views. Creating a snapshot must not mutate the source T09 result, its input
references, its upstream references, or any caller-owned collection.

### 9.4 Finite Decimal requirements

Any snapshot value must be a finite `Decimal`. NaN, positive infinity,
negative infinity, binary-float artifacts represented as an invalid result,
and non-Decimal calculated values are rejected. Null is the only allowed
value for a non-calculated status.

T10 preserves T09’s canonical decimal semantics. It does not recalculate,
round, clamp, interpolate, extrapolate, or otherwise alter the value.

### 9.5 Normalized reason codes

Reason codes must be non-empty text values, deduplicated, and sorted into one
canonical order. An input whose reason-code tuple is not already normalized is
not accepted as a canonical T09 result.

### 9.6 Timezone-aware timestamps

Every present result, linkage, and input timestamp must be timezone-aware.
Canonical representation uses UTC ISO-8601 timestamps. Naive timestamps,
timestamps with an unusable offset, or timestamps that cannot be represented
canonically are invalid.

T10 preserves the distinction between observation time, received time, and
calculation reference time.

### 9.7 Input and upstream-reference validation

Inputs must be immutable T09 `FeatureInputReference` values and upstream
references must be immutable T09 `FeatureUpstreamReference` values. Their
collections must be tuples in the canonical T09 order.

The snapshot must preserve:

- observation identities and timestamps;
- source, chain, token, and market-subject identity;
- canonical input values and price semantics;
- P02 market-intelligence contract version;
- upstream state version and state digest; and
- upstream contract version.

T10 does not infer missing provenance, replace a reference with a digest only,
or manufacture a state reference.

### 9.8 Input-set digest validation

`input_set_digest` must equal the digest of the canonical input-reference
material supplied by the T09 result. A mismatch indicates tampering or a
non-canonical result and must produce `INVALID_INPUT`.

### 9.9 Snapshot-linkage validation

`snapshot_linkage` must agree with the result and with the snapshot:

- `reference_time` must match, including nullness after UTC normalization;
- `input_set_digest` must match;
- `observation_ids` must equal the input observation identities in order;
- `upstream_references` must match the result’s references;
- the carried P02 contract version must be preserved; and
- `feature_representation_digest` must equal the T09 result representation
  digest.

The linkage is a reference record, not a persistence claim.

### 9.10 Result identity validation

The captured `calculation_result_id` must be the deterministic identity
derived from the T09 result representation digest. A result whose identity or
representation digest does not agree with its canonical content is rejected.

The snapshot does not invent a separate calculation identity. Its
`calculation_result_id` is the identity of the T09 result it captures.

### 9.11 Future-input protection

When `reference_time` is present, every input’s `observation_time` and
`received_time`, when present, must be less than or equal to that reference
time after UTC normalization.

An input after the reference time is invalid at the snapshot boundary. T10
must not sort it away, drop it, replace it with processing time, or construct
a snapshot from the remaining fields. T10 does not permit a later snapshot
operation to hide future-data leakage that should have been rejected by T09.

## 10. Determinism requirements

For the same canonical T09 result and the same T10 contract version, snapshot
creation must produce the same status, fields, canonical representation, and
digest.

Determinism requires:

- canonical serialization with sorted mapping keys and fixed sequence order;
- UTC ISO-8601 timestamps;
- canonical finite `Decimal` text rather than locale-dependent formatting;
- explicit representation of null, boolean, string, numeric, mapping, and
  sequence values;
- SHA-256 over the canonical UTF-8 JSON representation;
- sorted and deduplicated reason codes;
- no wall clock, random value, environment variable, provider state, network,
  filesystem, or database influence; and
- no observable mutation of source objects.

The T10 digest hashes only its canonical representation. Repeating the
operation with the same serialized T09 result must reproduce the same bytes
and digest.

## 11. Snapshot history contract

`FeatureCalculationSnapshotHistory` is a deterministic, local, in-memory
history of valid T10 snapshots. It is not a database, durable store, cache
with refresh behavior, or external retention system.

The history is keyed by each snapshot’s representation digest. It accepts
only an already-created `FeatureCalculationSnapshot` and validates the
snapshot again before storing it.

### 11.1 History result type

Each insertion attempt returns an immutable
`FeatureCalculationSnapshotHistoryResult` containing:

- `outcome`;
- `accepted`;
- the attempted or existing `snapshot`, when applicable;
- an immutable tuple `snapshots` representing the history after the attempt;
- normalized `reason_codes`;
- `history_digest`; and
- the T10 `contract_version`.

`accepted` is true only for `STORED`. It is false for `DUPLICATE` and
`INVALID_INPUT`.

### 11.2 `STORED`

`STORED` means the snapshot passed validation and its digest was not already
present. The snapshot is added exactly once. The result returns that snapshot,
the deterministic current history view, and no reason code.

### 11.3 `DUPLICATE`

`DUPLICATE` means a snapshot with the same canonical snapshot digest is
already stored. The history is unchanged. The result returns the existing
stored snapshot, the unchanged history view, and
`SNAPSHOT_ALREADY_STORED`.

Duplicate detection is by snapshot digest, not by insertion order, object
identity, arrival time, or a provider-specific key.

### 11.4 `INVALID_INPUT`

`INVALID_INPUT` means the attempted value was not a valid normalized T10
snapshot. The result contains no accepted attempted snapshot, returns the
unchanged history view, and carries `INVALID_SNAPSHOT`.

Invalid insertion must never mutate the stored snapshot set or its digest.

### 11.5 Deterministic retrieval

Retrieval returns a tuple of immutable snapshot references. The order is
independent of insertion order and is determined by lexicographic comparison
of each snapshot’s canonical JSON representation. Appending a snapshot does
not make arrival order part of the history contract.

Equivalent histories constructed from the same set of snapshots must return
the same ordered sequence and the same history digest.

### 11.6 Immutable read views

History result views and retrieval results are immutable tuples. The snapshots
inside them are immutable T10 snapshots. Reading history must not expose a
mutable internal collection or permit callers to rewrite a stored snapshot.

The history object itself may accept later valid insertions; immutability
applies to each snapshot and each returned read view, not to the local
append-capable container.

## 12. Duplicate semantics

A semantically identical canonical snapshot must not be stored twice.

For T10, semantic identity is the SHA-256 digest of the snapshot’s canonical
representation under the same T10 contract version. Two separately created
snapshot objects with byte-equivalent canonical representations are therefore
duplicates even if their Python object identities differ.

A different digest is not a duplicate merely because it shares a feature,
subject, timestamp, or calculation result. T10 must not collapse distinct
canonical records using an undocumented business key.

## 13. History integrity and digest

The history digest is derived from:

1. the canonical representations of all stored snapshots;
2. those representations in deterministic retrieval order; and
3. the T10 contract version.

The resulting canonical JSON material is hashed with SHA-256. The digest is
therefore sensitive to any accepted snapshot content, its position in the
canonical order, or the T10 contract version.

Deterministic ordering is mandatory because hashing an insertion-ordered
collection would make equivalent histories produce different digests. The
history digest is an integrity and reproducibility value; it does not claim
durable persistence, external audit storage, or a database transaction.

## 14. Error and fail-closed behavior

Expected invalid-data conditions must be observable as explicit non-success
outcomes, not repaired by fallback. In particular, T10 must not:

- recalculate a feature;
- replace a malformed result with a partial result;
- replace null with zero or an empty value;
- ignore an invalid reason/status relationship;
- accept an unsupported T09 version;
- accept a digest or identity mismatch;
- discard a future input;
- rebuild provenance from an untrusted payload; or
- mutate history after invalid insertion.

Programming/type violations that make direct object construction impossible
may raise a deterministic validation error. The explicit result wrappers must
remain available for callers that require an observable fail-closed outcome.

## 15. Out-of-scope behavior

The following are explicitly outside P04-T10:

- feature calculation or formula evaluation;
- feature selection or observation selection;
- prediction or machine learning;
- scoring or ranking;
- signal generation;
- opportunity generation;
- decision making;
- trading or paper-trading execution;
- wallet access, signing, or broadcast;
- provider adapters or provider selection;
- RPC, HTTP, network, or other external calls;
- APIs, workers, schedulers, retries, or orchestration;
- database, filesystem persistence, migrations, or durable retention;
- historical backfill or streaming;
- freshness-policy invention or wall-clock freshness evaluation;
- mutation of P02 evidence/state or P04 signal snapshots/history; and
- changes to roadmap numbering or unrelated governance documents.

The local history is a deterministic testable boundary, not a persistence
implementation.

## 16. Testing requirements

Focused tests must cover at least:

1. valid snapshot creation from a valid T09 calculated result;
2. preservation of T09 status, value, units, identity, and contract version;
3. preservation of feature, market-subject, source, and quote identity;
4. invalid or unsupported T09 result rejection;
5. invalid result-wrapper semantics and explicit `INVALID_INPUT`;
6. snapshot immutability;
7. immutable nested canonical representations and read views;
8. canonical representation completeness;
9. finite Decimal acceptance and non-finite-value rejection;
10. normalized reason-code validation and preservation;
11. timezone-aware timestamp normalization to UTC;
12. input and upstream-reference type and content validation;
13. input-set digest validation;
14. snapshot-linkage preservation and mismatch rejection;
15. calculation-result identity validation;
16. result representation digest validation;
17. future observation and future received-time rejection;
18. source-result immutability after snapshot creation;
19. repeated creation producing the same representation and digest;
20. valid history insertion producing `STORED`;
21. duplicate insertion producing `DUPLICATE`;
22. invalid insertion producing `INVALID_INPUT`;
23. invalid insertion leaving history and digest unchanged;
24. duplicate detection by snapshot digest;
25. deterministic retrieval independent of insertion order;
26. immutable history read views;
27. deterministic empty-history behavior;
28. history digest derivation and repeatability;
29. same snapshot set producing the same history digest;
30. absence of wall-clock, random, provider, network, database, filesystem,
    and environment influence; and
31. repeatability from identical canonical serialized inputs.

Tests must assert that no invalid or non-calculated result obtains a numeric
snapshot value and that T10 performs no feature recalculation.

## 17. Exit criteria

P04-T10 may be marked **DONE** only when:

- this specification is present and is the governing T10 contract;
- the implementation matches the boundary and field contract here;
- all snapshot and history tests in section 16 pass;
- valid T09 results are captured without recalculation;
- malformed, non-canonical, future-inconsistent, and linkage-inconsistent
  results fail closed;
- snapshots and returned history views are immutable;
- duplicate snapshots are not stored twice;
- retrieval ordering and history digests are deterministic;
- provenance and P02/T09 contract versions are preserved;
- no provider, external I/O, persistence, networking, AI, scoring,
  prediction, decision, trading, or execution behavior is introduced; and
- no unrelated baseline or roadmap document is silently changed.

P04-T10 may be marked **CLOSED** only after the DONE criteria are met and the
implementation boundary has been reviewed against the specification.

P04-T10 may be marked **AUDITED PASS** only after an independent final audit
verifies the implementation, tests, deterministic/fail-closed behavior, and
scope compliance. This specification does not record that audit result.

Any failed criterion is a failure of the T10 boundary; there is no partial
PASS claim.

## 18. Documentation / Governance Notes

The following repository conditions were found while preparing this
specification:

1. `docs/MASTER_BLUEPRINT.md` still says that no later P04 task has started and
   identifies P04-T08 as the next/undefined task. The repository contains an
   implemented P04-T10 snapshot and history boundary. The blueprint was not
   rewritten by this specification-only step.
2. `PROJECT_STATE.md` still identifies P04-T08 as the current task and records
   P04-T01 through P04-T07, but does not record the existing T10
   implementation. Its status was not changed here.
3. `docs/CHANGELOG.md` records P04-T08 as the latest task and contains
   historical language that no later P04 implementation was started. That
   governance record is stale relative to the existing T10 source and was not
   changed here.
4. Dedicated `docs/P04-T06_SPECIFICATION.md` and
   `docs/P04-T07_SPECIFICATION.md` files were not present during inspection,
   although their implementations and project-control references exist.
   T10 therefore relies on the established T09 contract and the existing
   P04-T06/P04-T07 implementation boundaries without inventing new
   dependencies or modifying those documents.

These conflicts require a later governance synchronization and audit decision.
They do not authorize T10 to claim CLOSED or AUDITED PASS.

## 19. Governance

Implementation must remain consistent with this specification and with the
upstream P04-T09 contract. Any change to the T10 fields, statuses, validation
rules, canonical representation, digest inputs, duplicate semantics, ordering,
history behavior, or scope requires:

1. an update to this specification;
2. an explicit review of compatibility with P04-T09 and carried P02
   provenance; and
3. a new verification and audit decision.

No implementation change may silently reinterpret an existing snapshot or
result. Contract changes require a new version or an explicitly reviewed
migration boundary. GitHub remains the source of truth, and this
specification-only step does not authorize a commit or push.