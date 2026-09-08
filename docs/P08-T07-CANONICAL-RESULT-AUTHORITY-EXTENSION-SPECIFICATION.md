# P08-T07 — Canonical Result Authority Extension

**Status:** SPECIFICATION DRAFT COMPLETE — ARCHITECT APPROVED / IMPLEMENTATION NOT AUTHORIZED  
**Phase:** P08 — Outcome Learning  
**Task relationship:** Extension of the closed P08-T07 Economic Outcome Interpretation Boundary  
**Nature:** Immutable, deterministic, provider-neutral, read-only governance specification

This document specifies the approved canonical-result authority extension for
P08-T07. It does not reopen, replace, or modify the closed P08-T07 runtime
implementation. It does not authorize implementation, persistence, external
access, or downstream P08 work.

## 1. Purpose and Scope

The extension defines the governance and validation contract for:

1. the lifecycle identity consumed by T07;
2. the authority boundary for lifecycle identity and lineage facts;
3. semantic result identity;
4. canonical result representation and integrity digest;
5. immutable correction and supersession lineage;
6. deterministic successor and canonical-head validation;
7. the distinction between invalid representatives, unresolved states, and
   valid economic results; and
8. the boundary between the current canonical T07 representative and future
   analytical as-of selection.

The extension is limited to canonical-result authority. It does not create or
recalculate economic facts.

The extension does not authorize:

- G2 realization calculations;
- G3 accounting calculations;
- G4 classification calculations;
- P&L, ROI, valuation, or performance metrics;
- strategy scoring or model updates;
- execution, capital, wallet, signing, or broadcast behavior;
- provider, network, RPC, DEX, exchange, or external API access;
- persistence beyond an explicitly authorized future architecture;
- CPA, AEA, Snapshot, or P08-T08 implementation; or
- changes to the closed P08-T07 runtime.

## 2. Relationship to the Existing P08-T07 Contract

The existing P08-T07 contract remains the economic interpretation and
assembly boundary for one validated lifecycle. G2, G3, and G4 remain
authoritative for their respective economic semantics:

```text
G2 realization eligibility
        ↓
G3 accounting / economic result
        ↓
G4 WIN / LOSS / BREAKEVEN classification
        ↓
T07 validation and assembly
```

This extension adds the authority and deterministic selection rules required
to establish which supplied T07 result is the current canonical
representative.

The extension is additive at the specification level:

- existing T07 economic semantics remain unchanged;
- existing upstream result meanings remain authoritative;
- existing immutable result behavior remains required;
- canonical-result selection is governed by this extension; and
- implementation requires a later, explicit authorization.

Until that authorization occurs, the current P08-T07 implementation remains
the closed implementation boundary and is not changed by this document.

## 3. Authority Boundary

Authority A and Authority B are two bounded governance authorities within the
upstream Economic Evidence Governance boundary. They may be documented or
implemented as extensions of that governance surface; this specification does
not require them to be separate runtime services.

### 3.1 Authority A — Canonical Economic Subject / Lifecycle Identity

Authority A owns:

- canonical economic subject identity;
- lifecycle identity;
- lifecycle equivalence;
- lifecycle mapping;
- authoritative Lifecycle Split Facts; and
- lifecycle mapping conflict resolution.

Authority A supplies the lifecycle identity and any authoritative split fact
consumed by T07.

Authority A does not own:

- G2 realization semantics;
- G3 accounting semantics;
- G4 classification semantics;
- T07 canonical-head selection;
- CPA analytical cohort selection;
- AEA analytical cutoff; or
- future performance metrics.

### 3.2 Authority B — Correction / Supersession Lineage Facts

Authority B owns:

- authoritative correction facts;
- authoritative supersession facts;
- predecessor/successor relationships;
- lineage fact identity;
- lineage evidence and fact provenance; and
- lineage policy/version.

Authority B supplies the lineage facts consumed and validated by T07.

Authority B does not own:

- G2 realization semantics;
- G3 accounting semantics;
- G4 classification semantics;
- T07 canonical-head selection;
- CPA analytical cohort selection;
- AEA analytical cutoff; or
- future performance metrics.

### 3.3 T07 authority boundary

T07:

- validates supplied lifecycle identity;
- validates supplied lifecycle split facts;
- validates supplied correction and supersession facts;
- validates result and lineage integrity;
- assembles validated economic semantics; and
- deterministically selects the current canonical head.

T07 must not:

- invent a lifecycle;
- invent or infer a lifecycle split;
- invent a lineage fact;
- repair a missing predecessor or successor;
- select between conflicting authoritative branches;
- recalculate G2, G3, or G4 semantics; or
- treat event grouping as lifecycle authority.

## 4. Lifecycle Identity Input

### 4.1 Lifecycle anchor

The V1 economic subject is a Trade Lifecycle anchored by:

```text
P06 DecisionIntent
+
Canonical Economic Subject
```

The lifecycle identity consumed by T07 must be supplied by Authority A or by
an explicitly authorized upstream contract representing Authority A.

### 4.2 Cardinality

The normative V1 cardinality is:

```text
one lifecycle → exactly one P06 DecisionIntent

one P06 DecisionIntent → exactly one lifecycle by default

one P06 DecisionIntent → multiple lifecycles only through
an explicit authoritative Lifecycle Split Fact
```

When a valid split fact exists, every resulting lifecycle still has exactly
one P06 DecisionIntent. The same P06 DecisionIntent may be referenced by the
resulting lifecycles only under that explicit exception.

Without a valid split fact, a claimed multiple-lifecycle mapping fails closed
with `INVALID_LIFECYCLE_MAPPING`.

### 4.3 Lifecycle Split Fact

A Lifecycle Split Fact is an explicit semantic governance fact. It is not
event grouping.

The fact must:

- be authoritative under Authority A;
- identify the originating P06 DecisionIntent;
- identify each resulting lifecycle identity;
- state the authoritative reason or basis for the split;
- preserve its own fact identity and provenance; and
- be independently validated before T07 uses the resulting mapping.

The exact field names and serialized field types for the Lifecycle Split Fact
are a **specification-level governance dependency** until separately locked.
No field may be added merely to encode implementation convenience.

### 4.4 Event association

Events may be associated with an existing lifecycle. Event association does
not create lifecycle authority.

The following cannot implicitly create or split a lifecycle:

- execution events;
- partial fills;
- accounting events;
- settlement events;
- corrections;
- observations;
- T02 dataset grouping;
- T06 readiness grouping;
- retrieval ordering; or
- database ordering.

A split cannot be inferred from timestamps, prices, amounts, execution count,
caller preference, database order, or implementation behavior.

### 4.5 Lifecycle identity seed

The lifecycle identity seed is:

```text
Canonical Economic Subject Identity
+
P06 DecisionIntent Identity
```

P08-T01, T02, and T06 identities are linkage or provenance only. They are not
part of the lifecycle identity seed.

Lifecycle identity remains stable across:

- T02 dataset snapshots;
- deterministic recomputation;
- ordering changes;
- replay; and
- T06 recomputation,

unless Authority A supplies an authoritative lifecycle identity fact that
changes the mapping.

## 5. T07 Lifecycle Validation

Before canonical-result selection, T07 must validate that:

1. the lifecycle identity is present;
2. the canonical economic subject identity is present;
3. the P06 DecisionIntent identity is present;
4. the lifecycle-to-P06 relationship satisfies the V1 cardinality rule;
5. any multiple-lifecycle mapping has an authoritative Lifecycle Split Fact;
6. the split fact identifies the resulting lifecycle identities;
7. lifecycle equivalence and conflict information is authoritative;
8. T01/T02/T06 records are used only for their declared linkage/provenance
   purposes; and
9. the supplied lifecycle identity is consistent with the candidate result.

T07 validates the supplied mapping. It does not create, split, merge, or
redefine the lifecycle.

An ambiguous, conflicting, missing, or unmappable relationship fails closed.

## 6. Result Identity Model

The result identity model is:

```text
Semantic Result Identity Seed
        ↓
Canonical Result Representation
        ↓
SHA-256 result_digest
```

### 6.1 Semantic identity

Semantic identity is the stable identity of the result as a domain object. It
is derived only from stable semantic identity fields that have been proven to
define the result.

The identity seed must not include:

