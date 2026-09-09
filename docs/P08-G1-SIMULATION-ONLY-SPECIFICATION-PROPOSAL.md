# P08 — G1 Simulation-Only Economic Authority Specification Proposal

**Status:** PROPOSAL / AWAITING OWNER APPROVAL
**Phase:** P08 — Outcome Learning
**Boundary:** G1 — Simulation-Only Economic Authority
**Implementation status:** NOT AUTHORIZED

## 1. Proposal scope and authority boundary

This document is a candidate semantic contract for a simulation-only G1
authority. It is documentation-only. It creates no source code, runtime
behavior, tests, dependencies, persistence, API, provider access, wallet
behavior, settlement, execution, accounting, classification, or P09 behavior.

The owner-selected decisions incorporated by this proposal are:

- G1 is simulation-only.
- One canonical G1 economic subject is one complete paper-simulation
  lifecycle.
- G1 must not calculate valuation, accounting, P&L, ROI, cost basis, numeraire,
  `WIN`, `LOSS`, or `BREAKEVEN`.
- G3 remains the future exclusive accounting/economic-result authority.
- G4 remains the future exclusive performance-classification authority.
- No custody, wallet, account, provider, RPC, DEX, network, signing,
  settlement, broadcast, execution, Risk Governor, capital, or P09 behavior is
  allowed.

Within this proposal, **simulation-only economic recognition** means a bounded
statement that a complete paper-simulation lifecycle satisfies this G1
contract. It does not mean external economic truth, settlement, realized
value, realized P&L, or performance classification. P07-T06's word
“finalized” retains its existing meaning: the canonical non-economic paper
result has been assembled.

### 1.1 Exact purpose

G1 is proposed to:

1. validate one complete, immutable P06 → P07 → P08 simulation provenance
   chain;
2. preserve the Authority A subject and lifecycle references without
   redefining them;
3. determine whether that simulation lifecycle is recognized under the
   simulation-only G1 contract;
4. determine whether the simulation lifecycle meets the proposed G1
   simulation-finality condition; and
5. expose only those recognition and finality states to future G2.

G1 does not create a new external economic event, calculate an economic
amount, or decide whether any result is realized or realization-eligible.

### 1.2 Non-overlap

| Boundary | Proposed relationship |
|---|---|
| Authority A | Supplies the established canonical economic subject and lifecycle identities. G1 preserves and validates them; it does not create, split, merge, or redefine them. |
| P07-T06 | Supplies the canonical finalized non-economic `PaperSimulationResult`. G1 may validate its terminal simulation state but must not reinterpret P07 finalization as settlement. |
| P07-T07 | Supplies the immutable history snapshot retaining the selected paper result. G1 uses the explicit snapshot; it does not create live history or persistence. |
| P08-T01 through P08-T06 | Supply the validated observation, dataset, evidence-state interpretation, evidence evaluation, evaluation snapshot, and structural readiness chain. G1 preserves these artifacts as explicit predecessor context and does not turn their non-economic states into accounting authority. |
| Authority B | Owns correction and supersession lineage facts for immutable G1/T07 result identities if the approved adapter relationship permits them. G1 does not create or interpret Authority B lineage facts. |
| G2 | Consumes the G1 recognition/finality result to make its separately governed realization-eligibility decision. G1 does not make that decision. |
| G3 | Owns all future accounting and canonical economic-result calculation. |
| G4 | Owns all future performance classification. |
| P08-T07 | Consumes separately governed G2/G3/G4 results and validates supplied lineage. It does not collect G1 evidence or replace G1 authority. |
| P09 | Remains separate and not authorized. |

## 2. Canonical simulation lifecycle subject

### 2.1 Subject definition

The canonical G1 economic subject is:

> One complete paper-simulation lifecycle represented by exactly one
> Authority A lifecycle identity and one linked P06 decision, with its
> validated P07 paper-simulation chain and P08 observation chain.

