# P08 — Authority B Implementation-Readiness Specification

**Status:** COMPLETE / READY FOR REVIEW — IMPLEMENTATION NOT AUTHORIZED
**Phase:** P08 — Outcome Learning
**Authority:** Authority B — Correction / Supersession Lineage Facts
**Readiness scope:** Bounded future implementation preparation only

## 1. Purpose and authorization boundary

This document translates the closed Authority B semantic specification into a
reviewable implementation-readiness contract. It does not create runtime
behavior, source code, tests, persistence, migrations, dependencies, external
access, or an implementation authorization.

The governing semantic sources are:

- `docs/P08-AUTHORITY-B-SPECIFICATION-AUDIT.md`;
- `docs/P08-AUTHORITY-B-FORMAL-CLOSURE-AUDIT.md`;
- `docs/P08-AUTHORITY-A-SPECIFICATION-AUDIT.md`;
- `docs/P08-T07-SPECIFICATION.md`; and
- `docs/P08-T07-CANONICAL-RESULT-AUTHORITY-EXTENSION-SPECIFICATION.md`.

The readiness contract preserves these current governance facts:

```text
Authority A specification = COMPLETE / CLOSED / AUDITED PASS
Authority A implementation = NOT AUTHORIZED
Authority B specification = COMPLETE / CLOSED / AUDITED PASS
Authority B implementation = NOT AUTHORIZED
P08-T07 = CLOSED; redesign NOT AUTHORIZED
P09 = NOT AUTHORIZED
```

No statement in this document may be interpreted as permission to implement
Authority B. A separate explicit implementation authorization is required
after review of this document.

## 2. Exact implementation scope

The future Authority B implementation is a pure, provider-neutral,
lineage-only boundary over explicitly supplied immutable values.

It may:

1. validate an explicitly supplied immutable `LineageFact`;
2. canonicalize a valid fact, edge, identity projection, and comparison
   snapshot according to the locked serialization contract;
3. derive and verify `LineageFactIdentity`, `LineageEdgeIdentity`,
   `edge_digest`, `snapshot_identity`, and `snapshot_digest`;
4. compare a candidate fact against an explicitly supplied immutable
   `Authoritative Lineage Fact Set Snapshot`;
5. build and validate an explicitly supplied lifecycle-scoped lineage graph;
6. detect duplicate, conflict, branch, cycle, self-reference, orphan,
   missing-endpoint, cross-lifecycle, contradiction, provenance, determinism,
   and digest failures;
7. identify a deterministic terminal candidate or unresolved graph state under
   the approved rules; and
8. produce only the exact lineage projection needed for the existing T07
   `correction_lineage` or `supersession_lineage` destination.

It must not:

- infer, repair, substitute, merge, or invent lineage;
- infer any missing endpoint, lifecycle, authority, provenance, or digest;
- resolve a conflict by timestamp, insertion order, result magnitude, caller
  preference, or last-write-wins;
- mutate a predecessor, successor, fact, edge, identity, or snapshot;
- choose between conflicting branches;
- assert T07's canonical head as an economic result;
- recalculate G2, G3, G4, or any T07 economic field; or
- introduce any authority outside the lineage relationship.

### 2.1 Canonical-head boundary

The implementation may compute a deterministic structural terminal candidate
from a complete, valid, explicitly supplied graph as an intermediate lineage
validation result. This computation is not an independent Authority B
canonical-head authority.

T07 remains the final validator, graph-conflict detector, and canonical-head
authority under its existing contract. If the graph has zero or multiple valid
terminal candidates, or any unresolved lineage condition, the Authority B
result is fail closed and no candidate is selected.

## 3. Exact allowed future implementation files

No files in this section are created by the current readiness task. If a
separate implementation authorization is granted, the minimum proposed file
set is exactly:

| Future path | Responsibility |
|---|---|
| `core/learning/authority_b_lineage.py` | Pure Authority B domain types and validation boundary: immutable input/output records, canonical serialization, identity and digest derivation, explicit snapshot comparison, lineage graph validation, deterministic terminal-candidate calculation, failure precedence, and the exact T07 lineage projection. |
| `tests/test_authority_b_lineage.py` | Targeted tests for the Authority B contract, including deterministic replay, canonical bytes, duplicate context, graph failures, T07 mapping completeness, immutability, and prohibited dependencies. |