- its own result digest;
- an outgoing successor edge;
- database insertion order;
- retrieval order;
- wall-clock time;
- caller preference;
- mutable status caused only by later lineage; or
- vague or mutable provenance that has not been proven identity-defining.

The exact field set for the semantic result identity seed is a
**specification-level governance dependency** where the existing T07 contract
does not already define it. T07 must not invent fields to close that gap.

### 6.2 Canonical representation

The canonical result representation is the complete deterministic
representation of the validated T07 result. It may contain:

- semantic result fields;
- validated lifecycle identity;
- validated upstream G2/G3/G4 references;
- required provenance;
- contract and evaluator versions;
- correction or supersession references as immutable supplied facts; and
- other fields explicitly authorized by the T07 contract.

An outgoing successor edge is not part of a predecessor’s representation merely
because the successor exists.

### 6.3 Integrity digest

`result_digest` is the SHA-256 digest of the canonical result representation.

The digest provides integrity and content identification for the representation
being hashed. It does not define the semantic identity seed that produced that
representation.

The digest must not be self-referential.

## 7. Canonicalization and SHA-256 Requirements

Result and lineage representations must use deterministic canonicalization.

The canonicalization requirements are:

- canonical UTF-8 encoding;
- deterministic JSON or the existing T07 canonical serialization format;
- sorted object keys;
- explicit representation of nullable values where permitted;
- canonical enum string values;
- canonical UTC timestamps;
- deterministic decimal/scaled-decimal values inherited from G3;
- negative zero normalized to zero;
- rejection of NaN, infinity, overflow, underflow, and precision loss;
- deterministic collection ordering based on canonical identity or digest; and
- no dependency on language-specific object ordering.

The exact field ordering, nullable-field policy, and canonical serialization
schema for newly introduced lifecycle and lineage records are
**specification-level governance dependencies** and must be locked before
implementation.

SHA-256 is applied to the complete canonical representation after
canonicalization. The digest field itself is excluded from the representation
being hashed.

For lineage:

```text
Lineage Fact
        ↓
Lineage Edge Identity
        ↓
Lineage Edge Digest
```

The lineage edge digest covers the canonical lineage-edge representation and
does not include itself.

## 8. Correction Lineage

A correction lineage fact states that a successor corrects an error or defect
in a predecessor result.

A correction must:

- be supplied by Authority B;
- identify the lifecycle;
- identify the predecessor result;
- identify the successor result;
- identify the correction edge;
- preserve authoritative evidence or fact provenance;
- preserve the applicable lineage policy/version; and
- be independently digest-verifiable.

The correction edge does not mutate the predecessor result.

## 9. Supersession Lineage

A supersession lineage fact states that a successor replaces a predecessor as
the current representative without necessarily asserting that the predecessor
was erroneous.

A supersession must:

- be supplied by Authority B;
- identify the lifecycle;
- identify the predecessor result;
- identify the successor result;
- identify the supersession edge;
- preserve authoritative evidence or fact provenance;
- preserve the applicable lineage policy/version; and
- be independently digest-verifiable.

The supersession edge does not mutate the predecessor result.

There is no precedence between correction and supersession.

Repeated and mixed transitions are valid only when every edge is independently
supported by an authoritative lineage fact.

## 10. Lineage Edge Identity and Digest

A lineage edge is a separate immutable fact that may contain the following
semantic components:

- lifecycle identity;
- predecessor result identity;
- successor result identity;
- edge type;
- lineage authority identity;
- fact or evidence identity;
- lineage policy/version; and
- required provenance.

The exact serialized field names and types are a
**specification-level governance dependency** unless already supplied by the
existing upstream contract.

The edge identity is derived from the stable semantic identity of the edge.
The edge digest is the SHA-256 digest of its canonical representation.

Neither the predecessor result nor the successor result is mutated by creation
of the edge.

## 11. Successor Cardinality and Lineage Conflicts

The normative successor rule is:

> At most one authoritative successor edge may exist for a result.

Two authoritative successor edges from one predecessor create a branching
conflict. T07 must fail closed and must not select a branch.

The following are invalid:

- multiple authoritative successors from one predecessor;
- a successor that references a missing predecessor;
- a declared successor that cannot be resolved;
- a predecessor that cannot be resolved;
- an edge whose fact authority is invalid;
- contradictory lineage facts for the same edge; and
- a lineage graph containing a cycle.

