# P07-T04 — Paper Ledger / Append-Only Simulation Record Contract

**Status:** SPECIFICATION PROPOSED — REVIEW REQUIRED — IMPLEMENTATION NOT
AUTHORIZED  
**Phase:** P07 — Paper Trading Engine  
**Task:** P07-T04 — Paper Ledger / Append-Only Simulation Record Contract  
**Contract:** `p07-t04-v1`  
**Ledger model:** `p07-t04-ledger-v1`  
**Nature:** Immutable, provider-neutral, deterministic logical ledger record and
pure append validation only

## 1. Purpose

P07-T04 defines the logical paper-ledger boundary after the completed
P07-T03 Paper Position / Exposure State Transition Contract.

It creates one immutable, auditable record of one hypothetical paper outcome
and its identity-linked paper-state transition. The record preserves the
provenance needed to answer:

- which P06 and P07 inputs produced the outcome;
- which T02 outcome was observed;
- which prior paper state was consumed;
- which T03 transition result was produced;
- which resulting paper state was produced, when one exists;
- where the record belongs in one logical append-only stream; and
- whether the same record can be reproduced during deterministic replay.

P07-T04 is a logical contract. It may validate an explicitly supplied immutable
tuple of prior records and return a new immutable tuple for a successful
append operation. It does not store, persist, publish, transmit, reconcile, or
otherwise manage records outside the returned values.

An append result of `APPENDED` means only that a valid hypothetical record was
added to the supplied in-memory logical sequence. It is not a successful fill,
an order, an authorization, a settlement, a capital movement, or evidence of
on-chain state.

## 2. Architectural position

```text
P06 DecisionIntent
        ↓
Risk / Capital Authorization observation
        ↓
P07-T01 PaperSimulationInput
        ↓
P07-T02 PaperFillOutcome
        ↓
P07-T03 Paper Position / Exposure State
        ↓
P07-T04 Paper Ledger Record
        ↓
future P07 reconciliation / future P08
```

The ledger consumes identity-verified outputs from T02 and T03. It does not
recompute a fill, recalculate a position, or create a new state transition.

The P07-T04 record is downstream of the P07-T03 transition result:

```text
PaperSimulationInput
  + PaperFillOutcome
  + PaperStateTransitionResult
  + explicit append identity/context
          ↓
immutable PaperLedgerEntry
          ↓
pure append validation over a supplied immutable sequence
```

The independent Risk / Capital Authorization observation remains an input
provenance boundary owned outside P07. A ledger record cannot create or
upgrade that observation.

## 3. Scope

This specification defines:

- one immutable `PaperLedgerEntry`;
- identity linkage to one valid P07-T01 input;
- identity and digest linkage to one valid P07-T02 outcome;
- identity and digest linkage to one valid P07-T03 transition result;
- prior and resulting paper-state identity;
- explicit ledger stream and sequence identity;
- append-only ordering and predecessor-link semantics;
- deterministic duplicate and conflicting-duplicate handling;
- canonical representation and SHA-256 digest rules;
- immutable provenance and deterministic replay requirements;
- explicit timestamps and future-data-leakage checks;
- `UNKNOWN`, unavailable, failed, rejected, and invalid semantics;
- a pure in-memory append operation over supplied records; and
- the focused verification plan for a later implementation.

This specification does not define:

- a database, table, ORM model, migration, repository, or durable store;
- filesystem, object-storage, Redis, queue, cache, or external persistence;
- reconciliation against a venue, wallet, chain, provider, or external truth;
- cash, bank, wallet, settlement, tax, or realized-profit authority;
- order management, an order book, routing, retry, or execution permission;
- Risk Governor or Capital Authorization behavior;
- P06 decision logic, ranking, optimization, learning, or AI/LLM behavior;
- provider, network, RPC, DEX, Jupiter, Jito, wallet, signing, or broadcast
  behavior; or
- P07-T05+, P08, or P09 work.

## 4. Contract identity and version policy

The future implementation must define the following public contract identities:

| Identity | Required value | Meaning |
|---|---|---|
| `P07_T04_CONTRACT_VERSION` | `p07-t04-v1` | Wire contract for one ledger entry and append result |
| `P07_T04_LEDGER_MODEL_VERSION` | `p07-t04-ledger-v1` | Entry identity, linkage, and append model |
| `P07_T04_CANONICALIZATION_VERSION` | explicit versioned value | Canonical serialization policy used by the implementation |
| `P07_T04_APPEND_POLICY_VERSION` | explicit versioned value | Sequence, predecessor, duplicate, and conflict policy |

The exact canonicalization and append-policy version strings must be constants
in the approved implementation. They must not be silently defaulted or
changed during replay.

Changing field meaning, requiredness, identity material, ordering, duplicate
handling, canonicalization, digest inputs, or failure semantics requires a new
contract or model version and separate approval.

## 5. Inputs

The future append operation must consume only explicitly supplied values. The
minimum logical inputs are:

1. one immutable `PaperSimulationInput` from P07-T01;
2. one immutable, digest-verified `PaperFillOutcome` from P07-T02;
3. one immutable, digest-verified `PaperStateTransitionResult` from P07-T03;
4. one explicit ledger-stream identity;
5. one explicit positive sequence number within that stream;
6. one explicit predecessor entry digest, or `null` for the first entry; and
7. one explicit ledger reference time.

The future implementation must not reconstruct, replace, refresh, or fetch any
of these values.

### 5.1 P07-T01 input identity

The ledger must preserve and verify the following identity values from the
supplied `PaperSimulationInput`:

- `input_digest`;
- P06 decision-intent digest and context digest;
- P06 candidate, chain, token, action, posture, decision timestamp, and
  contract/evaluator/ruleset versions;
- authorization observation identity, status, digest, scope, and versions;
- execution observation ID, digest, observation time, availability time, source
  contract version, replay key, and context digests;
- simulation configuration ID, digest, contract version, simulation version,
  fill-model version, friction-model version, failure-policy version, and
  seed-policy version;
- initial paper-state ID, digest, version, portfolio scope, component state
  digests, as-of time, quality, and provenance; and
- replay identity, including replay ID, schema version, seed identity, parent
  replay ID, and replay scope.

T04 must verify that:

- the supplied `PaperSimulationInput` is internally valid;
- its `input_digest` equals its canonical digest;
- its `simulation_reference_time` is explicit and timezone-aware;
- the T02 outcome's `p07_t01_input_digest` equals the input digest;
- the outcome's configuration and execution-observation identities match the
  input exactly; and
- the T03 prior state is the state identified by the simulation input where
  that transition is the simulation described by the input.

No P06 or authorization field may be treated as ledger authority.

### 5.2 P07-T02 outcome identity

The ledger must consume one actual `PaperFillOutcome` object, not a
reconstructed mapping. It must verify at minimum:

- the outcome canonical representation and `outcome_digest`;
- T02 contract, fill-model, and friction-model versions;
- status, side, quantity units, requested/filled/remaining quantities, and
  quantity conservation;
- effective-price, liquidity, friction, and explicit unknown/unavailable
  representation;
- quote observation and fill timestamps;
- T01 input digest, configuration identity, replay identity, and execution
  observation identity; and
- the outcome's immutable nested friction evidence.

All valid T02 statuses remain recordable:

- `FILLED`;
- `PARTIALLY_FILLED`;
- `FAILED`;
- `REJECTED`;
- `UNAVAILABLE`; and
- `INVALID`.

Recording a non-success T02 outcome does not turn it into a success. T04
preserves its status and reason codes exactly after canonical normalization.

### 5.3 P07-T03 transition identity

The ledger must consume one actual `PaperStateTransitionResult` object, not a
reconstructed mapping. It must verify:

- the transition canonical representation and `transition_digest`;
- T03 contract version;
- transition status and stable reason codes;
- prior-state digest and identity;
- outcome identity and its exact T02 outcome digest;
- next-state identity when `next_state` is present;
- quantity, accounting, and exposure effect values;
- transition reference time; and
- transition provenance linking the prior state and outcome.