The future module must remain independent from:

- API, HTTP, CLI, worker, queue, scheduler, and service layers;
- database, ORM, repository, migration, cache, filesystem, and persistence
  layers;
- wallet, custody, signer, provider, RPC, DEX, exchange, network, and
  external API layers;
- T07 implementation internals; and
- P09 or any execution chain.

No existing T07 source file, T07 test file, Authority A file, package
manifest, lockfile, migration, or runtime configuration may be changed by the
readiness work. Any later adapter wiring or integration change requires its
own explicit review and authorization.

## 4. Input contract

All inputs must be explicit, immutable, complete for the requested operation,
and validated before any derived output is accepted.

### 4.1 Candidate `LineageFact`

The candidate fact contains exactly the required non-null fields already locked
by Authority B:

| Field | Required meaning |
|---|---|
| `contract_version` | Fixed `p08-authority-b-lineage-v1` |
| `lineage_policy_version` | Fixed `p08-authority-b-policy-v1` |
| `lifecycle_identity` | Existing Authority A lifecycle identity |
| `predecessor_result_identity` | Exactly one immutable predecessor result identity |
| `successor_result_identity` | Exactly one immutable successor result identity |
| `lineage_type` | Exactly `correction` or `supersession` |
| `authority_identity` | Identity of the authority asserting the fact |
| `provenance` | Exactly one complete link for each required upstream stage in fixed order |
| `lineage_fact_identity` | Derived SHA-256 identity over the fixed identity projection |

The fact has no optional semantic fields, nullable semantic fields, numeric
fields, timestamp fields, effective-time fields, generated UUIDs, free-form
reason fields, amounts, provider fields, or network fields.

The provenance stage sequence is fixed to:

```text
p06_decision_intent
p07_simulation_input
p07_simulation_result
p07_history
p08_t01_observation
p08_t02_dataset
p08_t03_interpretation
p08_t04_evaluation
p08_t05_snapshot
p08_t06_readiness
authority_a_identity
```

Each stage occurs exactly once and each link contains exactly:

```text
stage
record_identity
record_digest
authority_identity
```

### 4.2 Explicit authoritative comparison snapshot

Duplicate comparison requires an explicitly supplied immutable
`Authoritative Lineage Fact Set Snapshot` with exactly:

- `snapshot_contract_version`, fixed to
  `p08-authority-b-lineage-snapshot-v1`;
- one `lifecycle_identity`;
- the complete canonical member set for that lifecycle;
- each member's `lineage_fact_identity` and complete canonical bytes;
- `snapshot_identity`; and
- `snapshot_digest`.

Snapshot members are canonically ordered by ASCII
`lineage_fact_identity`. The snapshot must be rejected if it has missing
members, duplicate member identities, mixed lifecycle scope, non-canonical
member bytes, identity/byte/digest disagreement, or non-canonical ordering.

The implementation must never discover comparison members from a database,
registry, cache, filesystem, provider, network, process memory, insertion
order, or hidden configuration.

### 4.3 Explicit graph input

Graph validation receives an immutable value containing:

- one target `lifecycle_identity`;
- the complete explicitly supplied immutable result-identity set for that
  lifecycle;
- the complete explicitly supplied valid or candidate lineage-fact set;
- the authoritative comparison snapshot; and
- the contract/policy versions required by each member.

The result-identity set is reference context only. Authority B does not create,
reconstruct, validate economic meaning for, or mutate the referenced T07
results. A missing, ambiguous, or cross-lifecycle endpoint fails closed.

### 4.4 Prohibited ambient inputs

No result may depend on:

- wall-clock or process time;
- local timezone;
- randomness;
- database or filesystem state;
- insertion or retrieval order;
- provider, RPC, network, wallet, or external API state;
- environment-specific hidden configuration;
- process identity;
- memory address; or
- caller preference.

## 5. Deterministic canonicalization and identity

The future implementation must reproduce the Authority B serialization profile
exactly for every fact, edge, identity projection, and snapshot:

1. canonical UTF-8 JSON without a byte-order mark;
2. Unicode NFC normalization before JSON escaping;
3. no NFKC, NFD, case folding, trimming, locale transformation, or other
   normalization;
4. unpaired surrogate rejection;
5. `U+0022` serialized only as `\"`;
6. `U+005C` serialized only as `\\`;
7. solidus `/` never escaped;
8. named short escapes only for `\b`, `\t`, `\n`, `\f`, and `\r`;
9. all other controls represented as lowercase `\u00xx`;
10. non-ASCII Unicode scalar values emitted directly as UTF-8;
11. object keys sorted by Unicode code-point sequence;
12. arrays never implicitly sorted;
13. only `,` and `:` separators, with no insignificant whitespace;
14. lowercase `true`, `false`, and `null`;
15. no explicit or implicit `null` in Authority B semantic objects;
16. no numeric JSON tokens in Authority B objects; and
17. exact canonical UTF-8 bytes used as digest input.

### 5.1 Identity projections

Both `LineageFactIdentity` and `LineageEdgeIdentity` use the exact six-element
canonical JSON array:

```text
[
  contract_version,
  lineage_policy_version,
  lifecycle_identity,
  predecessor_result_identity,
  successor_result_identity,
  lineage_type
]
```

The domain-separated digest rules are:

```text
LineageFactIdentity =
SHA-256(UTF-8("p08-authority-b:fact:v1\0" + canonical_identity_projection))

LineageEdgeIdentity =
SHA-256(UTF-8("p08-authority-b:edge:v1\0" + canonical_identity_projection))
```

`edge_digest` is SHA-256 over the complete canonical `LineageEdge`
representation with only `edge_digest` omitted. A digest never participates in
the identity projection it protects.

Snapshot identity and digest use the locked snapshot rules. Neither snapshot
value participates in fact or edge identity:

```text
Identity(F, S1) == Identity(F, S2) == Identity(F)
```

## 6. Duplicate and conflict behavior

The implementation must compute the candidate identity before consulting the
snapshot, then compare it only against the explicit snapshot:

| Condition | Required result |
|---|---|
| No matching identity | Candidate is not a duplicate and may continue validation |
| One byte-identical complete matching fact | `EXACT_DUPLICATE`; idempotently accepted and existing projection reused |
| Same identity with any canonical-byte difference | `CONFLICTING_DUPLICATE`; fail closed |
| More than one matching member | `DETERMINISM_FAILURE`; fail closed without selecting a member |
| Identity/bytes/digest disagreement | `DIGEST_FAILURE` or `DETERMINISM_FAILURE` according to first-applicable precedence |
| Same fact against another valid snapshot | Same fact/edge identities and canonical bytes; only contextual status may differ |

No duplicate may be accepted as a new authoritative fact. No conflict may be
resolved through last-write-wins, timestamp, insertion order, source
preference, or caller preference.

## 7. Graph validation and canonical-head behavior

### 7.1 Valid graph

A graph is valid only when:

- every edge has exactly one predecessor and one successor;
- all endpoints exist in the explicit result-identity set;
- all endpoints share the target lifecycle;
- every fact and edge is canonical, immutable, provenance-complete, and
  digest-valid;
- each predecessor has at most one direct authoritative successor;
- no self-reference exists;
- no cycle exists;
- no contradictory facts exist for the same edge; and
- exactly one structurally valid terminal candidate exists when canonical
  selection is requested.

Multi-hop chains are valid, including:

```text
R1 → R2 → R3
```

Correction and supersession may be mixed across successive edges when each edge
is independently valid. Correction and supersession have no precedence over
one another.

### 7.2 Fail-closed graph cases

The implementation must fail closed for:

- missing predecessor;
- missing successor;
- orphan or unresolved endpoint;
- cross-lifecycle reference;
- self-reference;
- cycle;
- multiple direct successors from one predecessor;
- multiple direct predecessors converging on one successor;
- contradictory facts for the same edge;
- invalid authority or provenance;
- invalid canonical bytes;
- digest mismatch;
- duplicate or conflicting duplicate;
- ambiguous terminal candidates; and
- any unsupported merge/convergence.