Conflicting lineage facts must not be resolved by timestamp, insertion order,
edge type preference, result magnitude, or caller preference.

## 12. Canonical-Head Selection

T07 selects the current canonical representative from the validated lineage
graph after lifecycle and lineage validation.

The normative rule is:

> Exactly one structurally valid terminal representative is the current
> canonical T07 representative.

A result is terminal when it has no declared successor edge.

The selection rules are:

| Condition | T07 outcome |
|---|---|
| No successor declared | Terminal candidate |
| Declared successor is missing | `MISSING_SUCCESSOR` |
| Declared lineage is invalid | `INVALID_LINEAGE` |
| More than one valid terminal head exists | Canonical selection ambiguity; fail closed |
| More than one authoritative successor edge exists | Branching conflict; fail closed |
| A cycle exists | Cycle failure; fail closed |
| Lineage cannot be resolved | No canonical result |
| Exactly one structurally valid terminal exists | Current canonical representative |

Selection must not depend on:

- database insertion order;
- retrieval order;
- wall-clock time;
- caller preference;
- result magnitude;
- economic performance;
- analytical cutoff; or
- future AEA rules.

## 13. INVALID_INPUT and Result-State Boundary

T07 must distinguish the following states.

### 13.1 No result

No structurally valid T07 result exists. This is not a representative and
does not count toward any coverage category.

### 13.2 Canonical `INVALID_INPUT` representative

A structurally valid T07 record may be the current canonical terminal
representative while carrying `INVALID_INPUT`.

It:

- may count toward structural lifecycle coverage;
- may count toward canonical representative coverage;
- is not a valid economic result; and
- must not count toward economic-outcome coverage.

### 13.3 Unresolved canonical state

An unresolved canonical state exists when the lineage graph cannot establish
the required single terminal representative because of missing, invalid,
ambiguous, branching, or cyclic lineage.

It:

- is not a result;
- is not a canonical representative;
- does not count toward structural coverage;
- does not count toward representative coverage; and
- does not count toward economic coverage.

### 13.4 Valid economic result

A valid economic result is a resolved, structurally valid, admissible T07
representative whose economic semantics have been supplied and validated from
the authoritative upstream G2/G3/G4 boundaries.

T07 does not turn `INVALID_INPUT`, unresolved evidence, or unresolved lineage
into a valid economic result.

## 14. Coverage Boundary

The following coverage concepts are independent:

1. **Structural lifecycle coverage** — whether the expected lifecycle mapping
   is structurally represented.
2. **Canonical representative coverage** — whether a resolved canonical T07
   representative exists.
3. **Economic outcome coverage** — whether a valid economic T07 result exists.

An `INVALID_INPUT` representative may contribute to the first two categories
when structurally valid, but never to economic-outcome coverage.

An unresolved canonical state contributes to none of the categories.

CPA may later project expected lifecycle population and structural coverage.
CPA must not choose the canonical result. Future economic metrics must exclude
`INVALID_INPUT`.

## 15. Current Canonical vs Future Analytical As-Of Selection

The current canonical T07 representative is selected from the complete
validated lineage graph without an analytical cutoff.

Future AEA analytical admissibility may later select an as-of representative
for a specific analytical cutoff. That future selection:

- is distinct from current T07 canonical selection;
- must not mutate current T07 results;
- must not redefine T07 lineage;
- must not redefine economic meaning; and
- must not feed backward into T07 canonical-head selection.

The current canonical representative is therefore cutoff-independent.

## 16. Provenance Requirements

T07 must preserve and validate provenance for:

- P06 DecisionIntent identity and digest;
- canonical economic subject identity;
- lifecycle identity and equivalence;
- any Lifecycle Split Fact;
- P08-T01 observation linkage;
- T02 dataset linkage and cutoff where present;
- T06 readiness linkage where present;
- G2 result identity, policy/version, and digest;
- G3 result identity, policy/version, and digest;
- G4 result identity, policy/version, and digest;
- result contract and evaluator versions;
- lineage fact identity;
- lineage authority identity;
- predecessor and successor result identities;
- evidence or fact identity; and
- lineage policy/version.