G1 does not derive a subject identity from fill count, timestamps, amounts,
event ordering, paper position, or arbitrary caller fields. The G1 subject
reference is the already-established Authority A canonical economic subject
identity plus its Authority A lifecycle identity.

One G1 evaluation produces at most one primary G1 result for that lifecycle
and explicit input snapshot. Multiple paper fills, ledger entries, or
reconciliation observations remain predecessor artifacts within the one
lifecycle. G1 does not produce one economic subject per fill.

### 2.2 Required predecessor chain

The candidate required chain is:

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
P08-T02 Dataset Snapshot
    ↓
P08-T03 Evidence-State Interpretation
    ↓
P08-T04 Evidence Evaluation
    ↓
P08-T05 Evaluation Snapshot
    ↓
P08-T06 non-economic Readiness
    ↓
G1 simulation-only recognition/finality result
```

Every predecessor must be supplied as its existing immutable contract at its
supported version. G1 must not reconstruct any predecessor from partial
evidence, identifiers, timestamps, or paper values.

The P07-T06 result is explicitly non-economic. The P08-T06 readiness result is
explicitly structural and non-economic. Their presence in the chain proves
validated simulation provenance and structural readiness only; neither one
alone is a settlement, realized-result, accounting, or classification fact.

### 2.3 Required identity links

The candidate chain must preserve and validate these links:

```text
DecisionIntent identity/digest
    = PaperSimulationInput.decision_intent identity/digest

PaperSimulationInput identity/digest
    = PaperSimulationResult.input identity/digest

PaperSimulationResult identity/digest
    = retained result in P07-T07 history

DecisionIntent + PaperSimulationInput + PaperSimulationResult + history
    = P08-T01 observation linkage

P08-T01 observation
    = retained member of the supplied P08-T02 dataset snapshot

P08-T02 dataset
    → P08-T03 interpretation
    → P08-T04 evaluation
    → P08-T05 evaluation snapshot
    → P08-T06 readiness

Authority A canonical subject identity
    → Authority A lifecycle identity
    → G1 lifecycle reference