Merge/convergence is always:

```text
MERGE / CONVERGENCE UNSUPPORTED — FAIL CLOSED
```

The implementation must not repair or reinterpret any of these cases.

### 7.3 Deterministic failure precedence

When multiple failures apply, the first applicable category in this exact order
is the sole Authority B failure:

1. `MALFORMED_FACT`
2. `INVALID_IDENTITY`
3. `INVALID_LIFECYCLE`
4. `MISSING_ENDPOINT`
5. `CROSS_LIFECYCLE_REFERENCE`
6. `CONFLICTING_DUPLICATE`
7. `LINEAGE_SELF_REFERENCE`
8. `LINEAGE_CYCLE`
9. `MERGE_UNSUPPORTED`
10. `LINEAGE_BRANCH_CONFLICT`
11. `CONTRADICTORY_LINEAGE`
12. `PROVENANCE_FAILURE`
13. `DETERMINISM_FAILURE`
14. `DIGEST_FAILURE`

This order is independent of collection order, input order, timestamps, and
runtime behavior.

### 7.4 T07 canonical-head result

For one lifecycle:

- no declared successor makes a result a terminal candidate;
- a missing successor fails closed;
- an invalid edge fails closed;
- more than one terminal candidate fails closed;
- any branch fails closed;
- any cycle fails closed; and
- exactly one valid terminal candidate may be returned as a structural
  candidate for T07 validation.

Authority B must not convert this candidate into a valid economic result or
override T07's final canonical-head decision.

## 8. Exact T07 adapter boundary

For one valid fact, the implementation produces one canonical `LineageEdge`
projection into the existing T07 field selected by `lineage_type`:

| Authority B relation | Exact T07 destination |
|---|---|
| `correction` | `EconomicOutcomeInterpretationInput.correction_lineage` and corresponding result field |
| `supersession` | `EconomicOutcomeInterpretationInput.supersession_lineage` and corresponding result field |

The adapter must preserve without semantic transformation:

- `contract_version`;
- `lineage_policy_version`;
- `lifecycle_identity`;
- `predecessor_result_identity`;
- `successor_result_identity`;
- `lineage_type`;
- `lineage_fact_identity`;
- `lineage_edge_identity`;
- `authority_identity`;
- ordered `provenance`; and
- `edge_digest`.

The adapter must not populate or redefine T07's own:

- `contract_version`;
- `evaluator_version`;
- `status`;
- `failure_reason`;
- G2/G3/G4 fields;
- `result_digest`; or
- `classification_digest`.

An invalid Authority B projection is semantically absent under the existing T07
output contract and must never be accepted as a valid lineage member.

The exhaustive mapping to existing T07 failure reasons is:

| Authority B result | T07 behavior |
|---|---|
| `MALFORMED_FACT`, `INVALID_IDENTITY`, `MISSING_ENDPOINT` | `INVALID_INPUT` / `MISSING_REQUIRED_INPUT` |
| `INVALID_LIFECYCLE`, `CROSS_LIFECYCLE_REFERENCE`, `CONFLICTING_DUPLICATE`, `LINEAGE_SELF_REFERENCE`, `LINEAGE_CYCLE`, `LINEAGE_BRANCH_CONFLICT`, `CONTRADICTORY_LINEAGE` | `INVALID_INPUT` / `CONFLICTING_INPUT` |
| `MERGE_UNSUPPORTED`, `DETERMINISM_FAILURE` | `INVALID_INPUT` / `UNRESOLVED_RESIDUAL` |
| `PROVENANCE_FAILURE` | `INVALID_INPUT` / `PROVENANCE_LINKAGE_FAILURE` |
| `DIGEST_FAILURE` | `INVALID_INPUT` / `DIGEST_FAILURE` |
| `EXACT_DUPLICATE` | Idempotent success; existing projection reused exactly once |

No new T07 status, failure enum, economic result, G2/G3/G4 meaning, or
canonical-head rule may be introduced.

## 9. Later authorization test plan

No tests are created by this document. After separate implementation
authorization, `tests/test_authority_b_lineage.py` must cover at minimum:

### 9.1 Canonicalization and replay

- identical semantic inputs produce byte-identical canonical JSON;
- NFC normalization and invalid surrogate rejection;
- quote, backslash, control, solidus, and non-ASCII escaping;
- sorted keys and fixed array order;
- absent versus explicit `null`;
- rejection of numeric tokens;
- exact SHA-256 identity and digest inputs;
- digest self-reference rejection;
- replay independent of input/collection order; and
- replay independent of wall clock, timezone, randomness, and ambient state.

### 9.2 Duplicate comparison

- explicit snapshot required;
- snapshot canonical member ordering;
- snapshot identity/digest verification;
- exact duplicate idempotent reuse;
- conflicting duplicate fail closed;
- duplicate identity independent of snapshot;
- multiple matching members;
- identity/bytes/digest disagreement; and
- no last-write-wins.

### 9.3 Graph adversarial cases

- valid single edge;
- valid multi-hop correction chain;
- valid mixed correction/supersession chain;
- direct branching;
- unsupported merge/convergence;
- cycle;
- self-reference;
- orphan and missing predecessor;
- missing successor;
- cross-lifecycle endpoint;
- contradictory facts;
- invalid authority/provenance;
- invalid digest;
- ambiguous terminal candidates; and
- deterministic failure precedence when multiple failures coexist.

### 9.4 T07 mapping completeness

- correction destination;
- supersession destination;
- every field preserved exactly;
- invalid projection omission;
- every Authority B failure mapping;
- `EXACT_DUPLICATE` projection reuse;
- no T07 field redefinition; and
- T07 remains final validator and canonical-head authority.

### 9.5 Immutability and dependency boundary

- predecessor and successor values remain unchanged;
- facts, edges, identities, and snapshots are immutable;
- no database/filesystem/provider/network access;
- no wallet, signer, execution, or persistence imports;
- no clock/randomness dependencies;
- no G2/G3/G4 calculation or classification;
- no P09 behavior; and
- no dependency added without separate authorization.

## 10. Explicit prohibitions

Authority B implementation readiness does not authorize:

- G2 realization or settlement;
- G3 accounting, P&L, ROI, or economic calculation;
- G4 `WIN`, `LOSS`, or `BREAKEVEN` classification;
- valuation or performance metrics;
- wallet or custody;
- private keys, signing, broadcast, or execution;
- provider, RPC, DEX, exchange, network, or external API access;
- database, persistence, migrations, caches, queues, or filesystem authority;
- Risk Governor or capital authorization;
- model training, AI/ML, strategy updates, or learning;
- T07 redesign or modification;
- Authority A modification;
- P08-T08; or
- P09 behavior.

No evidence, lineage fact, canonical terminal candidate, or T07 projection
grants any prohibited authority implicitly.

## 11. Authorization gate

A separate Authority B implementation authorization may be considered only
after all of the following are explicitly reviewed and recorded:

1. this readiness specification is approved without unresolved semantic
   contradictions;
2. the proposed implementation is limited to the two paths in Section 3;
3. all input/output fields, immutability rules, canonical bytes, identity
   projections, digest inputs, duplicate semantics, and failure precedence are
   implemented exactly;
4. the T07 adapter is verified against the existing closed T07 contract without
   changing T07;
5. the test plan is implemented in the proposed test file, including
   adversarial and prohibited-dependency coverage;
6. static inspection confirms no runtime/API/database/provider/wallet/P09
   dependency;
7. targeted tests and required repository checks pass; and
8. the authorization record explicitly preserves:

```text
Authority B implementation = AUTHORIZED ONLY BY SEPARATE APPROVAL
P09 = NOT AUTHORIZED
```

Until that separate approval exists, the only permitted changes are
specification or governance documents explicitly requested by the user.

## 12. Current task deliverable

This task creates only this document and the corresponding
`PROJECT_STATE.md` readiness status:

```text
Authority B implementation-readiness specification is COMPLETE / READY FOR REVIEW; implementation remains NOT AUTHORIZED.
```

The future source and test paths listed in Section 3 were proposed only. They
were not created, implemented, or tested by this task.