The transition status must agree with the outcome status:

| T02 outcome | Permitted T03 result |
|---|---|
| `FILLED`, `PARTIALLY_FILLED` with a positive fill | `APPLIED` |
| `FAILED` | `NO_CHANGE` |
| `REJECTED` | `NO_CHANGE` or `REJECTED` |
| `UNAVAILABLE` | `UNAVAILABLE` |
| `INVALID` | `INVALID` |

Any contradiction is `INVALID` and must not append a record.

For an `APPLIED` transition, `next_state` is required and becomes the
resulting-state identity. For `NO_CHANGE`, the resulting-state identity is the
prior-state identity when T03 returns the prior state as its unchanged state.
For `REJECTED`, `UNAVAILABLE`, and `INVALID`, a missing `next_state` is
expected; the resulting-state identity is `null`. T04 must preserve the
non-success result rather than inventing a state.

### 5.4 Explicit append identity and context

The caller must supply:

| Input | Requirement |
|---|---|
| `ledger_stream_identity` | Canonical bounded identity for one logical paper-ledger stream |
| `sequence_number` | Positive canonical integer; supplied, never generated |
| `previous_entry_digest` | Prior entry digest, or `null` for sequence `1` |
| `ledger_reference_time` | Explicit UTC timestamp used as the ledger as-of boundary |

The stream identity must not be a provider, wallet, venue, chain, or live
transaction identity. It identifies only a logical simulation record stream.

The implementation must not obtain sequence numbers, predecessor links, or
reference timestamps from mutable process state or the system clock.

## 6. Ledger entry contract

The future immutable value object is named `PaperLedgerEntry`. Its canonical
top-level fields are:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `contract_version` | canonical text | yes | Must be `p07-t04-v1` |
| `ledger_model_version` | canonical text | yes | Must be `p07-t04-ledger-v1` |
| `ledger_stream_identity` | bounded canonical mapping | yes | Logical stream identity |
| `sequence_number` | positive canonical integer | yes | Explicit position in the stream |
| `previous_entry_digest` | lowercase SHA-256 text or `null` | yes | Predecessor link |
| `entry_id` | lowercase SHA-256 text | derived | Deterministic event/stream identity |
| `event_identity_digest` | lowercase SHA-256 text | derived | Identity of the linked simulation event |
| `simulation_identity` | bounded identity mapping | yes | T01, P06, authorization, configuration, observation, and replay linkage |
| `outcome_identity` | bounded identity mapping | yes | T02 outcome identity and status |
| `transition_identity` | bounded identity mapping | yes | T03 transition identity and status |
| `prior_state_identity` | bounded identity mapping | yes | Prior T03 paper-state identity |
| `resulting_state_identity` | bounded identity mapping or `null` | yes | Resulting T03 state, when one exists |
| `timestamps` | bounded timestamp mapping | yes | Explicit simulation, observation, fill, transition, and ledger times |
| `effects` | bounded canonical mapping | yes | T03 quantity, accounting, and exposure effect identities/values |
| `reason_codes` | sorted tuple of canonical text | yes | Stable linked outcome/transition reasons |
| `provenance` | bounded canonical mapping | yes | Source identities, versions, and derivation context |
| `entry_digest` | lowercase SHA-256 text | derived | Digest of all other canonical entry fields |

The serialized entry must contain no fields outside this specification.
Unknown fields are rejected rather than ignored. Derived digests cannot
override their canonical source fields.

### 6.1 Simulation identity

`simulation_identity` must include, at minimum:

- `p07_t01_input_digest`;
- P06 `decision_intent_digest` and `context_digest`;
- P06 contract, evaluator, and ruleset versions;
- authorization observation ID and digest, including status and versions;
- execution observation ID and digest;
- execution observation observation/availability timestamps;
- simulation configuration ID and digest;
- simulation, fill, friction, and failure-policy versions;
- replay ID and replay schema version; and
- the explicit simulation reference time.

