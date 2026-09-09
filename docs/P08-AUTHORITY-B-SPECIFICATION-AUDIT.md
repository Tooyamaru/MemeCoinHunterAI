# P08 — Authority B Specification and Audit

**Status:** FINAL FORMAL CLOSURE AUDIT COMPLETE — SPECIFICATION-LEVEL BLOCKED — IMPLEMENTATION NOT AUTHORIZED
**Phase:** P08 — Outcome Learning
**Authority:** Authority B — Correction / Supersession Lineage Facts
**Scope:** Immutable lineage-fact authority for canonical T07 result lineage

## 1. Audit Basis and Status Vocabulary

This document is a specification and audit boundary only. It does not create
runtime behavior, source code, tests, persistence, external access, wallet
behavior, provider behavior, or a new P08 task.

The audit is based on:

- `REPLIT_RULES.md`;
- `PROJECT_STATE.md`;
- `docs/P08-CANONICAL-ECONOMIC-SUBJECT-LIFECYCLE-IDENTITY-AUTHORITY-SPECIFICATION.md`;
- `docs/P08-T07-CANONICAL-RESULT-AUTHORITY-EXTENSION-SPECIFICATION.md`;
- `docs/P08-T07-SPECIFICATION.md`;
- `docs/P08-T04-SPECIFICATION.md`;
- `docs/P08-T05-SPECIFICATION.md`;
- `docs/P08-T06-SPECIFICATION.md`;
- `docs/ARCHITECTURE.md`;
- `docs/RISK_ENGINE.md`;
- `docs/EXECUTION_ENGINE.md`;
- `docs/LEARNING_ENGINE.md`; and
- `docs/SECURITY.md`.

The terms below are used normatively:

| Status | Meaning |
|---|---|
| `RESOLVED` | The semantic boundary is established by repository evidence. |
| `UNRESOLVED` | A required semantic, field, serialization, or adapter decision is not locked. |
| `BLOCKED` | The dependency cannot be used or advanced without an upstream decision. |
| `PROHIBITED` | The behavior is outside Authority B and must not be inferred. |
| `NOT APPLICABLE` | The concern does not belong to Authority B. |

## 2. Authority B Status

### 2.1 Determination

Authority B is a bounded semantic authority. The final formal closure audit
identified remaining specification blockers. No implementation authorization is
implied.

Authority B owns:

- authoritative correction facts;
- authoritative supersession facts;
- predecessor/successor relationships;
- lineage-fact identity;
- lineage evidence and fact provenance; and
- lineage policy/version.

Authority B supplies those facts to P08-T07. P08-T07 validates the supplied
lineage and selects the current canonical result per lifecycle. Authority B
does not select that canonical head.

The `LineageFact` is an authoritative Authority B domain fact, not merely an
evidence or input object invented by T07. T07 remains the independent validator
of whether the supplied fact is structurally valid, linked to existing result
identities, and usable for canonical-head selection. Validation by T07 does
not transfer ownership of the fact to T07.

### 2.2 Exact boundary

The exact Authority B boundary is:

> Establish, preserve, and integrity-protect an immutable authoritative fact
> that one result successor corrects or supersedes one predecessor result for
> one already-established lifecycle, without mutating either result and without
> assigning economic meaning.

The correction/supersession fact is a lineage authority. It is not a
settlement fact, realization fact, accounting fact, valuation fact,
classification fact, custody fact, signing fact, or authorization fact.

### 2.3 Placement in the lifecycle

Authority A establishes the semantic economic subject and lifecycle identity.
Authority B is a parallel downstream lineage authority for T07 result records:

```text
Authority A
    ↓
Canonical Economic Subject Identity + Lifecycle Identity
    ↓
Immutable T07 result identities
    ↓
Authority B correction/supersession fact
    ↓
T07 lineage validation and canonical-head selection
    ↓
Future analytical consumers
```

This placement is important. Authority B is not an alternative G1 economic
authority and is not a pretext to open G2, G3, G4, or G5.

## 3. Purpose

### 3.1 Fact established by B

Authority B establishes only the existence and type of a lineage relationship:

- **Correction:** a successor corrects an error or defect in a predecessor
  result.
- **Supersession:** a successor replaces a predecessor as the current
  representative without necessarily asserting that the predecessor was
  erroneous.

The relationship must be explicit, lifecycle-linked, independently
provenanced, versioned, and digest-verifiable.

### 3.2 Why Authority A is insufficient

Authority A answers which canonical economic subject and lifecycle are being
represented. It does not own result correction, result replacement, predecessor
/ successor relationships, or T07 canonical-result lineage.

A lifecycle identity alone cannot establish:

- that a later result corrects an earlier result;
- that a later result supersedes an earlier result;
- which result identities participate in the relationship; or
- whether the relationship is authoritative and provenance-complete.

Authority A must not be extended to fill this gap. Authority B must also not
feed backward into Authority A and redefine lifecycle identity.

### 3.3 Downstream consumer

P08-T07 consumes and validates Authority B facts. T07 uses validated lineage
to determine whether a lifecycle has exactly one structurally valid terminal
representative.

T07 owns canonical-head selection. Authority B does not choose a branch,
resolve a conflict by preference, or decide which economic result is valid.

## 4. Inputs

The table distinguishes the semantic role of each input. “Authoritative” means
authoritative for the fact being asserted; it does not grant Authority B
authority over the referenced economic result.