T07 must not infer, repair, substitute, or silently discard missing or
contradictory provenance.

Provenance may be represented in the canonical result or lineage
representation. Provenance is not part of semantic identity unless explicitly
proven to be identity-defining.

## 17. Deterministic Replay

For equivalent validated authoritative inputs, T07 must produce equivalent:

- lifecycle validation outcomes;
- candidate result identities;
- canonical result representations;
- result digests;
- lineage validation outcomes;
- lineage edge identities;
- lineage edge digests;
- canonical-head selections; and
- failure states.

T07 must not depend on:

- wall-clock time;
- randomness;
- local timezone;
- insertion order;
- retrieval order;
- database state;
- network state;
- provider state;
- filesystem state;
- hidden configuration;
- process identity; or
- memory address.

## 18. Failure Taxonomy

The extension recognizes the following semantic failure categories:

| Failure category | Meaning |
|---|---|
| `INVALID_LIFECYCLE_MAPPING` | Lifecycle mapping is missing, ambiguous, conflicting, or violates cardinality |
| `MISSING_LIFECYCLE_SPLIT_FACT` | Multiple lifecycles are claimed for one P06 without the required authoritative split fact |
| `MISSING_SUCCESSOR` | A declared successor cannot be resolved |
| `MISSING_PREDECESSOR` | A declared predecessor cannot be resolved |
| `INVALID_LINEAGE` | A lineage fact or edge fails structural or authority validation |
| `LINEAGE_BRANCH_CONFLICT` | More than one authoritative successor edge exists for one result |
| `LINEAGE_CYCLE` | The lineage graph contains a cycle |
| `UNRESOLVED_CANONICAL_STATE` | Canonical-head selection cannot establish exactly one valid terminal |
| `DIGEST_FAILURE` | A result or lineage digest is invalid, mismatched, or non-canonical |
| `PROVENANCE_LINKAGE_FAILURE` | Required provenance or authority linkage is missing or contradictory |
| `CONFLICTING_INPUT` | Authoritative inputs disagree and no permitted resolution exists |
| `INVALID_INPUT` | The supplied T07 input cannot produce a valid economic result |

The exact public enum spelling, precedence among failure reporting fields, and
mapping to the existing T07 failure vocabulary are
**specification-level governance dependencies** where the existing contract
has not already locked them. No implementation may silently collapse distinct
failure categories.

## 19. Formal Invariants

The following invariants are normative.

### I-01 — Lifecycle anchor

Every T07 lifecycle is anchored by a P06 DecisionIntent and a canonical
economic subject.

### I-02 — Lifecycle cardinality

Every lifecycle maps to exactly one P06 DecisionIntent. A P06 maps to exactly
one lifecycle unless Authority A supplies a valid Lifecycle Split Fact.

### I-03 — Event association

Event grouping cannot create, split, or redefine lifecycle identity.

### I-04 — Lifecycle identity stability

T02, T06, observation identity, replay order, retrieval order, and dataset
snapshot identity cannot alter lifecycle identity.

### I-05 — Result identity acyclicity

The result digest is not an input to the identity seed that produces the
canonical result representation.

### I-06 — Lineage separation

A lineage edge is not part of either result’s canonical representation merely
because the edge exists.

### I-07 — Historical immutability

Creating a successor cannot mutate the predecessor result or predecessor
digest.

### I-08 — Successor cardinality

At most one authoritative successor edge may exist for a result.

### I-09 — No branch selection

A branching lineage graph must fail closed and cannot be resolved by preference.

### I-10 — No cycles

A cyclic lineage graph must fail closed.

### I-11 — Reference completeness

Missing declared predecessor or successor references must fail closed.

### I-12 — Canonical-head uniqueness

Exactly one structurally valid terminal representative is required for a
current canonical T07 result.

### I-13 — Invalid-result separation

`INVALID_INPUT` may be a canonical structural representative but is not a
valid economic result and is not economic-outcome coverage.

### I-14 — Unresolved-state separation

An unresolved canonical state is not a result and does not count as coverage.

### I-15 — Cutoff independence

Current canonical T07 selection cannot depend on future AEA analytical cutoff.

### I-16 — Ownership preservation