```

Any broken, ambiguous, cross-lifecycle, unsupported, or contradictory link
fails closed. G1 does not infer a missing link from a matching candidate,
timestamp, quantity, or digest fragment.

## 3. Candidate lifecycle recognition and finality rules

### 3.1 Recognition condition

The candidate G1 recognition condition is satisfied only when all of the
following are true:

1. exactly one supported P06 `DecisionIntent` is supplied;
2. exactly one supported P07 paper-simulation chain is supplied;
3. P07-T01 through P07-T05 are valid and linked without contradiction;
4. one supported P07-T06 `PaperSimulationResult` is valid, canonical, and
   linked to the P07-T07 history snapshot;
5. the selected paper result is retained exactly once by the supplied
   immutable history snapshot;
6. P08-T01 contains the exact P06/P07 observation linkage;
7. the P08-T01 observation is retained in the supplied P08-T02 dataset
   snapshot;
8. the supplied P08-T03 through P08-T06 chain is valid and linked;
9. the Authority A subject and lifecycle references are present and match all
   lifecycle-bearing predecessor references; and
10. every required contract version, canonical representation, provenance
    link, identity, and digest validates.

If these conditions hold, G1 emits the candidate recognition state
`RECOGNIZED`. This means “recognized by the simulation-only G1 contract,” not
“externally economically true.”

If any condition is not met, G1 emits `NOT_RECOGNIZED` with one deterministic
failure reason and no finality assertion.

### 3.2 Candidate finality condition

The candidate finality condition is intentionally narrower than P07-T06
finalization:

G1 may emit `FINAL` only when:

1. the recognition condition is satisfied;
2. the supplied P07-T06 result is the canonical finalized non-economic result
   for the lifecycle;
3. the P07 simulation state is an explicitly approved terminal simulation
   state;
4. no required predecessor retains an unresolved `UNKNOWN`, `UNAVAILABLE`,
   `INCOMPLETE`, failure, contradictory, or unresolved reconciliation state
   that the approved G1 policy defines as non-final; and
5. the supplied P08 chain is valid for the same explicit input snapshot.

P07-T06 assembly alone is not sufficient to make a G1 result final. G1
finality is a simulation-lifecycle finality label only. It is not settlement
finality, realization eligibility, realized P&L, or classification.

If the lifecycle is recognized but the terminal simulation condition is not
satisfied, G1 emits `RECOGNIZED` with finality `NON_FINAL`. It must not
upgrade this state because of elapsed time, a later retrieval, a paper
quantity, a positive or negative paper value, or caller preference.

If recognition fails, finality is `NOT_APPLICABLE`.

### 3.3 Candidate state model

The proposed state pair is:

| `recognition_state` | `finality_state` | Meaning |
|---|---|---|
| `NOT_RECOGNIZED` | `NOT_APPLICABLE` | The required simulation lifecycle or its provenance is missing, invalid, contradictory, unsupported, or non-canonical. |
| `RECOGNIZED` | `NON_FINAL` | The lifecycle and chain are valid, but the approved terminal simulation condition is not satisfied. |
| `RECOGNIZED` | `FINAL` | The lifecycle and chain are valid and the approved terminal simulation condition is satisfied. |

No state in this table means `SETTLED`, `REALIZED`, `PROFIT`, `LOSS`,
`WIN`, `BREAKEVEN`, `ACCOUNTED`, or `VALUED`.

## 4. Candidate G1 input contract

The future public input is proposed as:

```text
G1SimulationOnlyEconomicAuthorityInput
```

It is a value input composed only of explicit, immutable, already-validated
P06/P07/P08 artifacts and identity/digest references. It has no provider,
wallet, account, network, database, clock, or persistence dependency.

### 4.1 Required input artifacts

| Input artifact | G1 treatment |
|---|---|
| P06 `DecisionIntent` | Required complete predecessor; preserve identity, digest, contract version, decision context, and provenance. |
| P07-T01 `PaperSimulationInput` | Required complete predecessor; preserve its decision link and digest. |
| P07-T02 `PaperFillOutcome` | Required through the validated P07-T06 chain; G1 does not recalculate fills. |
| P07-T03 position/exposure transition | Required through the validated P07-T06 chain; G1 does not mutate paper state. |
| P07-T04 paper ledger | Required through the validated P07-T06 chain; G1 does not treat it as a live or external ledger. |
| P07-T05 reconciliation result | Required through P07-T06 provenance; G1 preserves its status and does not reconcile externally. |
| P07-T06 `PaperSimulationResult` | Required canonical simulation result and primary paper-lifecycle predecessor. |
| P07-T07 `PaperSimulationResultHistory` | Required explicit immutable snapshot retaining the exact P07-T06 result. |
| P08-T01 observation | Required exact decision-to-paper-result observation. |
| P08-T02 dataset snapshot | Required explicit snapshot containing the observation and its cutoff. |
| P08-T03 interpretation | Required validated evidence-state predecessor; no economic interpretation is copied from it. |
| P08-T04 evidence evaluation | Required validated predecessor; no new admissibility rule is inferred. |
| P08-T05 evaluation snapshot | Required complete collection snapshot. |
| P08-T06 readiness | Required structural readiness predecessor; it is not treated as economic evidence. |
| Authority A subject/lifecycle references | Required established identities; G1 preserves them and must not generate replacements. |

G1 receives these as explicit value inputs or explicitly materialized
references under the approved adapter contract. It must not fetch missing
artifacts, consult an ambient registry, read a database, or reconstruct
predecessors from digests.

### 4.2 Required identity, provenance, and digest inputs

The input must preserve:

- every predecessor contract and evaluator/policy version;
- every predecessor identity and digest needed to validate the chain;
- Authority A canonical subject and lifecycle identities;
- the exact P07-T06 result retained by P07-T07;
- the exact P08-T01 observation retained by P08-T02;
- the P08-T02 `as_of_time` and its snapshot identity/digest;
- source and authority identities already present in predecessor provenance;
- all upstream provenance in fixed predecessor order; and
- the explicit G1 contract/evaluator version.

The G1 wrapper must not add external source identity, settlement authority,
provider identity, wallet identity, account ownership, or a new economic event
identity.

## 5. Candidate temporal, cutoff, and replay contract

### 5.1 Time inputs

G1 does not own an event clock or a current-time clock. It may preserve the
timestamps already governed by its predecessor artifacts, including:

- P06 decision context reference time;
- P07 simulation timestamps and paper-state timestamps;
- P07-T05 reconciliation timestamps;
- P08-T01 observation timestamps; and
- P08-T02 dataset `as_of_time`.

The candidate contract does not create a G1 ingestion time, settlement time,
valuation time, correction time, or supersession time.

### 5.2 Cutoff rule

The candidate uses the explicit P08-T02 dataset snapshot and its
`as_of_time` only to identify the supplied point-in-time predecessor set. It
does not treat `as_of_time` as settlement, realization, accounting, or
classification finality.

G1 finality is determined from the supplied simulation artifacts and approved
terminal simulation-state policy, not from the current clock, a fixed elapsed
duration, or a later observation.

### 5.3 Replay invariant

For the same supported predecessor artifacts, Authority A identity references,
explicit snapshot memberships, contract versions, and canonical
representations:

```text
G1(input set A) == G1(input set A)
```

Replay must reproduce the same:

- recognition state;
- finality state;
- reason code;
- lifecycle reference;
- canonical representation;
- result identity; and
- result digest.

Replay must not depend on wall-clock time, timezone, randomness, process
identity, memory address, filesystem state, insertion order, retrieval order,
database state, provider state, network state, or hidden configuration.

Future evidence or a different explicit snapshot may produce a different
contextual outcome, but it must not mutate a prior G1 result. The prior result
must remain available for explicit correction or supersession lineage.

## 6. Candidate G1 output contract

The future public output is proposed as:

```text
G1SimulationOnlyEconomicAuthorityResult
```

### 6.1 Output fields

The candidate output contains:

| Field | Candidate meaning |
|---|---|
| `contract_version` | Fixed G1 output contract version. |
| `evaluator_version` | Fixed G1 evaluator version. |
| `canonical_economic_subject_identity` | Authority A subject identity copied without reinterpretation. |
| `lifecycle_identity` | Authority A lifecycle identity copied without reinterpretation. |
| `decision_intent_identity` | P06 decision identity reference. |
| `paper_simulation_result_identity` | P07-T06 result identity reference. |
| `history_snapshot_identity` | P07-T07 history snapshot identity reference. |
| `observation_identity` | P08-T01 observation identity reference. |
| `dataset_snapshot_identity` | P08-T02 dataset identity reference. |
| `dataset_as_of_time` | The preserved P08-T02 cutoff timestamp, not a G1 economic endpoint. |
| `recognition_state` | `NOT_RECOGNIZED` or `RECOGNIZED`. |
| `finality_state` | `NOT_APPLICABLE`, `NON_FINAL`, or `FINAL`. |
| `reason_code` | One bounded recognition/finality or fail-closed reason. |
| `provenance` | Complete ordered predecessor and Authority A provenance references. |
| `result_identity` | Derived identity of this immutable G1 result. |
| `result_digest` | Integrity digest over the complete canonical result representation excluding only this digest. |

The output contains no amount, quantity, price, fee, cost basis, numeraire,
valuation, P&L, ROI, classification, settlement, wallet, provider, account,
execution, or capital field.

### 6.2 Candidate reason vocabulary

The proposed bounded vocabulary is:

```text
RECOGNIZED_COMPLETE
RECOGNIZED_NON_FINAL
MISSING_REQUIRED_INPUT
UNSUPPORTED_VERSION
INVALID_TYPE
INVALID_IDENTITY_LINK
INVALID_LIFECYCLE
INVALID_CANONICAL_REPRESENTATION
DIGEST_FAILURE
PROVENANCE_FAILURE
CONTRADICTORY_INPUT
NON_FINAL_SIMULATION
UNSUPPORTED_SIMULATION_STATE
UNRESOLVED_CORRECTION
UNRESOLVED_SUPERSESSION
DETERMINISM_FAILURE
```

`RECOGNIZED_COMPLETE` is used only for `RECOGNIZED` / `FINAL`.
`RECOGNIZED_NON_FINAL` and `NON_FINAL_SIMULATION` are used only for
`RECOGNIZED` / `NON_FINAL`. All other reasons produce
`NOT_RECOGNIZED` / `NOT_APPLICABLE`.

This vocabulary is proposed for approval; it does not reuse T07's failure
vocabulary by implication.

### 6.3 Candidate identity and canonical representation

G1 must not create a replacement subject or lifecycle identity. The candidate
`result_identity` is a separate identity for the immutable G1 result:

```text
result_identity =
SHA-256(
  UTF-8(
    "p08-g1-simulation-only:result:v1\0"
    + canonical_identity_projection
  )
)
```

The proposed identity projection is the fixed array:

```text
[
  contract_version,
  lifecycle_identity,
  paper_simulation_result_identity,
  dataset_snapshot_identity,
  recognition_state,
  finality_state
]
```

The proposed canonical result representation is compact UTF-8 JSON with:

- Unicode NFC normalization before escaping;
- sorted object keys by Unicode code point;
- fixed semantic array order;
- explicit enum strings;
- UTC-normalized inherited timestamps;
- no language-specific object ordering;
- no wall-clock-generated fields; and
- no semantic numeric field introduced by G1.

The `result_digest` is SHA-256 over the complete canonical result
representation with only `result_digest` omitted. A digest never participates
in the identity projection it protects.

These are candidate representation rules pending the approval points in
Section 11. They do not authorize implementation.

## 7. Deterministic fail-closed behavior

G1 must fail closed for:

- missing predecessor artifacts;
- unsupported predecessor, contract, evaluator, or policy versions;
- invalid types or non-canonical predecessor representations;
- missing, mismatched, cross-lifecycle, or ambiguous identity links;
- missing or mismatched predecessor digests;
- missing or contradictory provenance;
- a paper result not retained by the supplied P07-T07 history snapshot;
- an observation not retained by the supplied P08-T02 dataset snapshot;
- conflicting lifecycle or subject references;
- unsupported, unknown, unavailable, incomplete, or contradictory simulation
  states when the approved policy cannot establish recognition or finality;
- invalid or ambiguous finality conditions;
- future leakage or invalid temporal ordering;
- non-deterministic input ordering or snapshot state;
- an invalid G1 result identity or digest; and
- an unresolved correction or supersession context.

G1 must not:

- infer a missing paper fill, ledger entry, reconciliation result, or
  observation;
- convert P07-T06 `finalized` into settlement finality;
- convert a paper amount or paper position into P&L, ROI, valuation, or cost
  basis;
- infer recognition from a positive or negative paper value;
- treat P08-T06 readiness as economic evidence;
- repair contradictory evidence;
- select a source by freshness, insertion order, amount, or caller preference;
- use a later artifact to mutate an earlier result;
- silently downgrade invalid input to non-final;
- silently upgrade non-final input to final; or
- create an ambient duplicate registry or persistence authority.

## 8. Correction and supersession relationship with Authority B

G1 results are immutable. A changed recognition or finality conclusion is a
new result with a new result identity; it is never an in-place edit.

Authority B retains sole ownership of correction and supersession facts:

```text
immutable G1 result predecessor
        ↓