| Input | Classification | Authority B treatment |
|---|---|---|
| Authority A canonical economic subject identity | `authoritative` upstream | Preserve through the lifecycle linkage; do not create, replace, split, merge, or redefine it. |
| Authority A lifecycle identity | `authoritative` upstream | Required lifecycle anchor for the lineage fact. A mismatch fails closed. |
| Predecessor result identity | `authoritative` reference | Required relationship endpoint. B asserts the relationship; T07 validates that the referenced result exists and belongs to the lifecycle. |
| Successor result identity | `authoritative` reference | Required relationship endpoint. B asserts the relationship; T07 validates that the referenced result exists and belongs to the lifecycle. |
| Lineage type (`correction` or `supersession`) | `authoritative` fact content | Must be explicit. No precedence between the two types may be inferred. |
| Lineage fact identity | `derived` from the locked semantic fact identity | SHA-256 domain-separated digest over the fixed six-field identity projection in Section 5.5. |
| Lineage policy/version | `authoritative` governance input | Required `VersionId`; current contract fixes `p08-authority-b-policy-v1`. |
| Fact/evidence identity and provenance | `authoritative` support | Provenance link identities must be preserved and independently verifiable. Missing or contradictory provenance fails closed. |
| Explicit fact/evidence timestamps | `contextual` provenance | No Authority B timestamp field exists; upstream timestamps may be preserved only inside provenance and cannot affect identity or graph decisions. |
| Canonical lineage-edge representation | `derived` representation | Construct using the exact fields and canonicalization rules in Sections 5.3–5.7. |
| Lineage-edge digest | `derived` integrity value | SHA-256 of the complete canonical edge representation, excluding the digest itself. |
| P06 → P07 → P08 provenance chain | `contextual` required linkage | Preserve for downstream verification; it does not become a new lineage authority. |
| G2/G3/G4 economic results | `prohibited` as B semantics | B does not calculate, validate, replace, or interpret realization, accounting, or classification. T07 consumes separately governed G2/G3/G4 outputs. |
| Wallet, account, custody, signing, settlement, provider, RPC, DEX, or network state | `prohibited` | No such state is an Authority B input. |
| Wall-clock or process state | `prohibited` | Must not affect fact identity, canonical representation, conflict handling, or replay. |

### 4.1 Missing or conflicting inputs

Authority B must not reconstruct missing inputs from identifiers, timestamps,
database order, result magnitude, or caller preference. A missing endpoint,
ambiguous lifecycle, invalid authority, contradictory fact, or invalid
provenance chain fails closed using the first applicable category in Section 5.6.

The normative failure categories and precedence are defined in Section 5.6.
They map deterministically into T07's existing `INVALID_INPUT` boundary as
defined in Section 5.7.

## 5. Canonical Output

### 5.1 Conceptual output

The canonical Authority B output is an immutable **Lineage Fact** with a
separately represented **Lineage Edge**:

```text
Authoritative correction/supersession fact
    ↓
Canonical lineage-edge representation
    ↓
SHA-256 lineage-edge digest
```

The fact and edge must preserve:

- explicit fact identity;
- explicit lineage type;
- explicit contract/policy version;
- lifecycle identity;
- predecessor result identity;
- successor result identity;
- fact/evidence identity;
- authority identity;
- provenance;
- approved timestamp fields, if any;
- canonical representation; and
- integrity digest.

The normative field names, semantic types, identity participation, and
canonical representation are defined in Sections 5.4–5.7 below. They are
specification-level rules only and do not authorize implementation.

### 5.2 Immutability and correction semantics

Creating a correction or supersession fact must not mutate either the
predecessor or successor result, its identity, or its digest.

The fact is read-only after creation. A later correction or supersession is a
new fact and a new successor relationship; it is not an in-place edit.

The repository evidence supports the following direct structural constraint:

> At most one direct authoritative successor edge may leave one result.

Multiple direct authoritative successors from one predecessor create a
branching conflict. T07 must fail closed and must not select a branch.

This is an out-degree rule, not a blanket limit on the length of a lineage.
The following is structurally compatible with the repository's correction
model:

```text
R1 ── correction ──> R2 ── correction ──> R3
```

R2 may be the successor of R1 and the predecessor of R3. Multiple successors
along a chain are therefore allowed when they are separate direct edges at
successive nodes. The following cases remain distinct:

- **Multiple direct successors:** prohibited; this is a branching conflict.
- **Multiple transitive successors:** permitted as a linear multi-hop chain,
  subject to every edge being independently valid.
- **Multiple direct predecessors converging on one successor:** unsupported;
  `MERGE / CONVERGENCE UNSUPPORTED — FAIL CLOSED`.
- **A cycle or self-reference:** prohibited and must fail closed.
- **Cross-lifecycle edge:** prohibited and must fail closed.

### 5.3 Canonical representation and digest

The canonical representation is UTF-8 JSON with no byte-order mark, no
whitespace outside JSON string contents, and object keys sorted by their
Unicode code points. All strings must be Unicode NFC and must not contain
unpaired surrogate code points; a non-NFC value is invalid rather than silently
rewritten. Identity references, versions, and enum values are non-empty strings
and are validated before canonicalization.

The representation has:

- no nullable fields;
- no optional semantic fields;
- fixed object keys defined in Section 5.4;
- a provenance sequence in the fixed stage order defined in Section 5.4;
- lowercase ASCII hexadecimal SHA-256 digests;
- canonical enum strings; and
- no language-specific object or collection ordering.

The identity projection is a JSON array whose values appear in the exact order
defined in Section 5.5. Its canonical bytes are hashed with SHA-256. The edge
integrity digest is SHA-256 over the complete canonical `LineageEdge`
representation with only the `edge_digest` field omitted. A digest never
participates in the identity projection that it protects.

### 5.4 Normative field and type contract

The semantic contract uses the following categories; these are not
programming-language class requirements:

- `IdentityRef`: an upstream-established, non-empty canonical UTF-8 identity
  string in Unicode NFC form. Authority B must not generate or reinterpret it.
- `VersionId`: a non-empty ASCII token matching
  `[A-Za-z0-9][A-Za-z0-9._-]*`.
- `Digest256`: exactly 64 lowercase ASCII hexadecimal characters.
- `LineageType`: exactly `correction` or `supersession`.
- `ProvenanceLink`: one upstream chain link containing exactly
  `stage`, `record_identity`, `record_digest`, and `authority_identity`, all
  required; `record_identity` and `authority_identity` are `IdentityRef` and
  `record_digest` is `Digest256`.

The allowed `stage` values are exactly `p06_decision_intent`,
`p07_simulation_input`, `p07_simulation_result`, `p07_history`,
`p08_t01_observation`, `p08_t02_dataset`, `p08_t03_interpretation`,
`p08_t04_evaluation`, `p08_t05_snapshot`, `p08_t06_readiness`, and
`authority_a_identity`. Each value occurs exactly once in the required
sequence below.

`LineageFact` has exactly these required, non-null fields:

| Field | Semantic meaning | Type/category | Identity | Serialized | Provenance-only |
|---|---|---|---|---|---|
| `contract_version` | Authority B fact contract | `VersionId`; fixed to `p08-authority-b-lineage-v1` | yes | yes | no |
| `lineage_policy_version` | Policy governing the relationship | `VersionId`; fixed to `p08-authority-b-policy-v1` for this contract | yes | yes | no |
| `lifecycle_identity` | Established Authority A lifecycle | `IdentityRef` | yes | yes | no |
| `predecessor_result_identity` | Exactly one predecessor result | `IdentityRef` | yes | yes | no |
| `successor_result_identity` | Exactly one successor result | `IdentityRef` | yes | yes | no |
| `lineage_type` | Correction or supersession assertion | `LineageType` | yes | yes | no |
| `authority_identity` | Authority asserting the fact | `IdentityRef` | no | yes | yes |
| `provenance` | Complete upstream provenance chain | non-empty ordered `ProvenanceLink` sequence | no | yes | yes |
| `lineage_fact_identity` | Derived identity of the semantic fact | `Digest256` | derived | yes | no |

The `provenance` sequence must contain exactly one link for each stage, in this
order: `p06_decision_intent`, `p07_simulation_input`,
`p07_simulation_result`, `p07_history`, `p08_t01_observation`,
`p08_t02_dataset`, `p08_t03_interpretation`, `p08_t04_evaluation`,
`p08_t05_snapshot`, `p08_t06_readiness`, and `authority_a_identity`.

`LineageEdge` has exactly these required, non-null fields:

| Field | Semantic meaning | Type/category | Identity | Serialized | Provenance-only |
|---|---|---|---|---|---|
| `contract_version` | Authority B edge contract | `VersionId`; fixed to `p08-authority-b-lineage-v1` | yes | yes | no |
| `lineage_policy_version` | Policy governing the relationship | `VersionId`; fixed to `p08-authority-b-policy-v1` for this contract | yes | yes | no |
| `lifecycle_identity` | Established Authority A lifecycle | `IdentityRef` | yes | yes | no |
| `predecessor_result_identity` | Exactly one predecessor result | `IdentityRef` | yes | yes | no |
| `successor_result_identity` | Exactly one successor result | `IdentityRef` | yes | yes | no |
| `lineage_type` | Correction or supersession assertion | `LineageType` | yes | yes | no |
| `lineage_fact_identity` | Identity of the asserted fact | `Digest256` | derived | yes | no |
| `authority_identity` | Authority asserting the fact | `IdentityRef` | no | yes | yes |
| `provenance` | Complete upstream provenance chain | ordered `ProvenanceLink` sequence | no | yes | yes |
| `lineage_edge_identity` | Derived identity of the edge | `Digest256` | derived | yes | no |
| `edge_digest` | Integrity digest of the canonical edge representation | `Digest256` | no | yes | no |

The edge contains exactly one predecessor and one successor; there are no
collections of endpoints and no nullable or optional semantic fields.

Administrative metadata, generated IDs, random UUIDs, free-form reasons,
amounts, timestamps, effective times, provider state, and network state are not
Authority B fields. They cannot be smuggled into identity or canonical
serialization.

### 5.5 Normative identity seeds

The identity projection for both objects is the following fixed six-element
tuple, represented as a canonical JSON array:

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

`LineageFactIdentity` is:

```text
SHA-256(UTF-8("p08-authority-b:fact:v1\0" + canonical_identity_projection))
```

`LineageEdgeIdentity` is:

```text
SHA-256(UTF-8("p08-authority-b:edge:v1\0" + canonical_identity_projection))
```

The domain prefixes are fixed ASCII bytes and are not JSON fields. Provenance,
authority identity, timestamps, effective time, administrative metadata,
database order, insertion order, generated IDs, and runtime state do not
participate in either identity. Lifecycle identity, predecessor identity,
successor identity, lineage type, contract version, and policy version do
participate.

Two semantically identical lineage facts therefore receive the same fact and
edge identities on every replay. Two facts with different identity-bearing
values cannot receive the same identity except through a SHA-256 collision;
collision handling is a digest/integrity failure, not an identity-resolution
fallback.

### 5.6 Duplicate, conflict, and failure semantics

An exact duplicate is a second input whose identity matches an existing fact
and whose complete canonical `LineageFact` representation is byte-identical.
It is idempotently accepted as the already-established fact and creates no
new edge.

A conflicting duplicate is any second input with the same
`lineage_fact_identity` but a different canonical representation, including a
difference in provenance-only or authority metadata. It produces
`CONFLICTING_DUPLICATE`, fails closed, and never uses last-write-wins.

The normative failure categories are:

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

`EXACT_DUPLICATE` is an idempotent success outcome, not a failure. When more
than one failure applies, the first applicable category in the numbered list
above is the sole reported category. The implementation must not select a
different category from input order, timestamps, provider state, or caller
preference.

### 5.7 Exact T07 adapter mapping

For one valid Authority B fact, B supplies exactly one edge projection to T07
containing the fact identity, edge identity, contract version, policy version,
lifecycle identity, predecessor identity, successor identity, lineage type,
authority identity, provenance, canonical edge representation, and edge
digest. `EXACT_DUPLICATE` reuses the already-established same projection and
does not create another edge.

The mapping is one-to-one and representational only: no semantic field is
renamed into a different meaning, and no economic value is created. T07
consumes the projection and independently validates identity, lifecycle
membership, endpoint existence, provenance, digest, graph invariants, and
failure state. T07 retains sole authority to select the canonical head.

Any Authority B failure maps to T07's existing primary `INVALID_INPUT` result.
The secondary failure reason is deterministic:

- `MALFORMED_FACT`, `INVALID_IDENTITY`, `INVALID_LIFECYCLE`,
  `MISSING_ENDPOINT`, `CROSS_LIFECYCLE_REFERENCE` →
  `MISSING_REQUIRED_INPUT`;
- `CONFLICTING_DUPLICATE`, `LINEAGE_SELF_REFERENCE`, `LINEAGE_CYCLE`,
  `MERGE_UNSUPPORTED`, `LINEAGE_BRANCH_CONFLICT`, and
  `CONTRADICTORY_LINEAGE` → `CONFLICTING_INPUT`;
- `PROVENANCE_FAILURE` → `PROVENANCE_LINKAGE_FAILURE`; and
- `DETERMINISM_FAILURE` or `DIGEST_FAILURE` → `UNRESOLVED_RESIDUAL`.

