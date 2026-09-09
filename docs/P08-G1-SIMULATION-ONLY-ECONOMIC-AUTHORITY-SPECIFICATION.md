# P08 — G1 Simulation-Only Economic Authority Specification

**Status:** SPECIFICATION COMPLETE / AWAITING FORMAL AUDIT  
**Phase:** P08 — Outcome Learning  
**Boundary:** G1 — Simulation-Only Economic Authority  
**Contract version:** `p08-g1-simulation-only-v1`  
**Evaluator version:** `p08-g1-simulation-only-economic-authority-v1`  
**Nature:** Immutable, deterministic, provider-neutral, read-only, simulation-only

## 1. Purpose and authority position

This document is the owner-approved V1 specification for the G1
simulation-only economic authority boundary. It is a documentation-only
contract. It creates no source code, runtime behavior, tests, dependencies,
persistence, API, provider access, wallet behavior, settlement, execution,
accounting, classification, or P09 behavior.

G1 has one deliberately narrow purpose:

> Recognize one complete paper-simulation lifecycle only when the complete
> explicitly supplied P06 → P07 → P08 chain is valid, linked, final, internally
> consistent, and free of material unresolved state.

G1's recognition is a governed statement about the completeness and finality of
one simulation lifecycle under this contract. It is not external economic truth,
external execution, settlement, realized value, accounting, valuation,
profitability, P&L, ROI, or performance classification.

The approved safe V1 decisions are:

1. G1 is simulation-only.
2. One G1 subject is one complete paper-simulation lifecycle.
3. The required chain is one P06 `DecisionIntent`, linked P07-T01 through
   P07-T06 artifacts, one P07-T07 history snapshot, and linked P08-T01 through
   P08-T06 artifacts.
4. Every input is an explicit immutable value or an explicitly materialized
   immutable reference carrying its identity, supported version, provenance,
   applicable timestamps/cutoffs, and digest.
5. G1 never fetches, infers, repairs, substitutes, filters, or reconstructs an
   artifact.
6. G1 recognizes a lifecycle only when every required predecessor is valid,
   linked, final, internally consistent, and free of material `UNKNOWN`,
   `UNAVAILABLE`, contradictory, failed, partial, unfilled, incomplete, stale,
   non-final, or unsupported state.
7. Every missing, stale, invalid, incomplete, partial, unfilled, failed,
   non-final, unknown, unavailable, contradictory, or unsupported input produces
   `NOT_RECOGNIZED`.
8. P08-T02 `as_of_time` is the sole G1 cutoff.
9. G1 does not invoke, redefine, wrap, or modify P08-T07.
10. G1 does not determine realization eligibility, settlement, accounting,
    valuation, P&L, ROI, cost basis, numeraire, `WIN`, `LOSS`, or `BREAKEVEN`.
11. G1 fails closed.
12. G3 remains the future accounting authority and G4 remains the future
    classification authority.

The proposal's possible `RECOGNIZED`/`NON_FINAL` state is not part of this
approved safe V1 contract. A non-final lifecycle is not recognized by V1.

## 2. Scope and non-overlap

### 2.1 Dependency chain

The required chain is:

```text
P06 DecisionIntent
    ↓
P07-T01 PaperSimulationInput
    ↓
P07-T02 PaperFillOutcome
    ↓
P07-T03 Position / Exposure Transition
    ↓
P07-T04 Paper Ledger
    ↓
P07-T05 Ledger / State Consistency Verification
    ↓
P07-T06 canonical finalized NON-ECONOMIC PaperSimulationResult
    ↓
P07-T07 PaperSimulationResultHistory snapshot
    ↓
P08-T01 OutcomeLearningObservation
    ↓
P08-T02 OutcomeLearningDatasetSnapshot
    ↓
P08-T03 Outcome Interpretation
    ↓
P08-T04 Outcome Evidence Evaluation
    ↓
P08-T05 Outcome Evidence Evaluation Snapshot
    ↓
P08-T06 Outcome Learning Readiness
    ↓
G1 simulation-only recognition/finality result
```