This is identity/provenance only. It is not an executable instruction.

### 6.2 Outcome identity

`outcome_identity` must include:

- `outcome_digest`;
- T02 contract, fill-model, and friction-model versions;
- outcome status and reason codes;
- side;
- requested, filled, and remaining quantities;
- quantity unit, price unit, and fee unit;
- effective-price identity where present; and
- execution observation identity and digest.

T04 must not reinterpret T02 friction fields or recalculate T02 effective
price, quantity, or status.

### 6.3 Transition and state identity

`transition_identity` must include:

- `transition_digest`;
- T03 contract version;
- transition status;
- transition reference time;
- stable reason codes; and
- the T03 outcome identity digest.

`prior_state_identity` must include:

- state ID;
- state version;
- state digest;
- portfolio scope;
- state quality; and
- state as-of time.

`resulting_state_identity` must use the same fields when T03 supplies a
resulting state and must be `null` when T03 has no resulting state. T04 must
not create an initial state, clone a missing state, or infer a resulting state
from quantities.

### 6.4 Effects

`effects` preserves the T03 effects by canonical value and identity:

- quantity effect;
- accounting effect;
- exposure effect;
- the applied versus attempted nature of the effect; and
- the T03 rounding policy/version.

T04 does not calculate, alter, or reinterpret these effects. The entry is a
record of the T03 result, not a second accounting engine.

## 7. Ledger entry identity

The identity of a ledger event must be deterministic and collision-resistant.
No local counter, random value, clock value, object address, or process order
may participate.

### 7.1 Event identity

`event_identity_digest` is the SHA-256 digest of the canonical mapping:

```text
{
  "ledger_model_version": ...,
  "p07_t01_input_digest": ...,
  "replay_id": ...,
  "outcome_digest": ...,
  "transition_digest": ...,
  "prior_state_digest": ...,
  "resulting_state_digest": null or ...,
  "transition_reference_time": ...,
  "ledger_reference_time": ...
}
```

The implementation must use the exact canonical field names and values from
the approved contract. The displayed mapping is the required identity
material, not a permission to add hidden fields.

### 7.2 Entry identity

`entry_id` is the SHA-256 digest of:

```text
{
  "ledger_stream_identity": ...,
  "sequence_number": ...,
  "previous_entry_digest": null or ...,
  "event_identity_digest": ...
}
```

The entry ID identifies one event at one explicit position in one logical
stream. Replaying identical inputs with identical stream and append context
must reproduce the same entry ID.

### 7.3 Entry digest

`entry_digest` is the SHA-256 digest of the complete canonical entry excluding
`entry_digest` itself. It covers the entry ID, every source identity,
timestamp, effect, reason, provenance, version, sequence, and predecessor
field.

An implementation must compute and verify supplied digests after
canonicalization. A caller-supplied mismatch is invalid.

## 8. Append-only semantics

The future implementation must expose a pure operation conceptually equivalent
to:

```text
append_paper_ledger_entry(
    existing_entries: immutable ordered sequence[PaperLedgerEntry],
    candidate: PaperLedgerEntry,
) -> PaperLedgerAppendResult
```

The operation:

- accepts only an explicitly supplied immutable sequence;
- never mutates that sequence or any entry;
- returns a new immutable sequence only for `APPENDED`;
- returns the original canonical sequence for `DUPLICATE`;
- returns no appended candidate for `CONFLICT`, `REJECTED`, `UNAVAILABLE`, or
  `INVALID`;
- performs no filesystem, database, queue, cache, network, provider, or
  external-service operation; and
- does not retain hidden state between calls.

`PaperLedgerAppendResult` must contain a canonical status, the candidate entry
identity, the resulting immutable sequence or `null`, and stable reason codes.
Its status values are:

| Status | Meaning |
|---|---|
| `APPENDED` | Candidate passed all checks and is returned as the final tuple member |
| `DUPLICATE` | Exact event is already present; no second record is added |
| `CONFLICT` | Same event/sequence/stream claim conflicts with existing canonical material |
| `REJECTED` | Candidate violates an append precondition or temporal boundary |
| `UNAVAILABLE` | Required identity/provenance is unknown or unavailable |
| `INVALID` | Candidate or existing sequence is malformed, tampered, or contradictory |