Authority B correction/supersession fact
        ↓
immutable G1 result successor
        ↓
T07 lineage validation, if the approved adapter accepts the G1 result
```

G1 must not:

- create a `LineageFact`;
- choose `correction` versus `supersession`;
- mutate a predecessor result;
- select a canonical lineage head;
- resolve a branch, cycle, merge, or conflicting duplicate;
- redefine the Authority A lifecycle; or
- make the corrected/superseded result economically realized.

Authority B must preserve the established Authority A lifecycle identity and
the immutable G1 result identities. Any direct G1-to-Authority-B adapter and
the exact T07 destination remain approval points; this proposal does not
change Authority B ownership or its audited implementation.

## 9. Exact output boundary into future G2

The only G1 semantic assertion available to G2 is:

```text
G1 may say only whether one simulation lifecycle is
economically recognized under the simulation-only contract and whether
that simulation lifecycle is final under the approved simulation policy.
```

G1 must not decide:

- whether the lifecycle is realization-eligible;
- whether any external execution occurred;
- whether any settlement occurred;
- whether any value is realized;
- whether accounting inputs are admissible;
- any accounting basis, cost basis, numeraire, conversion, precision, or
  rounding;
- any valuation;
- P&L, ROI, or performance;
- `WIN`, `LOSS`, or `BREAKEVEN`;
- custody, wallet, account ownership, provider truth, or capital state; or
- any Risk Governor, execution, signing, broadcast, or P09 step.

The candidate G2 input is the immutable G1 result identity, recognition state,
finality state, provenance, and digest. G2 must apply its own separately
approved realization-eligibility contract and must not infer a G2 decision
from a G1 `FINAL` state alone.

## 10. Required future verification and test plan

No tests are created by this proposal. If G1 receives separate implementation
authorization, the focused test plan must include at least:

1. **Valid predecessor chain** — one complete P06/P07/P08 chain produces the
   approved recognized state and preserves every identity and digest.
2. **Finality matrix** — approved terminal, open, partial-fill, unfilled,
   unknown, unavailable, failure, and reconciliation-disagreement simulation
   states map to the approved recognition/finality results.
3. **Broken linkage** — every required identity mismatch, missing artifact,
   cross-lifecycle reference, and history/snapshot membership failure fails
   closed.
4. **Provenance and digest integrity** — tampered, missing, reordered, or
   unsupported predecessor representations fail closed.
5. **Canonicalization** — equivalent inputs produce identical canonical bytes,
   result identity, and result digest.
6. **Replay** — repeated evaluation, equivalent snapshot ordering, and
   different processing order produce identical results without a clock.
7. **Temporal safety** — future leakage, invalid inherited timestamps, local
   timezone, wall-clock, and post-result mutation cannot affect output.
8. **Immutability** — result objects, nested provenance, and supplied
   predecessor artifacts cannot be mutated through the G1 boundary.
9. **Correction/supersession** — G1 creates no lineage fact and preserves
   immutable result identities for an explicitly supplied Authority B context.
10. **Negative authority checks** — no accounting, valuation, P&L, ROI,
    classification, settlement, provider, wallet, execution, capital, or
    P09 behavior is reachable.
11. **Dependency boundary** — the future public module has no clock, random,
    environment, filesystem, network, provider, database, persistence, wallet,
    execution, or API dependency.

## 11. Open approval points

The following details cannot be proven from the existing closed contracts and
must be approved before an implementation-ready specification or implementation
authorization:

1. The exact public field names and types for Authority A subject and lifecycle
   identity references, because Authority A implementation remains unauthorized.
2. Whether G1 receives complete nested predecessor objects, immutable
   materialized references, or both.
3. The exact supported predecessor version set and the G1 contract/evaluator
   version strings.
4. Whether every P08-T01 through P08-T06 artifact is a required G1 validation
   input or whether some are provenance-only references after P08-T01.
5. The exact terminal P07 simulation-state vocabulary that permits G1
   `FINAL`.
6. Whether partial fills, unfilled quantities, paper reconciliation
   disagreement, `UNKNOWN`, `UNAVAILABLE`, `INCOMPLETE`, and failed simulation
   states are `NON_FINAL` or `NOT_RECOGNIZED`.
7. Whether a complete lifecycle may be recognized when the P07 simulation is
   non-final, or whether recognition itself requires a terminal simulation
   state.
8. Whether P08-T02 `as_of_time` is the sole G1 input cutoff or whether a
   separate explicit G1 evaluation cutoff is required.
9. Which inherited timestamps are required in the G1 representation and which
   are provenance-only.
10. The exact G1 reason-code vocabulary and failure-precedence order.
11. The exact canonical serialization profile, nullable-field rules, array
    ordering, Unicode rules, and digest coverage.
12. The exact G1 result identity projection and domain-separated digest prefix.
13. Whether a G1 result identity is directly eligible as an Authority B
    predecessor/successor identity or must first be wrapped by a T07 result.
14. The exact G1-to-Authority-B adapter fields and whether T07 accepts that
    lineage without any T07 contract change.
15. Whether duplicate comparison is needed at G1's value boundary and, if so,
    which explicit immutable snapshot supplies that comparison without
    introducing ambient persistence.
16. The exact provenance envelope and G1 authority identity/version representation.
17. The exact public naming and placement of the future implementation module
    and test module listed below.

These are approval points, not defaults. No missing decision may be inferred
from P07 finalization, P08 readiness, paper quantities, or T07's downstream
contract.

## 12. Required future implementation files

If and only if this proposal is approved, separately authorized, and converted
into an implementation-ready specification, the candidate implementation scope
is:

```text
core/learning/g1_simulation_only_economic_authority.py
tests/test_g1_simulation_only_economic_authority.py
```

No file in this list was created by this proposal. No package, export,
dependency, migration, API, workflow, or runtime change is authorized.

## 13. Complete prohibited behavior

G1 is prohibited from:

- real-money behavior or live trading;
- external economic truth or external settlement claims;
- provider, RPC, DEX, exchange, network, or external API access;
- custody, wallet, account ownership, private keys, signers, signing, or
  broadcast;
- execution requests or execution behavior;
- Risk Governor decisions or capital authorization;
- settlement or external-finality integration;
- valuation, accounting, P&L, ROI, cost basis, numeraire, conversion,
  precision, rounding, or economic-result calculation;
- `WIN`, `LOSS`, `BREAKEVEN`, or any performance classification;
- G2 realization-eligibility decisions;
- G3 accounting/economic-result decisions;
- G4 classification decisions;
- P08-T07 redesign or canonical-head selection;
- Authority A identity creation, mutation, split, merge, or redefinition;
- Authority B correction/supersession fact creation or branch resolution;
- persistence, migrations, caches, queues, ambient registries, or database
  authority;
- model training, strategy updates, parameter updates, or learning behavior;
- fetching, reconstructing, repairing, or substituting missing evidence; and
- P09 behavior of any kind.

The existence of a paper result, readiness result, G1 `FINAL` state, or G1
documentation approval does not waive any prohibition.

## 14. Proposal conclusion

This proposal defines a candidate simulation-only G1 boundary over one complete
paper-simulation lifecycle. It supplies future G2 only with recognition and
simulation-finality states, provenance, identities, and digests. It supplies no
settlement, realization, accounting, valuation, classification, provider,
wallet, execution, capital, or P09 authority.

```text
G1 SIMULATION-ONLY SPECIFICATION
    = PROPOSAL / AWAITING OWNER APPROVAL

G1 IMPLEMENTATION
    = NOT AUTHORIZED

G2 / G3 / G4 / P09
    = NOT AUTHORIZED
```