Every predecessor is supplied explicitly. G1 must not construct a predecessor
from an identifier, digest, timestamp, quantity, paper value, or caller
preference. A digest-only reference is insufficient unless its complete
canonical materialization is supplied as part of the immutable input.

### 2.2 Ownership map

| Boundary | Owns | G1 relationship |
|---|---|---|
| Authority A | Canonical Economic Subject Identity, Lifecycle Identity, lifecycle mapping, equivalence, split, and mapping conflict facts | G1 consumes established subject and lifecycle identities. It does not create, split, merge, map, or redefine them. |
| Authority B | Immutable correction and supersession lineage facts for established result identities | G1 produces an immutable result identity that may be referenced by a separately approved Authority B adapter. G1 does not create or interpret a lineage fact. |
| P07-T01 through P07-T06 | Paper input, fills, paper state, ledger, reconciliation, and canonical finalized non-economic result | G1 validates and preserves supplied P07 facts. It does not re-simulate, recalculate, reconcile, or reinterpret them as settlement. |
| P07-T07 | Immutable local history of validated P07-T06 results | G1 requires the explicit history snapshot to retain the exact P07-T06 result. It does not create history or persistence. |
| P08-T01 through P08-T06 | Observation, dataset cutoff, evidence-state interpretation, evidence evaluation, collection snapshot, and structural readiness | G1 requires and preserves the linked chain. It does not turn any P08 non-economic state into accounting authority. |
| G1 | Simulation-only recognition and simulation-lifecycle finality | G1 owns only the result defined in this document. |
| G2 | Future realization eligibility | G2 consumes the immutable G1 result under its own separately approved contract. G1 does not decide realization eligibility. |
| G3 | Future accounting and canonical economic-result calculation | G3 owns quantities, costs, fees, basis, numeraire, conversion, precision, rounding, and economic-result calculation. |
| G4 | Future performance classification | G4 owns `WIN`, `LOSS`, `BREAKEVEN`, and any approved classification vocabulary. |
| P08-T07 | Interpretation and assembly of separately supplied G2/G3/G4 results | G1 does not invoke, redefine, wrap, modify, or replace T07. |
| P09 | Separately governed execution chain | P09 is not a G1 dependency and remains not authorized. |

### 2.3 Paper finalization is not economic finality

P07-T06's `finalized` meaning remains exactly:

```text
canonical finalized NON-ECONOMIC PaperSimulationResult
```

It does not mean settlement, external finality, realized value, realized P&L,
accounting completion, or classification. G1's `FINAL` state means only that
the complete simulation lifecycle satisfies this G1 simulation-finality
contract.

## 3. Canonical subject and lifecycle

### 3.1 Subject definition

One G1 subject is exactly one complete paper-simulation lifecycle represented by:

- one established Authority A canonical economic subject identity;
- one established Authority A lifecycle identity;
- one linked P06 decision identity;
- one linked P07 paper-simulation chain;
- one retained P07-T07 history snapshot; and
- one linked P08-T01 through P08-T06 chain.

The subject identity and lifecycle identity are opaque established Authority A
references. G1 does not define Authority A's internal identity seed or
representation. G1 must preserve the exact supplied identity bytes, validate
their declared identity/digest contract, and reject missing, empty, ambiguous,
or contradictory references.

G1 does not derive identity from:

- fill count;
- timestamps;
- amounts or quantities;
- paper position;
- event ordering;
- caller-provided labels;
- database order;
- retrieval order; or
- result magnitude.

Multiple paper fills, ledger entries, and reconciliation observations remain
predecessor artifacts inside one lifecycle. G1 produces at most one primary
result for one explicit input snapshot.

### 3.2 Required identity links

The following exact links are mandatory:

```text
DecisionIntent identity/digest
    = PaperSimulationInput.decision_intent identity/digest

PaperSimulationInput identity/digest
    = PaperSimulationResult.input identity/digest

PaperSimulationResult identity/digest
    = exactly one retained member of the P07-T07 history snapshot

DecisionIntent + PaperSimulationInput + PaperSimulationResult + history
    = the P08-T01 observation linkage

P08-T01 observation
    = exactly one retained member of the P08-T02 dataset snapshot

P08-T02 dataset
    → P08-T03 interpretation
    → P08-T04 evaluation
    → P08-T05 evaluation snapshot
    → P08-T06 readiness

Authority A subject identity
    → Authority A lifecycle identity
    → every lifecycle-bearing predecessor
    → G1 lifecycle reference
```

Any broken, missing, ambiguous, cross-lifecycle, unsupported, or contradictory
link fails closed. G1 never infers a link from a matching digest fragment,
timestamp, quantity, or value.

## 4. Exact input contract

### 4.1 Public input

The future public input is exactly:

```text
G1SimulationOnlyEconomicAuthorityInput
```

It is an immutable value containing the complete materialized predecessor chain
and the established Authority A references. The input has no implicit registry,
clock, environment, filesystem, database, network, provider, wallet, account,
API, or persistence dependency.

The input contains exactly these semantic groups:

| Group | Required contents |
|---|---|
| `authority_a` | `canonical_economic_subject_identity`, `lifecycle_identity`, and the Authority A authority/version reference. |
| `p06` | Complete validated `DecisionIntent`, identity, contract version, evaluator version where applicable, provenance, canonical representation, and digest. |
| `p07` | Complete validated P07-T01, T02, T03, T04, T05, and T06 artifacts, each with its identity, supported version, canonical representation, provenance, and digest. |
| `p07_history` | One complete validated P07-T07 history snapshot and the exact retained P07-T06 result member. |
| `p08` | Complete validated P08-T01, T02, T03, T04, T05, and T06 artifacts, each with its identity, supported version, canonical representation, provenance, and digest. |
| `policy` | The fixed G1 contract version and evaluator version; no caller-selected policy or terminal-state override is accepted. |

The public input has no economic amount, price, fee, cost basis, numeraire,
valuation, P&L, ROI, classification, settlement, provider, wallet, account,
execution, or capital field owned by G1. Economic values may remain inside
immutable predecessor records only where their predecessor contract owns them;
G1 must not reinterpret or calculate them.

### 4.2 Required predecessor versions

G1 accepts only the exact supported predecessor contracts below:

| Predecessor | Required version |
|---|---|
| P07-T07 history | `p07-t07-v1` |
| P08-T01 observation | `p08-t01-v1` |
| P08-T02 dataset | `p08-t02-v1` |
| P08-T03 interpretation | `p08-t03-v1` |
| P08-T04 evaluation | `p08-t04-v1` |
| P08-T05 evaluation snapshot | `p08-t05-v1` |
| P08-T06 readiness | `p08-t06-v1` |
| G1 contract | `p08-g1-simulation-only-v1` |
| G1 evaluator | `p08-g1-simulation-only-economic-authority-v1` |

P06 and P07-T01 through P07-T06 versions must be present and validated against
their own closed contracts. An unsupported or absent version is not substituted
with a compatible-looking version.

### 4.3 Input validation

Before producing a normal result, G1 validates, in the declared order:

1. the exact input type and required structure;
2. presence of every required artifact and Authority A reference;
3. supported contract, evaluator, policy, and predecessor versions;
4. canonical representation of every supplied artifact;
5. every supplied identity and digest;
6. exact P06 → P07 identity and digest links;
7. exact P07-T06 → P07-T07 membership;
8. exact P06/P07 → P08-T01 linkage;
9. exact P08-T01 → P08-T02 membership and cutoff compliance;
10. exact P08-T02 → P08-T03 → P08-T04 → P08-T05 → P08-T06 linkage;
11. Authority A subject/lifecycle equality across all applicable records;
12. complete ordered provenance;
13. absence of stale, future-inconsistent, unknown, unavailable, incomplete,
    contradictory, failed, partial, unfilled, or non-final material; and