`APPENDED` and `DUPLICATE` describe record handling only. Neither status
asserts that the linked hypothetical fill succeeded.

## 9. Ordering and predecessor rules

For every valid logical stream:

1. The first sequence number is `1` and its predecessor digest is `null`.
2. Each later sequence number is exactly the previous maximum plus `1`.
3. Each later `previous_entry_digest` equals the prior entry's `entry_digest`.
4. Entries are ordered strictly by `sequence_number`.
5. Sequence numbers are not generated, repaired, compacted, or renumbered.
6. Entries cannot be edited, deleted, inserted before an existing entry, or
   replaced in place.
7. Different streams may have independent sequence numbers.
8. Stream identity, contract version, and append-policy version must remain
   consistent for one supplied sequence.

The implementation must reject gaps, out-of-order entries, duplicate sequence
numbers, predecessor mismatches, mixed streams, and malformed existing
sequences. It must not silently sort or repair semantic record order.

The tuple is a logical append context only. It is not durable persistence and
does not establish a database transaction or cross-process lock.

## 10. Duplicate and conflict handling

Duplicate handling must be deterministic and fail closed:

### 10.1 Exact duplicate

If an existing entry has the same `entry_id`, `event_identity_digest`,
`entry_digest`, stream identity, sequence number, predecessor digest, and
canonical fields, the append result is `DUPLICATE`. The sequence remains
unchanged. A duplicate is idempotent, not a new fill and not a successful
transition.

### 10.2 Same event at a different location

If an existing entry has the same `event_identity_digest` but a different
stream, sequence number, predecessor, or canonical entry material, the result
is `CONFLICT`. T04 must not create a second position for the same event or
silently move it.

### 10.3 Same location with different event

If a candidate claims an occupied stream/sequence location but has a different
event identity or digest, the result is `CONFLICT`.

### 10.4 Digest collision or tampering

If a supplied digest does not match canonical source fields, or if an existing
entry cannot be verified, the result is `INVALID`. No candidate is appended.

No duplicate or conflict path may be upgraded to `APPENDED`.

## 11. Timestamp and future-data rules

All timestamps are explicit input data. T04 must never read the wall clock.

The entry must preserve, when present:

- P06 decision time;
- P07-T01 simulation reference time;
- execution observation time;
- execution availability time;
- T02 quote observation time;
- T02 fill/simulation time;
- T03 transition reference time; and
- T04 ledger reference time.

The following must hold:

- all timestamps are timezone-aware and canonicalized to UTC;
- execution observation time is no later than availability time;
- availability time is no later than the simulation reference time;
- quote and fill times are no later than the T03 and ledger reference times;
- the T03 transition reference time equals the explicit ledger reference time;
- the simulation reference time is no later than the ledger reference time;
- the prior state's as-of time is no later than the ledger reference time;
- a resulting state's as-of time, when present, is no later than the ledger
  reference time; and
- no timestamp is silently omitted when it is required by its source contract.

Future or internally contradictory timestamps produce `REJECTED` when the
candidate is otherwise well-formed but outside the reference boundary.
Malformed, non-canonical, or contradictory timestamp material produces
`INVALID`. A required unavailable timestamp produces `UNAVAILABLE`.

T04 does not invent a freshness window. Freshness and valuation validity remain
owned by T03 and its supplied contexts.

## 12. Failure, UNKNOWN, and non-success semantics

The ledger must fail closed. It must not convert an invalid or unknown source
into a valid record.

