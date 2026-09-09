# P08 — Authority B Implementation-Readiness Audit

**Status:** COMPLETE / CLOSED / AUDITED PASS  
**Phase:** P08 — Outcome Learning  
**Authority:** Authority B — Correction / Supersession Lineage Facts  
**Audit date:** 2026-09-09  
**Audit type:** Documentation-only implementation-readiness review

## 1. Audit scope and authorization boundary

This audit reviews whether the completed Authority B
implementation-readiness specification is sufficiently exact to authorize a
separate, future, limited implementation task.

This audit does not:

- create Authority B source code or tests;
- modify the closed P08-T07 implementation or specification;
- modify the Authority B implementation-readiness specification;
- add runtime, API, dependency, persistence, migration, provider, wallet,
  signing, or execution behavior;
- start P08-T08 or P09; or
- authorize Authority B implementation by itself.

The audit uses `PASS`, `FAIL`, and `BLOCKED` as follows:

| Result | Meaning |
|---|---|
| `PASS` | The readiness requirement is explicit, deterministic, bounded, and implementation-ready for a separately authorized task. |
| `FAIL` | The readiness specification contradicts an approved boundary or permits behavior outside the requested scope. |
| `BLOCKED` | A required semantic or compatibility decision remains unresolved. |

## 2. Documents reviewed

The documents required by the review instruction were read in the specified
order:

1. `REPLIT_RULES.md`;
2. `PROJECT_STATE.md`;
3. `docs/P08-AUTHORITY-B-FORMAL-CLOSURE-AUDIT.md`;
4. `docs/P08-AUTHORITY-B-SPECIFICATION-AUDIT.md`;
5. `docs/P08-AUTHORITY-B-IMPLEMENTATION-READINESS-SPECIFICATION.md`;
6. `docs/P08-T07-SPECIFICATION.md`; and
7. `docs/P08-T07-CANONICAL-RESULT-AUTHORITY-EXTENSION-SPECIFICATION.md`.

The review also checked the current repository state for the required
documentation-only change boundary.

## 3. Criterion-by-criterion findings

### Criterion 1 — Strictly lineage-only

**Result: PASS**

The readiness specification limits the future implementation to:

- validation of explicitly supplied immutable `LineageFact` values;
- canonicalization and digest/identity derivation for Authority B lineage
  objects and snapshots;
- duplicate and conflict comparison against an explicitly supplied snapshot;
- lifecycle-scoped lineage graph validation;
- deterministic detection of lineage failures; and
- production of the existing T07 correction or supersession lineage projection.

It explicitly prohibits inference, repair, substitution, merge behavior,
economic calculation, classification, canonical-head authority, and any
authority outside the lineage relationship. The structural terminal candidate
is expressly bounded as an intermediate result for T07 validation, not as an
independent Authority B canonical-head decision.

### Criterion 2 — Minimal, non-overlapping source and test paths

**Result: PASS**

The readiness specification proposes exactly these future paths:

| Future path | Permitted responsibility |
|---|---|
| `core/learning/authority_b_lineage.py` | Pure Authority B domain types, canonicalization, identity/digest derivation, snapshot comparison, graph validation, failure precedence, and the exact lineage projection. |
| `tests/test_authority_b_lineage.py` | Targeted tests for the Authority B contract and prohibited dependency boundary. |

The proposed module is explicitly independent from API, service, worker,
database, ORM, repository, migration, cache, filesystem, provider, wallet,
signer, network, T07 internals, P09, and execution layers. The readiness
specification also prohibits changes to existing T07, Authority A, manifest,
lockfile, migration, and runtime-configuration files. Any later integration
wiring requires separate authorization.

These paths are minimal for a pure isolated boundary and do not overlap the
existing runtime, API, persistence, provider, or T07 ownership.

### Criterion 3 — Explicit, immutable, deterministic inputs

**Result: PASS**

The readiness specification requires all inputs to be explicit, immutable,
complete for the requested operation, and validated before derived output is
accepted. It explicitly defines:

- the complete required `LineageFact` fields;
- the fixed provenance stages and link fields;
- the immutable authoritative comparison snapshot;
- the complete lifecycle-scoped result-identity set;
- the complete candidate lineage-fact set;
- the target lifecycle identity; and
- the required contract and policy versions.

It prohibits wall-clock and process time, timezone, randomness, database,
filesystem, insertion/retrieval order, provider, network, wallet, external
API, hidden configuration, process identity, memory address, and caller
preference dependencies. Missing or ambiguous values cannot be reconstructed
from ambient state.

### Criterion 4 — Canonical JSON, normalization, digest, and duplicate readiness

**Result: PASS**

The readiness specification reproduces the locked Authority B serialization
profile without introducing an alternate representation:

- UTF-8 JSON without a byte-order mark;
- NFC before JSON escaping;
- rejection of unpaired surrogates;
- no NFKC, NFD, case folding, trimming, locale, or other normalization;
- exact quote and reverse-solidus escaping;
- never-escaped solidus;
- fixed named control escapes and lowercase `\u00xx` for other controls;
- direct non-ASCII UTF-8 output;
- Unicode code-point key ordering;
- semantic array ordering with no implicit sorting;
- only comma and colon separators;
- lowercase boolean and null tokens;
- no semantic nulls or numeric JSON tokens in Authority B objects;
- exact canonical UTF-8 digest bytes;
- fixed six-field identity projection order; and
- digest self-reference exclusion.

The candidate identity is computed before snapshot consultation. Duplicate
comparison uses only the explicitly supplied immutable snapshot. The
specification distinguishes byte-identical `EXACT_DUPLICATE` from
same-identity byte differences, which are `CONFLICTING_DUPLICATE` and fail
closed. Snapshot context does not participate in fact or edge identity.

No ambiguity or missing requirement remains in the reviewed
canonicalization, digest-input, null, or duplicate semantics.

### Criterion 5 — Deterministic, fail-closed graph outcomes

**Result: PASS**

The readiness specification defines deterministic handling for every required
graph case:

| Required case | Deterministic readiness outcome |
|---|---|
| Valid linear lineage | Accepted when every edge, endpoint, provenance chain, digest, and graph invariant is valid; a unique structural terminal candidate may be returned for T07 validation. |
| Correction | Accepted only as an explicit `correction` edge mapped to `correction_lineage`. |
| Supersession | Accepted only as an explicit `supersession` edge mapped to `supersession_lineage`. |
| Duplicate | Byte-identical matching fact is `EXACT_DUPLICATE`, idempotently accepted, and the existing projection is reused. |
| Conflicting duplicate | Same identity with any canonical-byte difference is `CONFLICTING_DUPLICATE`; fail closed with no last-write-wins. |
| Branch | More than one direct authoritative successor fails closed as `LINEAGE_BRANCH_CONFLICT`; no branch is selected. |
| Cycle | Fails closed as `LINEAGE_CYCLE`. |
| Self-reference | Fails closed as `LINEAGE_SELF_REFERENCE`. |
| Orphan | Unresolved or non-member endpoint fails closed; no endpoint is inferred or repaired. |
| Missing endpoint | Missing predecessor or successor fails closed as `MISSING_ENDPOINT`. |
| Cross-lifecycle reference | Fails closed as `CROSS_LIFECYCLE_REFERENCE`; the snapshot cannot override Authority A lifecycle identity. |
| Contradiction | Contradictory facts for the same edge fail closed as `CONTRADICTORY_LINEAGE`. |
| Merge/convergence | Explicitly unsupported and always fails closed as `MERGE_UNSUPPORTED`, represented normatively as `MERGE / CONVERGENCE UNSUPPORTED — FAIL CLOSED`. |

The fixed first-applicable failure precedence is independent of collection
order, timestamps, or runtime behavior. Valid multi-hop chains are supported,
while branching, cycles, self-reference, unresolved endpoints, cross-lifecycle
references, contradictions, and convergence cannot be repaired or preferred.

### Criterion 6 — Complete Authority B → T07 mapping without redefining T07

**Result: PASS**

The readiness specification maps:

- `correction` to the existing T07
  `EconomicOutcomeInterpretationInput.correction_lineage` and corresponding
  result field;
- `supersession` to the existing T07
  `EconomicOutcomeInterpretationInput.supersession_lineage` and corresponding
  result field;
- every Authority B identity, version, endpoint, type, authority,
  provenance, and edge digest field to the lineage member projection; and
- every Authority B failure to an existing T07 `INVALID_INPUT` and
  `failure_reason` behavior.

It explicitly prohibits populating or redefining T07's own contract version,
evaluator version, status, failure reason, G2/G3/G4 fields, result digest, and
classification digest. T07 remains responsible for independent validation,
graph-conflict detection, and canonical-head selection. No new T07 failure
vocabulary or semantic transformation is introduced.

### Criterion 7 — Sufficient test plan

**Result: PASS**

The future test plan covers the required proof obligations:

- canonical-byte equivalence, NFC, invalid surrogates, escaping, key and array
  ordering, null policy, numeric rejection, digest input, and self-reference;
- replay across processing order, collection order, timezone, clock,
  randomness, and ambient-state changes;
- explicit snapshot validation, canonical ordering, identity/digest checks,
  exact duplicates, conflicting duplicates, multiple matches, and
  no-last-write-wins behavior;
- valid linear and mixed multi-hop chains;
- branch, merge/convergence, cycle, self-reference, orphan, missing endpoint,
  cross-lifecycle, contradiction, provenance, digest, ambiguous-terminal, and
  precedence cases;