14. deterministic canonical result identity and digest derivation.

G1 rejects the input rather than repairing, dropping, filtering, or downgrading
any failed validation.

## 5. Recognition and finality contract

### 5.1 Recognition condition

The lifecycle is recognized only when all of the following are true:

1. exactly one supported P06 `DecisionIntent` is supplied;
2. exactly one complete supported P07-T01 through P07-T06 chain is supplied;
3. every P07 predecessor is valid, canonical, immutable, and exactly linked;
4. exactly one supported P07-T06 `PaperSimulationResult` is retained by the
   supplied P07-T07 history snapshot;
5. the P07-T06 result is canonical and its paper-simulation lifecycle is
   terminal under Section 5.2;
6. exactly one P08-T01 observation contains the P06/P07 linkage;
7. that observation is retained exactly once by the supplied P08-T02 dataset;
8. the P08-T03 through P08-T06 chain is complete, valid, canonical, and linked;
9. the Authority A subject and lifecycle references match every applicable
   predecessor reference;
10. P08-T02 `as_of_time` is valid, timezone-aware, canonical UTC, and is the
    only G1 cutoff;
11. every required identity, version, provenance link, and digest validates; and
12. no material prohibited or unresolved state exists anywhere in the required
    chain.

If and only if every condition holds, G1 emits:

```text
recognition_state = RECOGNIZED
finality_state    = FINAL
reason_code       = RECOGNIZED_COMPLETE
```

`RECOGNIZED` means recognized by this simulation-only contract. It does not mean
externally economically true.

### 5.2 Approved simulation-finality condition

The approved V1 terminal condition is a conjunction of predecessor-owned facts;
G1 does not invent a new P07 status:

- P07-T01 through P07-T05 are valid and linked;
- the P07-T02 outcome is complete rather than partial, unfilled, failed,
  rejected, unavailable, or invalid;
- the P07-T03 transition and resulting paper state are complete and internally
  consistent;
- the P07-T04 ledger is complete and canonical;
- the P07-T05 reconciliation is valid and reconciled, with no unresolved
  disagreement or unknown state;
- the P07-T06 result is the canonical finalized non-economic result;
- the P07-T06 result contains no unresolved unknown, unavailable, incomplete,
  failed, contradictory, or unsupported simulation state; and
- the linked P08-T01 through P08-T06 chain is complete and valid.

G1 may inspect predecessor-owned status and completeness fields to validate this
predicate, but it must not recalculate fills, quantities, paper state, ledger
entries, reconciliation, or any economic value.

### 5.3 Non-recognition

Any one of the following produces:

```text
recognition_state = NOT_RECOGNIZED
finality_state    = NOT_APPLICABLE
```

- missing or incomplete material;
- stale or future-inconsistent material;
- invalid type, version, identity, canonical representation, digest, or
  provenance;
- broken, ambiguous, contradictory, or cross-lifecycle linkage;
- partial, unfilled, failed, rejected, unavailable, unknown, or non-final
  predecessor state;
- unsupported simulation state;
- unresolved correction or supersession context; or
- any non-deterministic or unsupported input condition.

V1 has no `RECOGNIZED`/`NON_FINAL` result. Elapsed time, later retrieval,
paper quantity, positive or negative paper value, caller preference, or a later
unrelated artifact cannot upgrade a non-final input.

### 5.4 State model

| `recognition_state` | `finality_state` | Meaning |
|---|---|---|
| `NOT_RECOGNIZED` | `NOT_APPLICABLE` | The required simulation lifecycle or provenance chain is absent, invalid, contradictory, unsupported, stale, incomplete, or not terminal. |
| `RECOGNIZED` | `FINAL` | The complete required chain is valid, linked, internally consistent, terminal, and recognized under the simulation-only contract. |