T07 validates and assembles supplied semantics but does not invent upstream
lifecycle, lineage, realization, accounting, or classification facts.

### I-17 — Deterministic replay

Equivalent authoritative inputs produce equivalent validation, representation,
digest, lineage, and canonical-head outcomes.

## 20. Dependency Graph

```text
Canonical Economic Subject / Lifecycle Identity Authority
        ↓
Canonical Economic Subject Identity
        ↓
Lifecycle Identity / Equivalence / Split Validation
        ↓
T07 Candidate Results
```

Parallel lineage path:

```text
Correction / Supersession Lineage Fact Authority
        ↓
Correction / Supersession Facts
        ↓
T07 Lineage Validation
        ↓
T07 Canonical Selection
        ↓
Current Canonical T07 Representative
        ↓
AEA
        ↓
Future Analytical Snapshot
        ↓
Future Performance / Economic Analysis
```

Parallel population path:

```text
T02 Observation Population
        +
Lifecycle Identity / Equivalence
        ↓
CPA
        ↓
Expected Lifecycle Population
        +
Structural T07 Coverage
```

The dependency constraints are:

```text
CPA MUST NOT create or split lifecycles.
CPA MUST NOT select the canonical T07 result.
AEA MUST NOT feed lineage selection.
AEA MUST NOT redefine T07 economic meaning.
Snapshot MUST NOT create economic semantics.
```

## 21. Explicit Non-Responsibilities

This extension does not own or authorize:

- lifecycle facts supplied by Authority A;
- lineage facts supplied by Authority B;
- G2 realization eligibility;
- G3 accounting or economic calculation;
- G4 classification;
- raw evidence collection;
- event-provider truth;
- valuation;
- P&L;
- ROI;
- performance aggregation;
- strategy scoring;
- model training or updates;
- execution;
- capital authorization;
- wallet access;
- signing or broadcast;
- external I/O;
- database or queue access;
- persistence requirements not already authorized;
- CPA implementation;
- AEA implementation;
- Snapshot implementation; or
- P08-T08.

## 22. Specification-Level Governance Dependencies

The following details must be resolved in the eventual implementation-ready
specification or contract amendment without inventing semantics:

1. exact serialized fields and types for `LifecycleIdentity`;
2. exact serialized fields and types for `LifecycleSplitFact`;
3. exact semantic field set for the result identity seed;
4. exact serialized fields and types for `LineageFact`;
5. exact serialized fields and types for `LineageEdgeIdentity`;
6. exact canonical field ordering and nullable-field policy for new records;
7. exact public enum spellings and failure-reporting structure for new failure
   categories; and
8. exact adapter mapping between the extension and the existing closed T07
   input/output contracts.

These are specification dependencies, not permission to infer fields from
implementation convenience.

## 23. Status and Next Audit

### Specification status

**P08-T07 Canonical Result Authority Extension specification draft complete.**

The draft reflects the explicitly approved governance baseline and preserves
the existing closed P08-T07 implementation boundary.

### Implementation status

**Implementation not authorized.**

No source code, tests, runtime behavior, Authority A, Authority B, CPA, AEA,
Snapshot, or P08-T08 was created or modified by this specification.

### Unresolved specification dependencies

The field-level, serialization-level, and exact public failure-vocabulary
items listed in Section 22 remain specification dependencies. They are not
unresolved semantic governance decisions and must not be filled by inference.

### Exact next audit required

Before any implementation authorization, perform a dedicated P08-T07
Canonical Result Authority Extension specification audit covering:

1. lifecycle cardinality and Lifecycle Split Fact validation;
2. Authority A and Authority B ownership separation;
3. result identity non-circularity;
4. immutable lineage and successor cardinality;
5. branching, cycle, missing-reference, and conflict failures;
6. canonical-head determinism;
7. `INVALID_INPUT` and coverage separation;
8. current canonical versus future analytical cutoff independence;
9. provenance and canonicalization completeness; and
10. preservation of all existing T07, G2, G3, and G4 ownership boundaries.

No implementation authorization is implied by this draft.

P08-T07 CANONICAL RESULT AUTHORITY EXTENSION SPECIFICATION DRAFT COMPLETE — IMPLEMENTATION NOT AUTHORIZED