- correction and supersession destinations;
- preservation of every mapped field;
- invalid projection omission;
- every Authority B failure mapping;
- idempotent projection reuse;
- T07 non-redefinition and retained T07 authority;
- immutability of facts, edges, snapshots, identities, and endpoints; and
- absence of database, filesystem, provider, network, wallet, signer,
  execution, persistence, clock, randomness, G2/G3/G4, and P09 dependencies.

This is sufficient for a separately authorized implementation task to prove
determinism, replay, immutability, canonical-byte behavior, mapping
completeness, and prohibited dependency absence.

### Criterion 8 — Explicit prohibitions for prohibited authority

**Result: PASS**

The readiness specification explicitly prohibits:

- G2 realization and settlement;
- G3 accounting, P&L, ROI, and economic calculation;
- G4 `WIN`, `LOSS`, and `BREAKEVEN` classification;
- valuation and performance metrics;
- wallet, custody, private keys, signing, broadcast, and execution;
- provider, RPC, DEX, exchange, network, and external API access;
- database, persistence, migrations, caches, queues, and filesystem authority;
- Risk Governor and capital authorization;
- model training, AI/ML, strategy updates, and learning;
- T07 redesign or modification;
- Authority A modification;
- P08-T08; and
- P09 behavior.

The prohibition is explicit even where lineage evidence, a structural terminal
candidate, or a T07 projection exists. Evidence presence cannot grant
prohibited authority implicitly.

### Criterion 9 — No accidental implementation or P09 authorization

**Result: PASS**

The readiness specification repeatedly states that:

- Authority B implementation remains `NOT AUTHORIZED`;
- a separate explicit implementation authorization is required;
- no files in the proposed future file set are created by the readiness work;
- only specification or governance documents may be changed before separate
  approval;
- T07 remains closed and must not be redesigned; and
- P09 remains `NOT AUTHORIZED`.

The authorization gate describes conditions for a later decision; it does not
grant that decision. The readiness document therefore does not accidentally
authorize implementation or P09.

## 4. Ambiguity and missing-requirement review

**Finding: No blocking ambiguity or missing requirement.**

The reviewed readiness specification is sufficiently explicit for the limited
future implementation scope. In particular, it resolves the previously
identified readiness blockers for:

1. canonical JSON byte behavior;
2. deterministic duplicate-comparison context; and
3. exact Authority B → T07 field and failure mapping.

The following are not gaps in this readiness specification because they are
explicitly outside its permitted implementation scope:

- changes to the closed T07 implementation or its integration wiring;
- lifecycle and result-identity semantics owned by the broader T07 extension;
- persistence or service/API integration;
- provider, wallet, signing, execution, or economic behavior; and
- P09 or later-phase behavior.

Any such work requires its own specification and explicit authorization. This
does not prevent a separate limited Authority B implementation authorization
from being requested for the two isolated paths listed below.

## 5. Exact future implementation scope permitted if separately authorized

Only if a later, separate implementation authorization is granted, the
permitted scope is exactly:

1. implement the pure, provider-neutral Authority B lineage boundary described
   in `core/learning/authority_b_lineage.py`;
2. implement the corresponding targeted contract tests in
   `tests/test_authority_b_lineage.py`;
3. accept only explicit immutable values and the explicit comparison snapshot;
4. implement the locked canonicalization, identity, digest, duplicate, graph,
   failure-precedence, and T07-lineage-projection rules; and
5. preserve all prohibited-dependency and non-overlap restrictions in this
   audit.

No other source, test, runtime, API, persistence, migration, dependency,
provider, wallet, signer, execution, T07, Authority A, P08-T08, or P09 change
is permitted under that limited scope.

## 6. Exact allowed future file paths

The exact proposed paths are:

```text
core/learning/authority_b_lineage.py
tests/test_authority_b_lineage.py
```

No other path is authorized by this readiness audit. These paths are proposed
for a future task only; they were not created or modified by this audit.

## 7. Final verdict

All nine requested criteria pass. The Authority B
implementation-readiness specification is sufficient to support a separate,
future, limited implementation authorization request.

```text
AUTHORITY B IMPLEMENTATION-READINESS SPECIFICATION
    = COMPLETE / CLOSED / AUDITED PASS

AUTHORITY B IMPLEMENTATION
    = NOT AUTHORIZED BY THIS AUDIT ALONE

SEPARATE LIMITED IMPLEMENTATION AUTHORIZATION
    = REQUIRED BEFORE CODE MAY BE CREATED

P09
    = NOT AUTHORIZED
```

No source code, tests, runtime, API, dependency, persistence, migration,
provider, wallet, signing, or execution behavior was added. P08-T07 was not
modified or redesigned.