T07 does not infer a missing fact, repair an endpoint, or select a branch from
any failure mapping.

## 6. Authority B Boundary

### 6.1 Authority B may establish

Authority B may:

1. assert that a named successor corrects a named predecessor;
2. assert that a named successor supersedes a named predecessor;
3. bind the relationship to one established lifecycle;
4. preserve predecessor and successor identities without mutation;
5. preserve the fact’s authority, evidence, provenance, and policy/version;
6. produce deterministic lineage-fact and lineage-edge identities under the
   normative semantic and serialized contract;
7. produce an integrity digest for the canonical edge representation; and
8. fail closed when the relationship is missing, ambiguous, contradictory,
   branching, cyclic, orphaned, or non-canonical.

### 6.2 Authority B must not establish

Authority B must not:

- create, split, merge, substitute, or redefine a canonical economic subject;
- create or redefine a lifecycle;
- infer lifecycle identity from events, timestamps, amounts, fills, or ordering;
- select the T07 canonical head;
- choose between conflicting authoritative lineage branches;
- repair missing predecessor or successor references;
- establish execution or a fill;
- establish custody or ownership of an account;
- establish settlement;
- establish realization eligibility;
- calculate or establish accounting;
- calculate valuation, P&L, ROI, or performance;
- assign `WIN`, `LOSS`, or `BREAKEVEN`;
- create trading, execution, or Risk/Capital Authorization;
- connect to a wallet, provider, RPC, DEX, exchange, database, network, or API;
- use paper artifacts as live economic truth; or
- authorize P08-T08, P09, or any later phase.

Evidence being present never grants any of these authorities implicitly.

## 7. Identity Linkage

### 7.1 Required chain

Authority B must preserve this identity path:

```text
Canonical Economic Subject Identity
    ↓
Lifecycle Identity
    ↓
Lineage Fact Identity
    ↓
Lineage Edge Identity / Digest
    ↓
Referenced predecessor and successor result identities
    ↓
T07 validated lineage and canonical-head outcome
```

The lineage fact is not allowed to replace the Authority A lifecycle identity.
It references the established lifecycle and result identities; it does not
derive a new lifecycle from the existence of the edge.

### 7.2 Identity safety

The following must fail closed:

- a fact whose lifecycle does not match the predecessor or successor;
- a predecessor or successor from another lifecycle;
- a missing endpoint;
- a duplicate or ambiguous semantic fact identity;
- contradictory facts for the same edge;
- multiple authoritative successor edges from one predecessor;
- a cycle in the lineage graph;
- an edge with an invalid authority or provenance chain; or
- a digest that does not match the canonical representation.

An exact duplicate is byte-identical and idempotently accepted. Any
same-identity representation difference is `CONFLICTING_DUPLICATE` and fails
closed. No duplicate may be treated as a new authoritative fact.

No timestamp, database insertion order, retrieval order, result magnitude, or
caller preference may resolve an identity collision.

## 8. Provenance

Authority B must preserve, without replacement or silent omission, the full
available chain:

```text
P06 DecisionIntent
→ P07 simulation input/result/history
→ P08-T01 observation
→ P08-T02 dataset
→ P08-T03 interpretation
→ P08-T04 evidence evaluation
→ P08-T05 evaluation snapshot
→ P08-T06 readiness
→ Authority A subject/lifecycle identity
→ Authority B lineage fact
→ T07 lineage validation and canonical-head result
```

P08-T06 readiness remains structural non-economic readiness. It is not
economic evidence and cannot authorize the lineage fact to become realization,
accounting, or classification authority.

Authority B must preserve the identity, version, and digest of any predecessor
record required by the applicable contract. It must not fetch, infer, repair,
substitute, or silently discard missing or contradictory provenance.

## 9. Temporal Governance

### 9.1 Allowed timestamps

Authority B has no event time, reference time, correction time, supersession
time, effective time, settlement time, or as-of/cutoff field. An upstream
timestamp may be preserved only as provenance data under its existing contract.
It is not an Authority B clock, does not participate in identity, and does not
affect graph ordering or canonical-head selection.

Absence of an Authority B timestamp is therefore normative. A future timestamp
may appear in preserved upstream provenance only if that upstream contract
accepts it; B must not interpret, compare, or use it for any semantic decision.
Settlement time is not an Authority B authority and cannot make a result
realized.

### 9.2 Prohibited temporal behavior

Authority B must not:

- read the wall clock or current time;
- use local timezone or process time;
- select a successor by earliest/latest timestamp;
- resolve a conflict by timestamp;
- use a later fact to retroactively mutate an earlier result;
- use P08-T02 `as_of_time` as an economic endpoint;
- use a future analytical cutoff;
- leak future information into fact identity or lineage validation; or
- allow retrieval, insertion, filesystem, or network timing to affect output.

Analytical as-of selection belongs to a separately governed future analytical
authority and must not feed backward into B or T07 canonical-head selection.

## 10. Determinism and Replay

The required replay invariant is:

> The same authoritative inputs, contract versions, policy versions, and
> canonical representations produce the same Authority B result.

Replay must produce identical:

- lineage fact identity;
- lineage edge identity;
- canonical edge representation;
- lineage-edge digest;
- validation outcome; and
- failure state.

The result must not depend on:

- wall-clock time;
- randomness;
- local timezone;
- insertion or retrieval order;
- database or filesystem state;
- network or provider state;
- hidden configuration;
- process identity; or
- memory address.

The field-level serialization, identity projection, digest construction,
duplicate policy, failure precedence, and T07 mapping are normatively defined
in Sections 5.3–5.7. This resolves the previous specification blockers for the
separate closure audit; it does not authorize implementation.

## 10A. Prior Formal Audit Findings — Historical

The findings in this section are retained as the record of the previous
formal audit. The blocker-resolution rules in Sections 5.3–5.7 and Section 19
supersede the prior unresolved determinations. They do not authorize
implementation.

### 10A.1 Authority A status reconciliation

The repository now records Authority A as:

`SPECIFICATION COMPLETE / CLOSED / AUDITED PASS — IMPLEMENTATION NOT AUTHORIZED`

