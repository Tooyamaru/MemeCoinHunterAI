# P08 — Authority B Specification and Audit

**Status:** BOUNDED SPECIFICATION / AUDIT COMPLETE — IMPLEMENTATION NOT AUTHORIZED
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

Authority B is sufficiently established as a **bounded semantic authority**,
but it is not implementation-ready.

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
| Lineage fact identity | `derived` from the locked semantic fact identity | Must be stable and distinct from result identity and result digest. Exact seed fields remain unresolved. |
| Lineage policy/version | `authoritative` governance input | Must be preserved in the fact and edge representation. Exact version vocabulary is unresolved. |
| Fact/evidence identity and provenance | `authoritative` support | Must be preserved and independently verifiable. Missing or contradictory provenance fails closed. |
| Explicit fact/evidence timestamps | `contextual` provenance | May be carried only under an approved timestamp contract. They must not select a successor or resolve a conflict by age. |
| Canonical lineage-edge representation | `derived` representation | Construct only from the locked semantic fact and authorized references. Exact fields, ordering, and null policy remain unresolved. |
| Lineage-edge digest | `derived` integrity value | SHA-256 of the complete canonical edge representation, excluding the digest itself. |
| P06 → P07 → P08 provenance chain | `contextual` required linkage | Preserve for downstream verification; it does not become a new lineage authority. |
| G2/G3/G4 economic results | `prohibited` as B semantics | B does not calculate, validate, replace, or interpret realization, accounting, or classification. T07 consumes separately governed G2/G3/G4 outputs. |
| Wallet, account, custody, signing, settlement, provider, RPC, DEX, or network state | `prohibited` | No such state is an Authority B input. |
| Wall-clock or process state | `prohibited` | Must not affect fact identity, canonical representation, conflict handling, or replay. |

### 4.1 Missing or conflicting inputs

Authority B must not reconstruct missing inputs from identifiers, timestamps,
database order, result magnitude, or caller preference. A missing endpoint,
ambiguous lifecycle, invalid authority, contradictory fact, or unresolved
provenance chain remains unresolved and fails closed for downstream use.

The repository has not locked the exact public failure enum spelling or
precedence among failure-reporting fields. Those details are
`UNRESOLVED`, not permission to collapse distinct failures.

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

The exact serialized field names and types for `LineageFact`,
`LineageEdgeIdentity`, and the canonical edge representation are
`UNRESOLVED`. They must be separately locked before implementation readiness.

### 5.2 Immutability and correction semantics

Creating a correction or supersession fact must not mutate either the
predecessor or successor result, its identity, or its digest.

The fact is read-only after creation. A later correction or supersession is a
new fact and a new successor relationship; it is not an in-place edit.

The repository evidence supports the following structural constraint:

> At most one authoritative successor edge may exist for a result.

Multiple authoritative successors from one predecessor create a branching
conflict. T07 must fail closed and must not select a branch.

### 5.3 Canonical representation and digest

The representation must use the repository’s deterministic governance
requirements:

- canonical UTF-8;
- deterministic JSON or the approved existing canonical format;
- sorted object keys;
- canonical enum strings;
- canonical UTC timestamps where timestamps are authorized;
- deterministic collection ordering by canonical identity or digest;
- no language-specific object ordering; and
- SHA-256 over the complete canonical representation, excluding the digest
  field itself.

The exact field ordering, nullable-field policy, and semantic identity seed are
`UNRESOLVED`. A digest is an integrity value; it is not automatically semantic
identity and must not participate in a circular identity/digest dependency.

## 6. Authority B Boundary

### 6.1 Authority B may establish

Authority B may:

1. assert that a named successor corrects a named predecessor;
2. assert that a named successor supersedes a named predecessor;
3. bind the relationship to one established lifecycle;
4. preserve predecessor and successor identities without mutation;
5. preserve the fact’s authority, evidence, provenance, and policy/version;
6. produce deterministic lineage-fact and lineage-edge identities once their
   semantic and serialized contracts are locked;
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

The exact policy for accepting an exact duplicate representation versus
reporting it as a duplicate is `UNRESOLVED`. Until that policy is locked, no
ambiguous duplicate may be treated as a new authoritative fact.

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

Authority B may consume an explicitly supplied timestamp only when it is part
of an approved fact/evidence provenance contract. The timestamp is data
belonging to that fact or evidence; it is not an Authority B clock.

The following semantics are not currently locked for Authority B and therefore
remain `UNRESOLVED`:

- event time;
- observation time;
- reference time;
- effective time of a correction;
- effective time of a supersession;
- correction time;
- settlement time; and
- any as-of/cutoff representation for lineage facts.

Settlement time is not an Authority B authority. A settlement timestamp cannot
make a result realized.

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

The canonicalization and digest rules are sufficiently established
semantically. The exact field-level serialization and semantic identity seed
remain `UNRESOLVED` and block implementation readiness.

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
- At most one authoritative successor edge may exist for a result.
- Branches, cycles, missing references, contradictory facts, and invalid
  provenance fail closed.
- SHA-256 protects a deterministic canonical edge representation and is not
  semantic identity.
- T07, not B, selects the canonical head per lifecycle.
- B does not own G2, G3, G4, G5, custody, signing, settlement, or execution.

### 14.2 Unresolved

- Exact serialized fields and types for `LineageFact`.
- Exact serialized fields and types for `LineageEdgeIdentity`.
- Exact semantic identity seed for lineage facts and edges.
- Exact field ordering and nullable-field policy.
- Exact policy/version vocabulary.
- Exact public failure enum spellings and precedence.
- Exact mapping into the closed T07 input/output contract.
- Exact duplicate handling policy.
- Exact timestamp fields and effective-time semantics.

### 14.3 Blocked

- Implementation-ready Authority B contract.
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

The supplied checkpoint identifies Authority A as closed and PASS. The current
Authority A document also contains an internal status of
`SPECIFICATION DRAFT — IMPLEMENTATION NOT AUTHORIZED` and says formal audit is
required.

This is a governance-document status inconsistency. It does not change the
Authority A semantic boundary used by this audit, and it does not authorize B
implementation. Before any implementation-readiness decision, the project
governance record should reconcile the checkpoint status and the Authority A
document status through an explicit governance update. No such update is made
by this work order.

## 16. Audit Conclusion and Next Governance Gate

Authority B is **SEMANTICALLY BOUNDED / SPECIFICATION-LEVEL BLOCKED**.

The repository establishes a precise non-economic boundary: B owns immutable
correction/supersession lineage facts and their provenance, while T07 validates
them and selects a canonical head. The repository does not establish the
field-level contract required for implementation readiness.

The next governance gate is a dedicated Authority B implementation-readiness
decision that must, at minimum, lock:

1. the semantic identity seed;
2. exact serialized fields and types;
3. canonical field ordering and nullable policy;
4. timestamp and effective-time semantics;
5. duplicate and conflict behavior;
6. public failure vocabulary and precedence;
7. adapter mapping into the closed T07 contract; and
8. reconciliation of the Authority A status inconsistency.

That gate must remain separate from G1–G5 economic authority decisions.

## 17. Implementation Status

**AUTHORITY B IMPLEMENTATION = NOT AUTHORIZED**

This document does not authorize source changes, tests, persistence, runtime
behavior, wallet access, provider selection, economic calculation, P08-T08,
P09, or any later phase.