| Condition | Required result |
|---|---|
| Missing required identity or digest | `INVALID` or `UNAVAILABLE` according to whether the field is malformed or unavailable |
| T02/T03 digest mismatch | `INVALID` |
| Unsupported contract/model/version | `INVALID` |
| Contradictory duplicated identity | `INVALID` |
| Future timestamp | `REJECTED` |
| Stale or unavailable required source identity | `UNAVAILABLE` |
| Invalid existing append sequence | `INVALID` |
| Broken predecessor or sequence ordering | `CONFLICT` or `INVALID` according to whether the candidate conflicts or the sequence is malformed |
| T02 `FAILED` or `REJECTED` | Recordable outcome; no state-change claim |
| T02 `UNAVAILABLE` | Recordable explicit unavailable outcome; no state-change claim |
| T02 `INVALID` or T03 `INVALID` | Recordable only when the objects and digests are valid explicit non-success results; never an applied state |
| T03 `NO_CHANGE` | Recordable with prior state identity and no new resulting state |
| Unknown required provenance | `UNAVAILABLE`; never a zero or empty substitute |

An explicit non-success T02/T03 result may be recorded because the ledger is
an audit record of a hypothetical attempt. Recording it does not make the
attempt successful and does not grant permission to retry, cancel, settle, or
execute.

`UNKNOWN` must remain visible in status, reason codes, state quality,
valuation/exposure context, authorization observation, and provenance where
provided by T01/T02/T03. T04 must not replace it with `PASS`, zero, an empty
identity, or a fabricated state.

## 13. Provenance and replay

Every entry must preserve enough immutable identity to reproduce the record
without accessing external state:

- exact P06 decision-intent and context digests;
- exact P07-T01 input digest and replay identity;
- authorization observation ID, digest, status, and versions;
- execution observation ID, digest, timestamps, and source contract version;
- simulation configuration ID, digest, and model versions;
- exact T02 outcome digest, status, model versions, and reasons;
- exact T03 transition digest, status, and contract version;
- prior and resulting paper-state IDs, versions, and digests;
- ledger stream identity, sequence, predecessor, and append policy version;
- explicit simulation, observation, transition, and ledger timestamps; and
- canonical entry and event identity digests.

Given identical canonical source identities and identical append context, the
future implementation must produce identical:

- entry status;
- entry ID;
- event identity digest;
- entry digest;
- canonical representation;
- append result; and
- bounded reason codes.

Replay must not query current data, use a new clock value, use a new random
value, resolve a missing identity, or use process-global mutable state.

## 14. Canonicalization and immutability

Canonicalization follows the established P07 conventions:

- mappings use sorted string keys;
- tuples/sequences are ordered arrays;
- sets are forbidden;
- timestamps are timezone-aware UTC in one microsecond ISO-8601 form ending in
  `Z`;
- decimals are finite normalized decimal text with no exponent notation;
- enum values use explicit wire values;
- nullable values are represented as `null`, not omitted;
- text is non-empty, trimmed UTF-8;
- bounded mappings contain only canonical JSON-compatible values;
- unknown fields, non-string keys, floats, NaN, infinity, and opaque objects are
  rejected; and
- SHA-256 is computed over compact UTF-8 JSON with sorted keys and no extra
  whitespace.

`PaperLedgerEntry` and `PaperLedgerAppendResult` must be immutable. Nested
mappings and sequences must be protected from mutation through returned
representations. Existing entries supplied to an append operation must remain
unchanged, including when the result is `DUPLICATE`, `CONFLICT`, or a
non-success status.

The entry's canonical representation must expose every field required by this
specification, including `null` fields and all version values. It must not
include raw unbounded provider payloads or opaque objects.

## 15. Authority separation

P07-T04 MUST NOT:

- create, approve, renew, evaluate, or modify Risk / Capital Authorization;
- modify a P06 `DecisionIntent` or any P05/P06 contract;
- create an order, route, quote, retry, execution permission, or live request;
- change the status or meaning of a T02 outcome;
- recalculate or mutate a T03 paper position or exposure state;
- create a paper state that T03 did not provide;
- establish cash, wallet, bank, settlement, tax, or realized-profit authority;
- claim wallet, venue, provider, RPC, DEX, chain, or on-chain truth;
- perform reconciliation or resolve disagreement with external truth;
- invoke P08, P09, an LLM, an AI loop, ranking, optimization, or learning; or
- introduce hidden mutable state or process-global record storage.