This status is present in the Authority A specification, its standalone audit
record at `docs/P08-AUTHORITY-A-SPECIFICATION-AUDIT.md`, and
`PROJECT_STATE.md`. Authority A's semantic boundary is therefore resolved for
this bounded Authority B audit, while its implementation remains unauthorized.

No Authority A compatibility blocker remains. Authority B must still consume
Authority A's established lifecycle identity and must not redefine, split,
merge, or replace it.

### 10A.2 Authority B object classification

`LineageFact` is an authoritative object owned by Authority B because the
governance extension explicitly assigns B ownership of correction facts,
supersession facts, predecessor/successor relationships, lineage identity,
lineage provenance, and lineage policy/version.

It is also an input to T07. Those statements are not contradictory:

```text
Authority B owns and asserts the fact
        ↓
T07 validates the fact and its graph placement
        ↓
T07 selects the canonical head
```

T07 is not the origin of the lineage assertion, and B does not inherit T07's
canonical-head authority.

### 10A.3 Correction/supersession graph invariant

The governed graph is a directed, lifecycle-scoped graph whose nodes are
independently immutable result identities and whose edges are independently
provenanced correction or supersession facts.

The currently supported invariant is:

1. each direct edge has exactly one predecessor result and one successor
   result;
2. one result has at most one direct authoritative successor edge;
3. a successor may become the predecessor of a later edge;
4. a linear multi-hop chain is valid when every edge is independently valid;
5. multiple direct successors from one predecessor are a branching conflict;
6. direct predecessor convergence/merging is `UNRESOLVED`;
7. self-reference is invalid;
8. cycles are invalid;
9. predecessor and successor must belong to the same lifecycle; and
10. missing, orphaned, contradictory, or non-resolvable endpoints fail closed.

T07 may select one terminal representative only after this graph has been
validated. Neither B nor T07 may choose a branch using timestamps, result
magnitude, insertion order, or caller preference.

### 10A.4 Identity closure

The repository provides the Authority A lifecycle seed:

```text
Canonical Economic Subject Identity
+ P06 DecisionIntent Identity
```

The repository does **not** provide an approved semantic identity seed for:

- `LineageFact`;
- `LineageEdge`;
- the predecessor reference; or
- the successor reference.

Predecessor and successor references are required relationship endpoints, but
their presence does not define the semantic identity seed of the fact or edge.
The result identity seed referenced by those endpoints is itself a separate
specification dependency. No seed is created by this audit.

### 10A.5 Canonical representation closure

The repository establishes the following semantic requirements:

- the fact and edge are immutable;
- the edge has deterministic canonical representation;
- canonical UTF-8 and deterministic serialization are required;
- object keys and governed collections are deterministically ordered;
- canonical enum and authorized UTC timestamp representations are required;
- the digest covers the complete canonical edge representation;
- the digest is SHA-256; and
- the digest is excluded from its own input and cannot define semantic
  identity circularly.

The following remain unresolved:

- exact field set;
- exact field types;
- required versus optional fields;
- nullability;
- exact field ordering;
- normalization rules for every field;
- exact canonical serialization format; and
- exact identity-to-representation adapter.

### 10A.6 Timestamp closure

The repository does not define Authority B's fact-creation time, correction
time, supersession time, or effective time as semantic inputs.

Predecessor/successor result timestamps belong to the referenced result
contracts. They must not be used by B or T07 to choose a canonical result.

The current safe rule is:

- explicitly supplied timestamps may be preserved as governed provenance;
- no B timestamp is an Authority B clock;
- no wall-clock/current-time dependency is allowed;
- timestamps cannot resolve a conflict or choose a branch; and
- effective-time semantics remain `UNRESOLVED`.

### 10A.7 Duplicate and conflict closure

The current governance supports deterministic failure categories for missing
references, invalid lineage, branching, cycles, digest failures, provenance
failures, and conflicting input. It does not fully define duplicate policy.

| Case | Current determination |
|---|---|
| Exact replay of the same fact | Same canonical inputs must replay identically; idempotent acceptance versus duplicate reporting is `UNRESOLVED`. |
| Same identity with different payload | Must fail closed; exact public failure mapping is `UNRESOLVED`. |
| Conflicting correction facts | Must not be resolved by preference; exact failure precedence is `UNRESOLVED`. |
| Conflicting supersession facts | Must not be resolved by preference; exact failure precedence is `UNRESOLVED`. |
| Multiple direct successors | `LINEAGE_BRANCH_CONFLICT` is the governed semantic category. |
| Multiple transitive successors in a linear chain | Valid when each direct edge is valid. |
| Direct predecessor convergence/merge | `UNRESOLVED`; no implementation acceptance rule exists. |
| Contradictory graph edges | Must fail closed; exact category precedence is `UNRESOLVED`. |
| Cycle or self-reference | `LINEAGE_CYCLE` / invalid lineage behavior is established semantically; exact public mapping remains subject to the existing contract. |

No new enum or silent conflict-resolution rule is introduced.

### 10A.8 Failure taxonomy and precedence

The existing governance material names these relevant categories:

- `MISSING_LIFECYCLE_SPLIT_FACT`;
- `INVALID_LIFECYCLE_MAPPING`;
- `MISSING_SUCCESSOR`;
- `MISSING_PREDECESSOR`;
- `INVALID_LINEAGE`;
- `LINEAGE_BRANCH_CONFLICT`;
- `LINEAGE_CYCLE`;
- `UNRESOLVED_CANONICAL_STATE`;
- `DIGEST_FAILURE`;
- `PROVENANCE_LINKAGE_FAILURE`;
- `CONFLICTING_INPUT`; and
- `INVALID_INPUT`.

The semantic meanings are sufficiently established for audit purposes.
However, the public enum spelling, multi-failure precedence, error payload
shape, and mapping into the already-closed T07 contract are not fully locked.
Those details remain `UNRESOLVED`; this audit does not create replacement
failure codes.

### 10A.9 T07 integration closure

The conceptual mapping is:

```text
Authority B LineageFact
        ↓
T07 validates fact identity, endpoints, lifecycle, provenance, digest,
and graph invariants
        ↓
T07 determines canonical-head outcome per lifecycle
```

Authority B must not select the canonical head. T07 must not invent, repair,
or silently substitute a missing lineage fact. A valid correction chain can
contain multiple successive result nodes, but a branch, cycle, missing
endpoint, invalid lifecycle, or unresolved merge cannot be selected.