No G1 state means `SETTLED`, `REALIZED`, `ACCOUNTED`, `VALUED`, `PROFIT`,
`LOSS`, `WIN`, or `BREAKEVEN`.

## 6. Exact output contract

### 6.1 Public output

The future public output is exactly:

```text
G1SimulationOnlyEconomicAuthorityResult
```

It is an immutable record with exactly these semantic fields:

| Field | Required meaning |
|---|---|
| `contract_version` | `p08-g1-simulation-only-v1`. |
| `evaluator_version` | `p08-g1-simulation-only-economic-authority-v1`. |
| `canonical_economic_subject_identity` | Established Authority A subject identity copied without reinterpretation. |
| `lifecycle_identity` | Established Authority A lifecycle identity copied without reinterpretation. |
| `decision_intent_identity` | P06 decision identity reference. |
| `paper_simulation_result_identity` | P07-T06 result identity reference. |
| `history_snapshot_identity` | P07-T07 history snapshot identity reference. |
| `observation_identity` | P08-T01 observation identity reference. |
| `dataset_snapshot_identity` | P08-T02 dataset identity reference. |
| `dataset_as_of_time` | P08-T02 `as_of_time`, preserved in canonical UTC form; it is not an economic endpoint. |
| `readiness_identity` | P08-T06 readiness result identity reference. |
| `recognition_state` | `NOT_RECOGNIZED` or `RECOGNIZED`. |
| `finality_state` | `NOT_APPLICABLE` or `FINAL`. |
| `reason_code` | Exactly one value from Section 7. |
| `provenance` | Complete ordered predecessor and Authority A provenance links. |
| `result_identity` | Immutable G1 result identity derived under Section 8. |
| `result_digest` | SHA-256 digest over the complete canonical result excluding only this field. |

Every field is present in the canonical representation. G1 has no nullable
semantic field. For `NOT_RECOGNIZED`, identity and provenance fields preserve
the explicitly supplied validated references that are available before the
first applicable failure; if a required reference is absent, the operation
fails closed without a normal result. A failure must never invent a
placeholder identity.

The output contains no amount, quantity, price, fee, cost basis, numeraire,
valuation, P&L, ROI, classification, settlement, wallet, provider, account,
execution, capital, or external-finality field.

### 6.2 Output cardinality

One valid explicit input produces exactly one immutable result. An invalid input
produces no normal result rather than a partial or synthetic result. G1 has no
batch, aggregate, ranking, collection, persistence, or ambient-registry mode.

## 7. Reason vocabulary and precedence

### 7.1 Exact reason vocabulary

The bounded reason vocabulary is:

```text
RECOGNIZED_COMPLETE
INVALID_TYPE
MISSING_REQUIRED_INPUT
UNSUPPORTED_VERSION
INVALID_CANONICAL_REPRESENTATION
DIGEST_FAILURE
INVALID_IDENTITY_LINK
INVALID_LIFECYCLE
PROVENANCE_FAILURE
CONTRADICTORY_INPUT
STALE_INPUT
UNKNOWN_INPUT
UNAVAILABLE_INPUT
INCOMPLETE_INPUT
PARTIAL_INPUT
UNFILLED_INPUT
FAILED_INPUT
NON_FINAL_INPUT
UNSUPPORTED_SIMULATION_STATE
UNRESOLVED_CORRECTION
UNRESOLVED_SUPERSESSION
DETERMINISM_FAILURE
```

`RECOGNIZED_COMPLETE` is used only with `RECOGNIZED`/`FINAL`. Every other
reason is used only with `NOT_RECOGNIZED`/`NOT_APPLICABLE`.

### 7.2 Deterministic reason precedence

Exactly one reason is selected. When multiple conditions apply, the first
applicable category in this fixed order wins:

1. `INVALID_TYPE`
2. `MISSING_REQUIRED_INPUT`
3. `UNSUPPORTED_VERSION`
4. `INVALID_CANONICAL_REPRESENTATION`
5. `DIGEST_FAILURE`
6. `INVALID_IDENTITY_LINK`
7. `INVALID_LIFECYCLE`
8. `PROVENANCE_FAILURE`
9. `CONTRADICTORY_INPUT`
10. `STALE_INPUT`
11. `UNKNOWN_INPUT`
12. `UNAVAILABLE_INPUT`
13. `INCOMPLETE_INPUT`
14. `PARTIAL_INPUT`
15. `UNFILLED_INPUT`
16. `FAILED_INPUT`
17. `NON_FINAL_INPUT`
18. `UNSUPPORTED_SIMULATION_STATE`
19. `UNRESOLVED_CORRECTION`
20. `UNRESOLVED_SUPERSESSION`
21. `DETERMINISM_FAILURE`

The precedence is based on the canonical validation model, not caller order,
retrieval order, timestamps, result magnitude, freshness, or preference.

## 8. Identity, canonicalization, and digests

### 8.1 Result identity

G1 does not create a subject or lifecycle identity. It creates only the identity
of its immutable result. The identity projection is the fixed eleven-element
canonical JSON array:

```text
[
  contract_version,
  canonical_economic_subject_identity,
  lifecycle_identity,
  decision_intent_identity,
  paper_simulation_result_identity,
  history_snapshot_identity,
  observation_identity,
  dataset_snapshot_identity,
  readiness_identity,
  recognition_state,
  finality_state
]
```

The result identity is:

```text
SHA-256(
  UTF-8(
    "p08-g1-simulation-only:result:v1\0"
    + canonical_identity_projection
  )
)
```

The identity projection excludes `result_identity`, `result_digest`, reason
code, provenance, and any digest that would create a circular dependency.

### 8.2 Canonical representation

The canonical representation is compact UTF-8 JSON with:

1. no byte-order mark or insignificant whitespace;
2. Unicode NFC normalization before escaping;
3. object keys sorted by Unicode code-point order;
4. fixed semantic array order;
5. explicit enum strings;
6. canonical UTC timestamp serialization as an RFC 3339 UTC string with
   fractional seconds only when required by the inherited timestamp;
7. lowercase ASCII hexadecimal SHA-256 digests;
8. no language-specific object or collection ordering;
9. no numeric semantic fields introduced by G1;
10. no absent-versus-null equivalence; and
11. no wall-clock-generated, random, process, filesystem, database, network, or
    provider value.

Textual identity, version, authority, stage, enum, and reason values are
validated as non-empty strings before NFC normalization. Unpaired surrogate
code points are invalid. Control characters use only the permitted JSON short
escapes or lowercase `\u00xx` escapes. Non-ASCII Unicode scalar values are
emitted directly as UTF-8.

`result_digest` is SHA-256 over the complete canonical result representation
with only `result_digest` omitted. A digest never participates in the identity
projection it protects.

### 8.3 Provenance representation

`provenance` is a fixed ordered immutable tuple of links in this order:

```text
p06_decision_intent
p07_simulation_input
p07_fill_outcome
p07_position_exposure
p07_ledger
p07_reconciliation
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

Each link contains exactly:

```text
stage
record_identity
record_digest
authority_identity
contract_version
evaluator_version
```

The link values are copied from the supplied governed records. G1 does not
invent, omit, reorder, or reinterpret a provenance link.

## 9. Cutoff, temporal semantics, and replay

### 9.1 Sole cutoff

P08-T02 `as_of_time` is the sole G1 cutoff. It is copied exactly after
canonical UTC normalization and is never treated as:

- settlement time;
- an economic endpoint;
- a valuation horizon;
- a realized-outcome time;
- a correction time; or
- a supersession time.

G1 does not accept an independent cutoff, current time, elapsed-duration rule,
evaluation horizon, or caller-selected temporal policy.

G1 validates the T02 observation membership and cutoff according to the closed
T02 contract. Other inherited event and paper-state timestamps remain owned by
their predecessor contracts and are preserved as provenance; G1 does not use
them to create a second cutoff or to infer economic finality.

### 9.2 Replay invariant

For the same explicit immutable input set:

```text
G1(input A) == G1(input A)
```

Replay must reproduce the same:

- recognition state;
- finality state;
- reason code;
- subject and lifecycle references;
- canonical representation;
- result identity; and
- result digest.

The result must not depend on wall-clock time, timezone, randomness, process
identity, memory address, filesystem state, database state, insertion order,
retrieval order, network state, provider state, hidden configuration, or
ambient persistence.

Future evidence or a different explicit T02 snapshot may produce a different
new G1 result. It must never mutate this result or silently update its identity.

### 9.3 Temporal failure

G1 fails closed on future-inconsistent T02 material, stale material, invalid
inherited timestamp representation, or any temporal contradiction already
visible under the applicable predecessor contract. G1 does not silently exclude
future material or repair late material.

## 10. Authority B relationship

G1 results are immutable. A changed conclusion is a new G1 result with a new
result identity; it is never an in-place edit.

Authority B remains the sole owner of:

- correction facts;
- supersession facts;
- predecessor/successor relationships;
- lineage-fact identity;
- lineage provenance; and
- lineage policy/version.

G1 must not:

- create a `LineageFact` or `LineageEdge`;
- choose correction versus supersession;
- choose a canonical lineage head;
- resolve a branch, cycle, merge, or conflicting duplicate;
- mutate a predecessor result;
- redefine the Authority A lifecycle; or
- make a corrected or superseded result economically realized.

A future separately approved adapter may reference immutable G1 result identities
from Authority B and may then be validated by T07 under the existing Authority B
and T07 contracts. This specification authorizes no adapter, lineage change, or
T07 change.

## 11. Exact boundary into future G2

The only semantic assertions available to G2 are:

1. whether one complete paper-simulation lifecycle is recognized under the
   simulation-only G1 contract; and
2. whether that recognized simulation lifecycle is final under the approved
   simulation-finality predicate.

G2 may consume the immutable G1 result identity, subject/lifecycle references,
recognition state, finality state, provenance, and digest. G2 must apply its own
separately approved realization-eligibility contract and must not infer a
realized outcome from `RECOGNIZED` or `FINAL` alone.

G1 must not decide:

- whether external execution occurred;
- whether settlement occurred;
- whether value was realized;
- whether accounting inputs are admissible;
- accounting basis, cost basis, numeraire, conversion, precision, or rounding;
- valuation;
- P&L, ROI, or profitability;
- `WIN`, `LOSS`, or `BREAKEVEN`;
- custody, wallet, account ownership, provider truth, or capital state; or
- any Risk Governor, capital authorization, execution, signing, broadcast, or
  P09 step.

## 12. Explicit prohibitions

G1 is prohibited from:

- real-money behavior or live trading;
- external economic truth or external settlement claims;
- provider, RPC, DEX, exchange, network, or external API access;
- custody, wallet, account, private-key, signer, signing, or broadcast behavior;
- execution requests or execution behavior;
- Risk Governor decisions or capital authorization;
- settlement or external-finality integration;
- valuation, accounting, P&L, ROI, cost basis, numeraire, conversion,
  precision, rounding, or economic-result calculation;
- `WIN`, `LOSS`, `BREAKEVEN`, or any performance classification;
- G2 realization-eligibility decisions;
- G3 accounting/economic-result decisions;
- G4 classification decisions;
- invoking, redefining, wrapping, modifying, or redesigning P08-T07;
- creating, mutating, splitting, merging, or redefining Authority A identity;
- creating Authority B correction/supersession facts or resolving lineage graphs;
- persistence, migrations, caches, queues, ambient registries, or database
  authority;
- model training, strategy updates, parameter updates, or learning behavior;
- fetching, reconstructing, repairing, filtering, or substituting evidence; and
- P09 behavior of any kind.

The existence of a paper result, readiness result, G1 `FINAL` state, or this
approved specification does not waive any prohibition.

## 13. Future implementation paths

These are future paths only. This specification creates neither file:

```text
core/learning/g1_simulation_only_economic_authority.py
tests/test_g1_simulation_only_economic_authority.py
```

No package export, dependency, migration, API, workflow, persistence, or
runtime change is authorized by this document.

## 14. Future verification and test plan

If and only if implementation receives separate authorization, the focused test
plan must cover at least:

1. one complete valid P06/P07/P08 chain produces exactly
   `RECOGNIZED`/`FINAL` and preserves every identity, version, provenance link,
   cutoff, and digest;
2. the exact input and output field contracts and supported versions;
3. missing artifact and invalid-type rejection;
4. unsupported version rejection;
5. every P06 → P07, P07 → history, P07 → P08, and P08 → G1 linkage failure;
6. cross-lifecycle, ambiguous, contradictory, and invalid Authority A identity;
7. missing, stale, future-inconsistent, and invalid cutoff material;
8. canonical representation and digest tampering;
9. P07-T06 history membership failure and duplicate membership;
10. incomplete, unknown, unavailable, failed, partial, unfilled, rejected,
    non-final, and unsupported simulation states;
11. deterministic reason precedence when multiple failures apply;
12. canonicalization stability across equivalent input ordering and Unicode
    representations;
13. deterministic identity and result digest replay;
14. no wall-clock, timezone, randomness, process, filesystem, database,
    network, provider, wallet, or ambient-registry dependency;
15. recursive immutability of the result, provenance, and supplied
    predecessor material;
16. correction/supersession behavior proving G1 creates no Authority B fact;
17. no accounting, valuation, settlement, P&L, ROI, classification, G2, G3,
    G4, T07, capital, execution, or P09 behavior; and
18. exact future-path and dependency boundary compliance.

These are future implementation-audit expectations only. They do not authorize
implementation.

## 15. Separate implementation-authorization gate

This specification is complete at the governance/specification level only.
Implementation remains unauthorized unless a separate explicit authorization
records all of the following:

1. formal audit of this specification is complete;
2. P07-T01 through P07-T07 remain closed, immutable, and unchanged;
3. P08-T01 through P08-T06 remain closed, immutable, and unchanged;
4. Authority A remains specification-level and its established identity is
   consumed without redefinition;
5. Authority B remains the sole lineage authority;
6. P08-T07 remains unchanged and outside the G1 implementation boundary;
7. the exact input/output fields, versions, state model, reason vocabulary,
   reason precedence, cutoff rule, identity projection, canonicalization, and
   digest coverage are accepted without additions;
8. the implementation is limited exactly to the two future paths in Section 13;
9. focused tests cover every valid and fail-closed path in Section 14;
10. no provider, external I/O, persistence, wallet, settlement, accounting,
    classification, execution, or P09 behavior is included; and
11. a separate implementation audit is required before any G2 specification
    work begins.

No implementation authorization is implied by specification completion, audit
completion, a documentation status, a P07 result, a P08 readiness result, or a
G1 `FINAL` result.

## 16. Specification conclusion

The approved boundary is:

```text
one explicit complete P06 → P07 → P08 simulation provenance chain
    → G1SimulationOnlyEconomicAuthorityResult
```

The only successful G1 result is:

```text
RECOGNIZED / FINAL / RECOGNIZED_COMPLETE
```

All missing, stale, invalid, incomplete, partial, unfilled, failed, non-final,
unknown, unavailable, contradictory, or unsupported input results in:

```text
NOT_RECOGNIZED / NOT_APPLICABLE / <one deterministic failure reason>
```

G1 is simulation-only and fail-closed. It supplies future G2 with recognition
and simulation-finality state only. G3 remains the future accounting authority,
G4 remains the future classification authority, P08-T07 remains unchanged, and
G1, G2, G3, G4, and P09 implementation remain separately unauthorized.