A ledger entry is evidence of a hypothetical paper event and its supplied
state transition. It cannot authorize a later paper transition, a retry, a
live trade, capital movement, or strategy promotion.

## 16. Persistence boundary

This specification authorizes a logical record value and a pure append
operation over an explicitly supplied immutable sequence only.

It does not authorize:

- database tables or SQLAlchemy models;
- migrations or schema changes;
- repositories or durable record writers;
- files, object storage, or filesystem journals;
- Redis, queues, caches, or event buses;
- retention, compaction, archival, or deletion policies; or
- workflow, deployment, or production changes.

The returned immutable tuple is a testable value, not persistence. Durable
storage and retention require a separate governed specification.

## 17. Reconciliation boundary

P07-T04 does not implement reconciliation.

Future reconciliation may consume paper-ledger entries and compare their
identity-linked state with explicitly supplied replay expectations or another
governed observation boundary. T04 does not:

- fetch an external truth;
- identify a venue or wallet as authoritative;
- resolve a disagreement;
- rewrite or delete a conflicting ledger record;
- mark a paper record as settled; or
- authorize a dependent state transition after disagreement.

Missing, duplicated, delayed, unexpected, or contradictory material remains
visible to a future reconciliation boundary. T04 only preserves the record
identities and append invariants needed for that later work.

## 18. Exact proposed implementation files

The following files are proposed for a later, separately authorized
implementation. They are not created or authorized by this specification task:

| File | Proposed responsibility |
|---|---|
| `core/execution/paper_ledger.py` | Immutable `PaperLedgerEntry`, append result/status values, canonical identity/digest logic, and pure append validation |
| `tests/test_paper_ledger.py` | Focused ledger construction, identity, ordering, duplicate/conflict, provenance, fail-closed, and forbidden-behavior tests |

No implementation export change is proposed at this boundary. Adding exports
or modifying `core/execution/__init__.py` requires explicit inclusion in a
future implementation authorization.

No other source, test, documentation, dependency, migration, persistence,
workflow, provider, network, wallet, authorization, P08, or P09 file is
proposed.

## 19. Focused verification plan

The future focused suite must be run with:

```text
uv run pytest tests/test_paper_ledger.py -q
```

It must verify at minimum:

1. construction of a valid immutable ledger entry;
2. exact linkage to the P07-T01 input digest and replay identity;
3. exact linkage to P06 intent digest/provenance;
4. exact linkage to T02 outcome identity, digest, status, and model versions;
5. exact linkage to T03 transition identity, digest, status, and state digests;
6. resulting-state `null` semantics for non-applied T03 results;
7. deterministic event identity and entry identity;
8. deterministic complete-entry digest;
9. canonical representation stability across mapping order;
10. immutable nested provenance and unchanged source objects;
11. first-entry sequence and `null` predecessor rules;
12. valid contiguous append and predecessor linking;
13. append-only rejection of gaps, reordering, insertion, deletion, and edits;
14. exact duplicate idempotency with no second record;
15. conflicting duplicate and occupied-location rejection;
16. failed, rejected, unavailable, and invalid outcome recording semantics;
17. UNKNOWN and unavailable provenance preservation;
18. missing, tampered, contradictory, unsupported, and non-canonical input;
19. stale and future timestamp behavior;
20. transition/outcome/state identity mismatches;
21. unsupported T01/T02/T03/model versions;
22. no wall-clock dependence or random behavior;
23. no filesystem, database, persistence, queue, cache, provider, or network
    access;
24. no authorization, order, wallet, signing, broadcast, reconciliation,
    P08, or P09 behavior; and
25. identical canonical inputs and append context producing identical results.

Required regression commands after a future implementation is separately
authorized are:

```text
uv run pytest tests/test_paper_simulation_input.py \
  tests/test_paper_fill_outcome.py \
  tests/test_paper_position_exposure_state.py -q
uv run pytest -q
```