### 10A.10 Economic and custody closure

The following remain explicitly outside Authority B:

- realization;
- settled account;
- custody;
- signer;
- provider selection;
- settlement;
- accounting;
- P&L;
- ROI;
- `WIN`;
- `LOSS`;
- `BREAKEVEN`;
- trading authority;
- execution authority; and
- Risk/Capital Authorization.

The supplied gate status remains unchanged:

```text
G1 = BLOCKED / UNRESOLVED
G2 concrete endpoint = BLOCKED_BY_G1
G3 = BLOCKED_BY_G1_G2
G4 = BLOCKED_BY_G3
G5 = BLOCKED
```

## 11. G1 / G2 / G3 / G4 / G5 Impact Matrix

The following statuses are the supplied governance baseline and are not
promoted by this audit.

| Gate | Current status | Authority B impact | Dependency direction | What remains blocked |
|---|---|---|---|---|
| G1 | `UNRESOLVED_NO_AUTHORITY_EXISTS` | B does not create or resolve the missing G1 economic authority. B is a distinct lineage-fact authority and cannot be promoted into G1. | B depends on established Authority A lifecycle identity and result references; it does not depend on G1 to invent lineage semantics. | The concrete G1 authority and endpoint remain unresolved. |
| G2 | Architectural model `RESOLVED_PROVIDER_NEUTRAL`; concrete endpoint `BLOCKED_BY_G1` | B does not define realization eligibility and cannot make a G2 endpoint available. | T07 may consume B lineage alongside validated G2 output; B does not feed realization semantics backward. | G2 concrete realization endpoint remains blocked by G1. |
| G3 | `BLOCKED_BY_G1_G2` | B does not calculate accounting, P&L, ROI, cost basis, numeraire, or economic result. | B preserves result lineage references; G3 remains authoritative for accounting when separately unlocked. | G3 accounting and economic result semantics remain blocked. |
| G4 | `BLOCKED_BY_G3` | B does not classify performance and cannot assign WIN/LOSS/BREAKEVEN. | T07 consumes G4 classification separately; B does not resolve classification conflicts through lineage. | G4 classification remains blocked by G3. |
| G5 | `BLOCKED` | B does not promote lineage evidence into G5 authority and does not alter G5. | Any G5 consumer remains downstream of its own approved prerequisites. | G5 remains blocked; no downstream promotion is authorized. |

Authority B therefore resolves none of the G1–G5 economic gates. Its role is
limited to the lineage relationship that T07 validates around immutable result
records.

## 12. Custody / Signing / Account Test

### 12.1 Result

Custody, signing, account identity, settled economic account, account-state
authority, and settlement authority are **not Authority B prerequisites for its
semantic boundary**. Authority B can assert a lineage relationship without
selecting or owning any account or custody model.

### 12.2 Explicit non-selection

Authority B does not select or imply:

- user-controlled custody;
- application-controlled custody;
- exchange custody;
- broker/custodian custody; or
- hybrid custody.

It also does not select a signing owner, wallet provider, RPC provider, DEX,
exchange, or settlement provider.

If a future economic authority requires any of these dependencies, that
dependency is `BLOCKED` until separate product governance resolves it.
Authority B must not fill the gap by inference.

## 13. Economic Authority Status

Authority B has **no economic authority**.

It must not:

- establish settlement or realization;
- calculate or validate P&L, ROI, valuation, or performance;
- classify WIN, LOSS, or BREAKEVEN;
- treat a paper result, paper fill, or paper ledger as external economic truth;
- authorize capital or trading;
- authorize execution, signing, or broadcast; or
- promote an immutable result lineage fact into live economic authority.

G2 remains the realization-eligibility authority, G3 remains the accounting /
economic-result authority, and G4 remains the classification authority when
their separate governance gates are resolved. T07 validates and assembles
those supplied semantics; B only supplies lineage facts.

## 14. Resolved, Unresolved, Blocked, and Prohibited Findings

### 14.1 Resolved

- Authority B owns correction and supersession lineage facts.
- A lineage fact is bound to an already-established lifecycle.
- Predecessor and successor result identities are explicit.
- Correction and supersession are distinct relationship types.
- Results and facts are immutable; later lineage does not mutate historical
  records.
- At most one direct authoritative successor edge may leave a result; a
  multi-hop correction/supersession chain is not itself a branch.
- Branches, cycles, missing references, contradictory facts, and invalid
  provenance fail closed.
- SHA-256 protects a deterministic canonical edge representation and is not
  semantic identity.
- T07, not B, selects the canonical head per lifecycle.
- B does not own G2, G3, G4, G5, custody, signing, settlement, or execution.

### 14.2 Resolved by blocker-resolution pass

- Exact serialized fields and semantic types for `LineageFact` and
  `LineageEdge`.
- Exact semantic identity seeds for lineage facts and edges.
- Exact field ordering, normalization, nullable-field policy, and digest input.
- Exact current contract and policy version values.
- Exact failure categories and first-applicable precedence.
- Exact mapping into the closed T07 input/output contract.
- Exact duplicate handling policy.
- Exact timestamp and effective-time semantics.

### 14.3 Blocked

- Formal Authority B closure audit findings recorded in Section 20.
- Cross-implementation canonical JSON escaping rules.
- Deterministic duplicate-comparison context.
- Exact field-level adapter mapping into the existing T07 contract.
- Implementation-ready Authority B runtime contract and implementation
  authorization.
- Any runtime or persistence implementation of B.
- Any G1 concrete economic authority endpoint.
- G2 concrete realization endpoint.
- G3 accounting/economic result.
- G4 classification.
- G5 downstream authority.
- Any custody, signing, account, settlement, provider, or network model that
  would be needed by a future economic authority.

### 14.4 Prohibited

- Source-code or test implementation under this work order.
- P08-T08 creation.
- P09 start.
- Reopening P06 or P07.
- Wallet/provider selection.
- Economic formulas or WIN/LOSS/BREAKEVEN definitions.
- Live execution, signing, broadcast, or capital authorization.
- Inferring authority from evidence presence.

## 15. Authority A Baseline Reconciliation

Authority A is formally reconciled and closed at specification level:

`SPECIFICATION COMPLETE / CLOSED / AUDITED PASS — IMPLEMENTATION NOT AUTHORIZED`

The standalone Authority A audit records the semantic PASS, the bounded
identity authority, the deterministic/replay requirements, the deferred
representation-level items, and the explicit implementation prohibition.
Authority B remains downstream of that closed specification and cannot use this
audit to extend Authority A's authority.

## 16. Audit Conclusion and Next Governance Gate

The final formal Authority B closure audit is complete. Authority B remains
**SPECIFICATION-LEVEL BLOCKED** and implementation-unauthorized.

The audit confirms that B owns only immutable correction/supersession lineage
facts and their provenance, while T07 validates them and selects the canonical
head. The directed, lifecycle-scoped graph invariants are explicit for
single-predecessor/single-successor edges, linear multi-hop chains, branching,
self-reference, cycles, cross-lifecycle references, missing endpoints, and
contradictory relationships.

Predecessor convergence/merge remains intentionally deferred by design:

`MERGE / CONVERGENCE UNSUPPORTED — FAIL CLOSED`

It must not be inferred as valid, invalid, or preferentially resolved, and no
merge implementation is authorized.

Authority A compatibility, graph semantics, provenance, and the economic
authority boundary pass. Canonical serialization, duplicate context, and the
exact field-level T07 adapter remain blocking specification gaps as recorded in
Section 20. No T07 redesign is authorized.

The Authority B closure result remains separate from G1–G5 economic authority
decisions.

## 17. Formal Audit Record — 2026-09-08

### 17.1 Scope and documents reviewed

This formal audit reviewed:

- `REPLIT_RULES.md`;
- `PROJECT_STATE.md`;
- `docs/P08-AUTHORITY-B-SPECIFICATION-AUDIT.md`;
- `docs/P08-CANONICAL-ECONOMIC-SUBJECT-LIFECYCLE-IDENTITY-AUTHORITY-SPECIFICATION.md`;
- `docs/P08-AUTHORITY-A-SPECIFICATION-AUDIT.md`;
- `docs/P08-T07-CANONICAL-RESULT-AUTHORITY-EXTENSION-SPECIFICATION.md`; and
- `docs/P08-T07-SPECIFICATION.md`.

### 17.2 Findings matrix — Historical

| Audit area | Result | Determination |
|---|---|---|
| Authority A verification | PASS | Authority A is formally closed; implementation remains unauthorized. |
| Semantic identity seed | BLOCKED | `LineageFact` and `LineageEdge` seeds and endpoint participation are unresolved. |
| Field/type contract | BLOCKED | Exact fields, types, optionality, nullability, cardinality, and identity fields are unresolved. |
| Canonical serialization | BLOCKED | Semantic requirements exist, but exact ordering, normalization, nullable policy, and adapter are unresolved. |
| Timestamp/effective-time semantics | BLOCKED | No wall-clock dependency is allowed, but authoritative temporal concepts are not locked. |
| Duplicate semantics | BLOCKED | Exact duplicate acceptance/reporting and conflicting duplicate treatment are unresolved. |
| Conflict semantics | PASS with deferred mapping | Branching and contradictory relationships fail closed; public category/precedence mapping remains unresolved. |
| Merge/convergence | DEFERRED / FAIL CLOSED | Convergence is intentionally unsupported for this scope; no nondeterministic merge behavior is permitted. |
| Graph invariants | PASS | Directed, lifecycle-scoped, single-edge endpoints, linear multi-hop, branch, cycle, self-reference, cross-lifecycle, missing endpoint, and orphan rules are bounded. |
| Failure taxonomy/precedence | BLOCKED | Semantic categories exist, but public vocabulary, precedence, payload, and T07 mapping are unresolved. |
| Provenance | PASS | The P06 → P07 → P08 → Authority A → Authority B → T07 chain is preserved and B cannot bypass A. |
| Authority A compatibility | PASS | B consumes an established lifecycle and cannot redefine Authority A identity. |
| T07 compatibility | PASS semantically / BLOCKED at adapter level | T07 retains graph validation and canonical-head selection; exact adapter mapping remains unresolved. |
| Determinism/replay | PASS conditionally | Prohibited time/order/provider/random dependencies are excluded; unresolved identity/serialization decisions still block closure. |
| Economic/custody boundary | PASS | B has no realization, accounting, classification, custody, signing, execution, or Risk/Capital authority. |

### 17.3 Historical formal verdict

The previous audit did not establish specification closure and correctly
recorded:

**AUTHORITY B SPECIFICATION-LEVEL BLOCKED**

The blocker-resolution pass below supersedes that previous unresolved finding
for the current governance state. A separate formal closure audit is still
required and implementation remains unauthorized.

## 18. Implementation Status

**AUTHORITY B IMPLEMENTATION = NOT AUTHORIZED**

This document does not authorize source changes, tests, persistence, runtime
behavior, wallet access, provider selection, economic calculation, P08-T08,
P09, or any later phase.

## 19. Blocker Resolution Pass — 2026-09-08 — Historical

This section records the resolution of the eight blockers identified by the
previous formal audit. The normative rules are defined in the Authority B
specification and are summarized here for audit traceability. This is not the
formal closure audit.

| Original blocker | Result | Resolution |
|---|---|---|
| Semantic identity seed | RESOLVED | `LineageFactIdentity` and `LineageEdgeIdentity` use domain-separated SHA-256 digests over the fixed identity projection: contract version, policy version, lifecycle identity, predecessor result identity, successor result identity, and lineage type. |
| Exact field/type contract | RESOLVED | The specification now defines the required semantic fields, types/categories, cardinality, nullability, identity participation, serialization participation, and provenance-only fields for the fact and edge. |
| Canonical serialization | RESOLVED | Canonical UTF-8 JSON, NFC string validation, sorted keys, fixed provenance order, no nulls, no optional semantic fields, fixed identity projection order, and SHA-256 edge digest input are normative. |
| Timestamp/effective-time semantics | RESOLVED | Authority B has no event, reference, correction, supersession, or effective-time field. Any upstream timestamp is provenance-only and cannot affect identity, graph order, conflict resolution, or canonical-head selection. |
| Duplicate handling | RESOLVED | Byte-identical canonical facts with the same identity are idempotently accepted. Any same-identity representation difference is `CONFLICTING_DUPLICATE`, fails closed, and never uses last-write-wins. |
| Conflict/failure vocabulary and precedence | RESOLVED | A closed failure taxonomy and first-applicable precedence order are defined, including deterministic mapping to T07's existing `INVALID_INPUT` failure boundary. |
| Exact adapter mapping into T07 | RESOLVED | One valid Authority B fact produces one edge projection supplied to T07; B supplies identity, endpoints, type, versions, provenance, representation, digest, and validation state, while T07 revalidates graph placement and selects the canonical head. |
| Merge/convergence treatment | DEFERRED BY DESIGN | `MERGE / CONVERGENCE UNSUPPORTED — FAIL CLOSED` is normative. No merge semantics or graph redesign is introduced. |

### 19.1 Resolution boundary

The blocker-resolution pass establishes a deterministic specification contract,
but it does not declare Authority B closed or implementation-ready. The next
gate is:

**NEXT GATE: FORMAL AUTHORITY B SPECIFICATION CLOSURE AUDIT**

## 20. Final Formal Specification Closure Audit — 2026-09-08

### 20.1 Scope and documents reviewed

This final closure audit reviewed:

- `REPLIT_RULES.md`;
- `PROJECT_STATE.md`;
- this Authority B specification/audit record;
- `docs/P08-CANONICAL-ECONOMIC-SUBJECT-LIFECYCLE-IDENTITY-AUTHORITY-SPECIFICATION.md`;
- `docs/P08-T07-CANONICAL-RESULT-AUTHORITY-EXTENSION-SPECIFICATION.md`; and
- `docs/P08-T07-SPECIFICATION.md`.

Authority A was verified as:

`SPECIFICATION COMPLETE / CLOSED / AUDITED PASS — IMPLEMENTATION NOT AUTHORIZED`

No source code, runtime, database, migration, test, dependency, T07
implementation, Authority A implementation, P07, P06 runtime, or P09 change
was made by this audit.

### 20.2 Resolution verification

| Audit area | Result | Determination |
|---|---|---|
| Identity seed | PASS | Fact and edge identities use the fixed lifecycle/endpoint/type/version projection with domain-separated SHA-256 prefixes and no runtime, timestamp, provenance, or provider inputs. |
| Field/type contract | PASS | Fact and edge fields, categories, requiredness, nullability, cardinality, identity participation, serialization participation, and provenance-only status are explicit. |
| Canonical serialization | BLOCKED | UTF-8, NFC, sorted keys, no nulls, and digest coverage are defined, but JSON string escaping is not fixed. Independent implementations can produce different bytes for the same semantic string. |
| Timestamp/effective-time | PASS | Authority B has no temporal semantic field; upstream timestamps are provenance-only and do not affect identity, ordering, conflict resolution, or canonical-head selection. |
| Duplicate semantics | BLOCKED | Exact and conflicting duplicates are distinguished, but the authoritative existing-fact comparison set is not defined as an explicit deterministic input. Ambient database or registry state is prohibited by the replay contract. |
| Conflict/failure precedence | PASS within B / BLOCKED at adapter detail | B defines a first-applicable precedence, but exact field-level preservation into the current T07 contract is not locked. |
| Graph invariants | PASS | Directed lifecycle-scoped edges, linear multi-hop chains, branching failure, self-reference, cycles, cross-lifecycle references, missing endpoints, and contradictory relationships are bounded deterministically. |
| Merge/convergence | DEFERRED BY DESIGN | `MERGE / CONVERGENCE UNSUPPORTED — FAIL CLOSED` is explicit and introduces no merge authority. |
| Authority A compatibility | PASS | B consumes the established Authority A lifecycle and does not create, split, merge, substitute, or redefine economic subject identity. |
| T07 compatibility | BLOCKED | The conceptual one-to-one projection is clear, but the specification does not identify the exact existing T07 input/output fields and behavior for correction versus supersession, fact/edge identities, provenance, digest, and mapped failure reasons. |
| Provenance | PASS | The complete P06 → P07 → P08 → Authority A → Authority B → T07 chain is preserved without shortcut or inferred repair. |
| Determinism/replay | BLOCKED | Identity and graph outcomes are deterministic, but serialization escaping and duplicate comparison context prevent a complete replay guarantee. |
| Economic authority boundary | PASS | Authority B establishes lineage only and does not establish realization, accounting, P&L, ROI, classification, custody, signing, settlement, execution, risk, or capital authorization. |

### 20.3 Exact remaining blockers

1. **Canonical JSON escaping is not locked.** The document fixes UTF-8,
   normalization, sorted keys, and whitespace, but does not specify the exact
   escaping profile for quotes, reverse solidus, control characters, Unicode
   characters, and equivalent escaped/unescaped forms. Two independent
   implementations can therefore produce different canonical bytes and
   different identities or digests.

   **Decision required:** select and normatively specify one exact JSON escaping
   and byte-serialization profile for both the identity projection and full
   fact/edge representations.

2. **Duplicate comparison context is not locked.** The duplicate rule compares
   a new fact with an “existing fact,” while the replay contract prohibits
   dependence on ambient database/filesystem state. The specification does not
   define the authoritative established-fact set, its input boundary, or its
   order-independent replay representation.

   **Decision required:** define the deterministic authoritative fact set or
   registry snapshot supplied to duplicate validation, including its identity
   and canonical ordering, without introducing last-write-wins behavior.

3. **The T07 adapter is not field-level exact.** The B document describes a
   generic edge projection, but the existing T07 contract names concrete
   `correction_lineage` and `supersession_lineage` inputs and bounded failure
   reasons. It does not specify exactly how one B fact maps to those fields,
   how fact/edge identity and digest are carried, or how every B failure maps
   without semantic loss.

   **Decision required:** lock the exact one-to-one adapter field mapping and
   deterministic failure mapping against the existing T07 input/output
   contract, without changing T07 ownership or redesigning its semantics.

### 20.4 Final verdict

**AUTHORITY B SPECIFICATION-LEVEL BLOCKED**

The previous blocker-resolution pass was substantively useful but did not
resolve the three remaining semantic/contract-level gaps above. Authority B
implementation remains unauthorized, P09 must not start, and no workaround or
implementation placeholder is permitted.