The focused and regression suites must not be weakened to hide a contract
failure. If a failure requires changing an unauthorized file, implementation
must stop and report the boundary violation.

## 20. Entry criteria

P07-T04 implementation may begin only after all of the following are
separately accepted:

- this specification passes architecture and contract audit;
- the record field-level contract is approved;
- event, entry, stream, sequence, and predecessor identity semantics are
  approved;
- append-only and duplicate/conflict semantics are approved;
- T01/T02/T03 identity and digest linkage is approved;
- timestamp and future-data rules are approved;
- UNKNOWN, unavailable, failed, rejected, and invalid semantics are approved;
- canonicalization and immutability rules are approved;
- the persistence and reconciliation boundaries are approved;
- the focused and regression test commands are approved; and
- an explicit implementation authorization names the exact baseline, source
  files, test files, focused command, and regression commands.

This document does not authorize implementation.

## 21. Exit criteria

The P07-T04 specification task is complete when:

- this document has been reviewed against P07, T01, T02, and T03;
- ledger authority is clearly separated from simulation, risk, and live
  execution authority;
- the exact proposed implementation files and future tests are named;
- persistence and reconciliation remain outside this boundary; and
- only this specification file is created or modified by the specification
  task.

The future P07-T04 implementation task is complete only when:

- the approved implementation files are the only changed files;
- focused ledger tests pass;
- T01/T02/T03 regression tests pass;
- the full suite passes;
- deterministic identity, canonicalization, replay, provenance, and
  immutability are verified;
- append-only, duplicate, conflict, UNKNOWN, and fail-closed behavior is
  verified;
- no persistence, reconciliation, provider, authorization, wallet, live
  execution, P08, or P09 behavior exists; and
- the specification, project state, and verification evidence are synchronized
  under a separately governed completion step.

## 22. Audit record

This proposed specification has been internally checked against:

- the P07 master boundary: the ledger is a simulation-only record and does not
  create authority, persistence, or live execution;
- P07-T01: input, P06, authorization, execution-observation, configuration,
  initial-state, reference-time, replay, UNKNOWN, provenance, immutability,
  and digest identities are consumed by reference and verification;
- P07-T02: outcomes are consumed as immutable identity-verified values, all
  explicit statuses remain observable, and T04 does not reinterpret friction,
  quantity, or fill behavior;
- P07-T03: transition and state identities are consumed by digest, T04 does
  not recompute position/exposure effects, and non-applied results do not
  receive fabricated states;
- the P06 boundary: decision intent is provenance only and is not modified or
  re-evaluated;
- the Risk / Capital Authorization boundary: authorization is an independent
  observation and is never created, renewed, or upgraded;
- the future reconciliation boundary: T04 preserves identities but does not
  compare to external truth or resolve disagreement;
- the P08 boundary: no learning, performance promotion, or strategy feedback
  is implemented; and
- the P09 boundary: no provider, wallet, signing, RPC, DEX, broadcast, or live
  execution capability is introduced.

Specific accidental-authority checks:

- `APPENDED` is explicitly record-handling status, not fill success.
- A duplicate is idempotently recognized, not retried or re-executed.
- A conflicting duplicate is visible and not overwritten.
- Non-success outcomes may be recorded without becoming successful.
- The returned tuple is an in-memory value, not persistence.
- A ledger record cannot authorize a state transition or claim external truth.

Audit result: **PROPOSED / REVIEW REQUIRED**.

## 23. Governance conclusion

P07-T04 is the next separately governed paper-ledger boundary after P07-T03.
This document defines the proposed logical contract only.

**This document does not authorize implementation.**

Implementation requires a separate explicit authorization containing:

- the exact approved baseline commit;
- the exact implementation files;
- the exact test files;
- the exact focused test command;
- the exact regression command(s); and
- explicit permission to modify those files.

No P07-T04 implementation, test, dependency, persistence, reconciliation,
provider, wallet, RPC, DEX, signing, broadcast, P08, P09, or live-execution
work is authorized by this document.