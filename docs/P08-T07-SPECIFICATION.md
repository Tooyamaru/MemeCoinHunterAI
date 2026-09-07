# P08-T07 — Economic Outcome Interpretation Boundary

**Status:** SPECIFICATION DRAFT / IMPLEMENTATION NOT AUTHORIZED
**Phase:** P08 — Outcome Learning
**Task:** P08-T07 — Economic Outcome Interpretation
**Contract:** UNRESOLVED / REQUIRES GOVERNANCE DECISION
**Evaluator:** UNRESOLVED / REQUIRES GOVERNANCE DECISION
**Nature:** Proposed immutable, deterministic, provider-neutral, read-only
boundary; no runtime behavior is authorized by this document

## 1. Purpose

P08-T07 is a proposed downstream boundary for the separately governed
interpretation of economic outcomes associated with the already validated
P06 → P07 → P08 evidence chain.

This document exists to define the ownership boundary, admissibility
requirements, and unresolved governance parameters that must be settled before
P08-T07 can be implemented. T07 does not create economic truth itself:
economic truth must come from explicitly governed and admissible economic
evidence. This document does not authorize a runtime implementation.

The current governance direction establishes the following boundary:

> P08-T07 owns economic outcome interpretation, including realized P&L when
> admissible, and may derive an approved target classification from economic
> facts through deterministic calculation. It must consume validated upstream
> records and explicitly governed economic evidence; it must not create
> economic truth, and its exact implementation semantics still require
> governance approval.

No runtime economic conclusion is authorized by this draft.

### 1.1 Non-overlap with existing P08 boundaries

P08-T07 must not duplicate or absorb the responsibility of any predecessor:

| Boundary | Existing responsibility | P08-T07 must not replace |
|---|---|---|
| P08-T01 Observation | Preserves the point-in-time link between the decision and the canonical P07 paper result. | Observation identity, decision linkage, or P07 fact ownership. |
| P08-T02 Dataset Snapshot | Owns dataset membership, ordering, duplicate rejection, and the `as_of_time` cutoff. | Dataset membership, cutoff authority, or snapshot construction. |
| P08-T03 Interpretation | Assigns only evidence-state interpretation such as `UNCLASSIFIED`, `UNKNOWN`, `UNAVAILABLE`, and `INCOMPLETE`. | The evidence-state taxonomy or a financial meaning for those states. |
| P08-T04 Evidence Evaluation | Validates linkage, completeness, admissibility, and internal consistency of an individual interpretation. | P07 recalculation, reconciliation, settlement truth, or economic performance. |
| P08-T05 Evaluation Snapshot | Assembles the complete one-to-one T04 evaluation set into an immutable snapshot. | Collection membership, T04 state replacement, or snapshot identity. |
| P08-T06 Readiness | Emits only `READY_FOR_NON_ECONOMIC_ANALYSIS` or `NOT_READY_FOR_NON_ECONOMIC_ANALYSIS`. | Economic readiness, profitability, sample sufficiency, or authorization. |

P08-T07 is therefore not an alternative observation, dataset, evidence-state,
evaluation, snapshot, or readiness boundary. Any future T07 contract must
consume and preserve the validated predecessor chain rather than bypassing,
reconstructing, or weakening it.

### 1.2 Current governance position

The current state is:

- P07-T01 through P07-T07 are complete, closed, and audited PASS.
- P08-T01 through P08-T05 are complete, closed, and audited PASS.
- P08-T06 is implemented, audited PASS, and remains a non-economic readiness
  boundary.
- P08-T07 has no approved implementation contract.
- P09 remains separately governed and unauthorized.

The P08 next-boundary proposal is candidate scope, not authorization. Its
references to wins, losses, expectancy, drawdown, slippage, latency, cost,
attribution, drift, or validation do not define their semantics.

## 2. Economic Outcome Boundary

### 2.1 What the existing chain establishes

The existing chain establishes immutable paper-simulation facts, evidence
linkage, evidence-state interpretation, evidence evaluation, collection
integrity, and non-economic readiness. It does not establish:

- market settlement truth;
- a future-price or target/stop event window;
- an economic valuation source;
- an authoritative accounting numeraire;
- a fee, spread, slippage, latency, price-impact, MEV, or infrastructure-cost
  source for economic analysis;
- a benchmark or counterfactual;
  - a strategy-performance definition; or
  - an approved economic outcome classification rule.

P07-T06's word **finalized** means that the validated paper simulation,
paper-state, ledger, and reconciliation records were assembled into one
canonical non-economic result. It does not mean economically finalized,
settled, profitable, loss-making, or classified as `WIN` or `LOSS`.

P08-T06's `READY_FOR_NON_ECONOMIC_ANALYSIS` means only that the validated T05
evidence set contains no explicit T04 `UNKNOWN`, `UNAVAILABLE`, or `INCOMPLETE`
state under the T06 predicate. It does not mean economically evaluable,
sufficiently sampled, profitable, or ready for promotion or execution.

### 2.2 Economic concept decision matrix

The ownership decisions below are now settled. Exact evidence, formulas,
parameters, and field-level semantics remain subject to governance review.

| Concept | Ownership / boundary | Authoritative source | Required input evidence | Unit / precision | Temporal meaning | Current status |
|---|---|---|---|---|---|---|
| `WIN` | T07 target classification derived from economic facts, never a primitive fact. | Governed economic evidence plus the approved calculation/classification contract. | Admissible realized or other explicitly approved economic facts. | **GOVERNANCE PARAMETER REQUIRED** | Must use the approved horizon and endpoint. | Numeric threshold and exact rule remain open. |
| `LOSS` | T07 target classification derived from economic facts, never a primitive fact. | Governed economic evidence plus the approved calculation/classification contract. | Admissible realized or other explicitly approved economic facts. | **GOVERNANCE PARAMETER REQUIRED** | Must use the approved horizon and endpoint. | Numeric threshold and exact rule remain open. |
| Realized P&L | Core T07 economic output when based on admissible settled/realized evidence. | Explicitly governed settlement/realization authority. | Authoritative quantities, prices, costs, fees, and settlement evidence. | Accounting basis, numeraire, precision, and rounding are **GOVERNANCE PARAMETER REQUIRED**. | Only after the required endpoint/horizon is satisfied. | Ownership settled to T07; exact semantics remain open. |
| Valuation / mark-to-market | Distinct interpretation type; must not be mixed with realized P&L. | Explicitly governed valuation evidence and authority. | Approved valuation observations with timestamp and provenance. | **GOVERNANCE PARAMETER REQUIRED** | Must be labeled as valuation and use its own approved endpoint semantics. | T07 may support it only if separately authorized; not realized P&L. |
| Return | Broader derived metric, not mandatory core T07 responsibility. | **UNRESOLVED / REQUIRES GOVERNANCE DECISION** | **UNRESOLVED / REQUIRES GOVERNANCE DECISION** | **GOVERNANCE PARAMETER REQUIRED** | **GOVERNANCE PARAMETER REQUIRED** | Outside core T07 unless separately approved. |
| ROI | Broader performance metric, not mandatory core T07 responsibility. | **UNRESOLVED / REQUIRES GOVERNANCE DECISION** | **UNRESOLVED / REQUIRES GOVERNANCE DECISION** | **GOVERNANCE PARAMETER REQUIRED** | **GOVERNANCE PARAMETER REQUIRED** | Outside core T07. |
| Outcome horizon | Required T07 temporal boundary, not an economic result itself. | Timestamp authority and endpoint authority must be governed. | Upstream reference time plus approved economic event/settlement evidence. | Exact duration or event rule is **GOVERNANCE PARAMETER REQUIRED**; no default is allowed. | Reference, start, endpoint, inclusion, and replay semantics are required. | T07 owns the requirement; exact parameters remain open. |
| Trade result | T07 may own the economic result interpretation unit when explicitly defined. | **GOVERNANCE PARAMETER REQUIRED** | Validated upstream chain plus admissible economic evidence. | **GOVERNANCE PARAMETER REQUIRED** | Must be bound to an approved horizon. | Cardinality and exact semantics remain open. |
| Economic performance | Broader portfolio/strategy performance analysis. | **UNRESOLVED / REQUIRES GOVERNANCE DECISION** | **UNRESOLVED / REQUIRES GOVERNANCE DECISION** | **GOVERNANCE PARAMETER REQUIRED** | **GOVERNANCE PARAMETER REQUIRED** | Outside core T07. |
| Strategy attribution | Not a T07 responsibility; strategy/model/regime identity may be preserved as provenance only. | N/A for T07 attribution. | Decision and strategy/model version identities may be preserved. | N/A for T07 attribution. | N/A for T07 attribution. | Explicitly outside T07. |

The same non-core status applies to `BREAKEVEN`, expectancy, drawdown,
profitability, economic edge, missed opportunity, avoided loss, benchmark
performance, counterfactual performance, regime attribution, model
attribution, and challenger/production comparison. Their ownership and
semantics require separate governance; they are not implied by T07 ownership
of economic interpretation or realized P&L.

### 2.3 Boundary conclusion

The ownership decisions are settled as follows:

1. T07 is the economic outcome interpretation boundary.
2. Realized P&L is a core T07 output when admissible settled/realized evidence
   and the approved accounting basis are present.
3. `WIN` and `LOSS` are approved target classification concepts, derived from
   economic facts through deterministic calculation; they are not primitive
   economic truth.
4. Mark-to-market/valuation is distinct from realized P&L and must not be
   mixed with it.
5. Return, ROI, and broader performance aggregation are not mandatory core T07
   responsibilities.
6. Strategy, model, and regime attribution are outside T07; relevant version
   identities may be preserved as provenance only.

The remaining open decisions concern the evidence source, settlement authority,
horizon parameters, accounting and calculation semantics, classification
thresholds, output schema, and failure taxonomy.

## 3. Provenance and ownership

### 3.1 Required provenance chain

Any future T07 contract must preserve the complete chain without shortcuts:

```text
P06 DecisionIntent
→ P07-T01 SimulationInput
→ P07-T02 FillOutcome
→ P07-T03 Position / Exposure State
→ P07-T04 Paper Ledger
→ P07-T05 Paper Reconciliation
→ P07-T06 canonical finalized NON-ECONOMIC PaperSimulationResult
→ P07-T07 PaperSimulationResultHistory
→ P08-T01 Observation
→ P08-T02 DatasetSnapshot
→ P08-T03 Interpretation
→ P08-T04 EvidenceEvaluation
→ P08-T05 EvaluationSnapshot
→ P08-T06 Readiness
→ P08-T07
```

The P07-T06 and P07-T07 records remain paper-simulation records. They must not
be relabeled as settlement or economic records merely because they are
upstream of T07.

### 3.2 Ownership preservation

Ownership remains:

- P06 owns the decision intent and its decision identity.
- P07 owns paper simulation, fills, paper positions, exposure, ledger,
  reconciliation, canonical paper results, and local result history.
- P08-T01 owns the decision-to-paper-result observation link.
- P08-T02 owns dataset membership and the dataset cutoff.
- P08-T03 owns evidence-state interpretation.
- P08-T04 owns individual evidence evaluation.
- P08-T05 owns complete evaluation collection assembly and snapshot identity.
- P08-T06 owns only the structural non-economic readiness predicate.
- P08-T07 owns the economic outcome interpretation boundary, including
  realized P&L when admissible and approved target classification derived from
  economic facts. It does not own economic truth, which remains with the
  explicitly governed evidence authority.
- P09 owns a separately governed live execution chain and is not a T07
  downstream implementation detail.

T07 must not recalculate or replace any upstream fact. In particular, it must
not re-simulate fills, rebuild paper positions, rebuild the ledger, redo
reconciliation, or reinterpret paper statuses as economic success or failure.

### 3.3 No provenance shortcut

A future T07 operation must not accept raw P07 or raw P08 material as a
substitute for validated predecessor contracts. It must not reconstruct
missing predecessor values from identifiers, fetch missing artifacts, repair
invalid digests, or silently replace an upstream object with a caller-created
approximation.

## 4. Candidate immutable inputs

There is no approved T07 input schema. The following distinction is mandatory
for the next architecture review, but is not an authorized runtime field list.

### 4.1 Predecessor inputs

T07 input design must distinguish two separate input classes:

**A. Validated upstream P08 chain**

- exactly one validated P08-T06 readiness result;
- the exact P08-T05 snapshot referenced by that result;
- the validated P08-T02 dataset and its T02 cutoff;
- the P08-T01 observations; and
- preserved P06/P07 provenance.

**B. Separately governed economic evidence**

- an explicitly identified economic-evidence artifact or immutable collection;
- its authority, provenance, timestamp, version, and integrity/digest; and
- its approved admissibility and replay semantics.

T07 must not treat the T06 readiness state as economic evidence. T07 must not
reconstruct missing upstream data or fetch or collect economic evidence itself.
The exact input shape, cardinality, and artifact-resolution rule are
**GOVERNANCE PARAMETER REQUIRED**.

### 4.2 Identity and integrity requirements

Before implementation authorization, governance must define which of the
following are authoritative inputs and how each is represented:

| Identity or value | Current status |
|---|---|
| Decision identity and digest | Preserved upstream; exact T07 input requirement is to be approved. |
| Simulation identity and digest | Preserved upstream; exact T07 input requirement is to be approved. |
| Paper result and history identities | Preserved upstream; not economic settlement authority. |
| Observation identity and digest | Preserved upstream; exact T07 linkage requirement is to be approved. |
| Dataset identity and digest | T02-owned; T02 remains cutoff and membership authority. |
| T06 readiness identity and digest | T06-owned; readiness has no economic meaning. |
| Economic evidence artifact identity | **GOVERNANCE PARAMETER REQUIRED** |
| Contract and evaluator versions | T07 values are not assigned. |
| Evidence-source versions | **GOVERNANCE PARAMETER REQUIRED** |
| Observation and event timestamps | Upstream timestamps are preserved; economic event semantics are unresolved. |
| Dataset `as_of_time` / cutoff | T02-owned and must not be silently replaced. |
| Economic evaluation cutoff | **GOVERNANCE PARAMETER REQUIRED** |
| Evidence/admissibility state | **GOVERNANCE PARAMETER REQUIRED** |

No additional field is approved merely because it might be useful.

### 4.3 Economic evidence admission

The current contracts do not identify an authoritative source for:

- settlement events;
- future prices;
- target or stop events;
- fees or priority fees;
- spread or slippage;
- price impact or liquidity;
- latency or infrastructure cost;
- venue or chain truth;
- benchmark values; or
- counterfactual opportunity values.

Any economic evidence admitted by T07 must have:

- explicit authority and an identified owner;
- a stable identity;
- complete provenance;
- an authoritative timestamp;
- a source and contract version;
- an integrity or digest value;
- explicit admissibility rules; and
- deterministic replay semantics.

The exact evidence type, source, settlement authority, and admissibility rules
are **GOVERNANCE PARAMETER REQUIRED**. No provider, network, RPC, DEX, wallet,
database, or external authority may be used by a future implementation unless
a separate approved contract explicitly changes this boundary.

## 5. Temporal and outcome-horizon semantics

### 5.1 Distinct time concepts

The following time concepts must not be conflated:

- P06 decision time;
- P07 simulation reference time;
- P08-T01 observation time;
- P08-T02 dataset `as_of_time`;
- any economic evidence observation time;
- any economic event or settlement time;
- any evaluation cutoff; and
- any outcome endpoint or horizon.

P08-T02 owns the current dataset cutoff. That cutoff is not, by itself, an
economic outcome horizon.

### 5.2 Horizon is required; exact parameters are not defined

T07 requires an explicit outcome horizon before an economic result can be
final. The current architecture does not define its exact immutable
future-price window, target/stop event stream, settlement endpoint, benchmark
period, or other economic horizon. T07 must not invent a duration, default
endpoint, timezone, or wall-clock rule.

The following are required horizon components and remain
**GOVERNANCE PARAMETER REQUIRED**:

- the reference time for an economic interpretation;
- the start time;
- the observation-time source and precedence;
- the relationship to the dataset cutoff;
- the endpoint and endpoint semantics;
- fixed-duration versus event-terminated horizons;
- endpoint inclusion and exclusion;
- settlement versus mark-to-market endpoint rules;
- timezone and UTC normalization rules;
- handling of late, revised, or corrected evidence;
- the timestamp authority;
- whether incomplete horizons produce a non-final state or no result; and
- whether multiple horizons are allowed.

P08-T02 `as_of_time` remains the upstream dataset cutoff and is not
automatically the T07 economic outcome horizon.

### 5.3 Temporal safety requirements

If a future T07 contract is authorized, it must:

- reject future leakage rather than silently excluding future evidence;
- define allowed timestamp ordering explicitly;
- reject or explicitly classify events outside the approved horizon;
- prevent post-outcome labels from entering pre-outcome evidence;
- prevent local timezone, process time, insertion time, or wall-clock time from
  changing a result;
- preserve all source timestamps and their authority; and
- make replay independent of when or where it is executed.

These are design constraints; the exact horizon parameters remain
**GOVERNANCE PARAMETER REQUIRED**.

## 6. Economic calculation semantics

Realized P&L is a core T07 economic output when all required settled/realized
evidence is admissible. T07 must not treat paper simulation as economic truth,
and must not treat an open or incomplete position as realized P&L or `WIN` /
`LOSS`.

The following exact calculation dimensions are
**GOVERNANCE PARAMETER REQUIRED** before implementation:

| Calculation dimension | Required decision |
|---|---|
| Accounting basis | Which settled economic events establish realized accounting facts. |
| Quantity basis | How filled, partially filled, unfilled, open, closed, and residual quantities are treated. |
| Price basis | Which observed, settled, quoted, marked, or benchmark price is authoritative. |
| Cost basis | How acquisition cost, notional, capital, collateral, and denomination are defined. |
| Fees and friction | Whether fees, spread, slippage, price impact, priority fees, MEV, latency, and infrastructure cost are included and where their evidence comes from. |
| Currency / numeraire | The accounting unit, conversion source, conversion time, and treatment of unavailable conversion. |
| Formula | The exact formula for each metric, including sign convention. |
| Precision | Exact numeric representation, scale, permitted range, and overflow behavior. |
| Rounding | The rounding mode, point at which rounding occurs, and replay behavior. |
| Partial fills | Whether and how partial fills can receive an economic interpretation. |
| Incomplete positions | Whether open or incomplete positions are admissible and what endpoint closes them. |
| Zero denominator | Whether the result is rejected or receives an explicitly approved undefined state. |
| Missing evidence | Whether no result, an unavailable state, or another approved state is emitted. |
| Contradictory evidence | Which source wins, or whether contradiction always fails closed. |
| Settlement | Whether economic truth requires actual settlement and who attests to it. |
| Counterfactual | Whether counterfactual performance is permitted and how it is observed. |

T07 may emit realized P&L only when:

- economic evidence is explicitly governed and admissible;
- quantities, prices, costs, and settlement facts are authoritative;
- the accounting basis and numeraire are defined;
- precision and rounding are defined;
- the required endpoint/horizon is satisfied; and
- the position is not open or incomplete under the approved semantics.

Where an exact numeric rule is not authoritative, the specification must use
the marker `GOVERNANCE PARAMETER REQUIRED`; implementation must not supply a
default.

## 7. Outcome classification

### 7.1 Approved target-classification concept; exact rule remains open

`WIN` and `LOSS` are approved target classification concepts for T07. They are
not primitive economic truth and must never be derived directly from a paper
result:

```text
economic facts
→ deterministic calculation
→ approved classification
```

The exact numeric threshold, tie/breakeven semantics, and classification
parameters are `GOVERNANCE PARAMETER REQUIRED`. Other possible states remain
subject to the output and failure taxonomy decision:

```text
WIN
LOSS
BREAKEVEN
UNKNOWN
UNAVAILABLE
INCOMPLETE
INVALID
```

Existing P07 and P08 statuses must not be reused as economic labels without an
explicit governance decision. In particular:

- `FILLED` does not mean `WIN`;
- `FAILED` or `REJECTED` does not mean `LOSS`;
- `PARTIAL` does not define a financial result;
- `UNAVAILABLE` does not define a market loss;
- `RECONCILED` does not define settlement or profit; and
- `READY_FOR_NON_ECONOMIC_ANALYSIS` does not define economic admissibility.

### 7.2 Required classification decisions

For the approved target classification, governance must define:

- the exact value vocabulary;
- deterministic admissibility requirements;
- the evidence needed for each value;
- precedence when multiple evidence states coexist;
- treatment of partial, failed, rejected, open, unavailable, unknown, and
  contradictory cases;
- whether a classification is descriptive only; it must not have execution,
  capital, model, or strategy authority;
- whether a classification is per decision, fill, position, trade, horizon,
  dataset, strategy, or another unit; and
- the version and digest semantics of the classification rule.

T07 owns classification application after these parameters are approved. This
draft does not authorize its runtime implementation.

## 8. Determinism and canonicalization

Any future T07 implementation must be pure, immutable, provider-neutral,
read-only, and deterministic over explicitly supplied validated inputs.

Equivalent validated inputs must produce equivalent semantic output, canonical
representation, and digest. The operation must not depend on:

- wall-clock time;
- randomness;
- process identity or memory address;
- filesystem state;
- database state;
- network or provider state;
- insertion order;
- local timezone;
- hidden configuration; or
- external assertions not present in the approved input contract.

### 8.1 Canonicalization decisions still open

The following exact details remain **UNRESOLVED / REQUIRES GOVERNANCE
DECISION**:

- the public output field set;
- field names and field ordering;
- canonical enum and classification serialization;
- decimal representation and scale;
- treatment of negative zero, NaN, infinity, and overflow;
- timestamp serialization and timezone normalization;
- event ordering when timestamps tie;
- collection ordering and duplicate identity;
- canonical representation of external evidence;
- digest algorithm and digest coverage;
- version inclusion in the digest;
- whether source artifacts are embedded or referenced by digest; and
- replay equivalence rules for corrected or superseded evidence.

The future contract must not rely on language-specific object ordering or
implementation-specific numeric serialization.

## 9. Failure and fail-closed behavior

The draft requires that no economic conclusion be produced unless all required
predecessor and economic evidence is admissible, linked, canonical, and
temporally valid.

### 9.1 Conditions that must not produce an economic conclusion

The future contract must fail closed for at least:

- missing predecessor evidence;
- incomplete predecessor evidence;
- unavailable required economic evidence;
- contradictory source values;
- invalid artifact or observation linkage;
- invalid or mismatched digest;
- unsupported contract or evaluator version;
- non-canonical source representation;
- stale reference data;
- unsatisfied outcome horizon;
- temporal ordering violation;
- future leakage;
- missing settlement or valuation authority;
- undefined calculation or zero denominator;
- unsupported unit or currency conversion;
- invalid quantity or position state;
- ambiguous partial-fill treatment;
- invalid classification input; and
- any unapproved external authority assertion.

### 9.2 Failure taxonomy is not approved

The exact public failure taxonomy, reason-code vocabulary, and distinction
between rejected input, unavailable evidence, incomplete horizon, invalid
calculation, and valid non-conclusion remain **UNRESOLVED / REQUIRES GOVERNANCE
DECISION**.

Until that taxonomy is approved, the only permitted draft-level behavior is:

> reject or withhold the economic conclusion; do not infer, impute, coerce,
> filter, repair, downgrade, upgrade, or silently substitute evidence.

An implementation must not turn an unresolved failure into `WIN`, `LOSS`,
profit, return, ROI, or any other economic metric.

## 10. Authority boundary

P08-T07 must remain strictly read-only and must not:

- execute paper or live trades;
- access wallets;
- sign transactions;
- broadcast transactions;
- call RPCs, DEXs, exchanges, or providers;
- authorize capital;
- override Risk/Capital Authorization;
- modify or reinterpret `DecisionIntent`;
- modify P07 fills, positions, exposure, ledger, reconciliation, results, or
  history;
- modify P08-T01 through P08-T06 artifacts;
- recalculate paper fills, fees, slippage, latency, or reconciliation;
- retrain, fit, evaluate for promotion, or update a model;
- update a strategy, threshold, weight, parameter, or risk limit;
- optimize parameters;
- perform strategy or model learning;
- rank, select, prioritize, or promote decisions;
- become a P09 execution boundary;
- create production authority;
- create external side effects; or
- treat an economic interpretation as authorization to act.

Any future model, strategy, parameter, risk, capital, or execution effect
requires its own separately reviewed and authorized boundary.

## 11. P08-T07 versus P09

P08-T07, if authorized, would be a read-only interpretation boundary over
validated evidence. Its potential output would describe or classify an
economic interpretation according to an explicitly approved contract. It would
not submit an order, reserve capital, sign, broadcast, reconcile live
execution, or write a journal entry.

P09 remains a separately governed execution phase. The architecture preserves
the mandatory chain:

```text
Decision Intent
→ Risk / Capital Authorization
→ Execution Request
→ isolated Signing
→ Broadcast
→ Reconciliation
→ Journal
```

T07 must not create a shortcut into any P09 step. A T07 result must not
authorize P09, imply model promotion, or change strategy behavior. Any
controlled promotion path remains subject to separate review and explicit
authorization.

## 12. Candidate output contract

No public T07 output type, contract version, evaluator version, or exact field
list is approved. The semantic ownership of the output is nevertheless
settled. The following completeness checklist is for the next architecture
review, not an implementation contract.

| Output category | Required governance decision |
|---|---|
| Output identity | Define the identity unit and deterministic identity derivation. |
| Provenance identity | Preserve the complete P06 → P07 → P08-T06 chain and every required digest. |
| Source artifact identities | Define which upstream and economic-evidence artifact identities are mandatory. |
| Contract and evaluator versions | Assign supported versions and version-compatibility rules. |
| Timestamps | Define source, reference, event, cutoff, horizon, and output timestamp semantics. |
| Digest | Define canonical representation, algorithm, coverage, and replay rules. |
| Evidence/admissibility state | Define the exact taxonomy and whether it is separate from economic classification. |
| Economic outcome facts/results | T07-owned interpretation of explicitly governed economic evidence; exact fields and cardinality are **GOVERNANCE PARAMETER REQUIRED**. |
| Realized P&L | Core T07 output when admissible; exact accounting and numeric semantics are **GOVERNANCE PARAMETER REQUIRED**. |
| Valuation / mark-to-market | Distinct interpretation type if authorized; must not be mixed with realized P&L. |
| Classification | T07-owned application of approved `WIN` / `LOSS` target semantics; exact threshold and tie rules are **GOVERNANCE PARAMETER REQUIRED**. |
| Non-final / incomplete states | Must prevent realized P&L or `WIN` / `LOSS` for open, incomplete, unavailable, or unsatisfied-horizon cases; exact taxonomy is **GOVERNANCE PARAMETER REQUIRED**. |
| Return / ROI / performance metrics | Outside mandatory core T07; any later use requires a separately governed performance boundary. |
| Strategy/model/regime attribution | Outside T07; version identities may be preserved as provenance only. |
| Immutability | Define recursive immutability and source-alias behavior. |
| Cardinality | Define per-observation, per-decision, per-position, per-trade, or collection output. |
| Aggregation | Define whether any aggregation is allowed and its ordering and missing-data rules. |
| Authority effect | State explicitly that the output cannot authorize execution or model/strategy changes. |

The semantic ownership rows are settled; exact implementation details remain
open governance parameters.

## 13. Security and provider neutrality

T07 must be provider-neutral. A future implementation must operate only on
explicitly supplied, validated, immutable evidence and must not depend on
live-provider authority.

This draft does not authorize:

- network access;
- provider SDKs;
- RPC or DEX calls;
- exchange or venue queries;
- wallet access;
- signing or broadcast;
- database or persistence access;
- workers, queues, or caches; or
- external evidence collection.

If governance later determines that an external source is required, its
identity, authority, authentication boundary, timestamp semantics, versioning,
replay behavior, and failure rules require a separate approved contract.

## 14. Open governance decisions

The following decisions must be resolved before implementation authorization:

1. The authoritative economic evidence type/source and its owner.
2. The settlement authority and the evidence that establishes realized status.
3. Whether paper simulation can ever be economic evidence; the current
   boundary says paper simulation is not economic truth.
4. Whether valuation/mark-to-market evidence is admissible as a distinct
   interpretation type and under what
   restrictions.
5. The exact horizon parameters: reference time, start time, endpoint,
   endpoint semantics, timestamp authority, inclusion/exclusion, and replay.
6. The accounting basis, quantity basis, price basis, and cost basis.
7. The treatment of fees, spread, slippage, latency, price impact, MEV,
   priority fees, and infrastructure cost.
8. The currency/numeraire, conversion source, conversion semantics, precision,
   scale, sign convention, and rounding.
9. The realized P&L formulas and undefined/zero-denominator behavior.
10. The exact definition of trade result and the unit of outcome.
11. The exact `WIN` / `LOSS` classification threshold, tie/breakeven semantics,
    and classification rule version.
12. The definitions and formulas for return, ROI, expectancy, drawdown,
   profitability, and economic edge.
13. The definition and admissibility of missed opportunity and avoided loss;
    these remain outside core T07 unless separately governed.
14. The handling of partial fills, open positions, failed attempts, rejected
    decisions, unavailable evidence, and reconciliation disagreement.
15. The exact evidence/admissibility state taxonomy and failure taxonomy.
16. The input cardinality and whether T07 consumes a T06 result, T05 snapshot,
    governed evidence packet, or fully explicit immutable bundle.
17. The exact output identity, fields, versions, digest, canonicalization, and
    immutable representation.
18. The relationship between T02 `as_of_time` and the T07 economic horizon.
19. The allowed ordering of observations and events, including tied timestamps.
20. Future-leakage, look-ahead, survivorship, selection, regime, and
    feedback-loop controls.
21. Missing, stale, unavailable, incomplete, contradictory, and superseded
    evidence semantics.
22. The exact digest coverage and replay equivalence rules.
23. The exact fail-closed taxonomy and whether an invalid input produces no
    result or an explicit non-economic rejection record.
24. Whether any aggregation, comparison, ranking, confidence interval,
    walk-forward analysis, drift analysis, or sample sufficiency measure is
    within T07; broader performance remains outside core T07.
25. The separate review required before any model, strategy, parameter, risk,
    capital, or execution effect.
26. The independent architecture and implementation authorization gates.

Each remaining parameter is a blocking decision. It must not be resolved by
implementation convention, a default value, a provider response, or an
assumption inherited from paper simulation.

## 15. Future implementation authorization gate

Implementation remains prohibited until all of the following are complete:

1. The economic purpose and non-overlap boundary are approved.
2. Every authoritative input and output field is specified.
3. Economic evidence ownership and admissibility are approved.
4. Horizon, cutoff, endpoint, replay, and future-leakage semantics are
   approved.
5. Units, formulas, precision, rounding, sign conventions, and undefined
   cases are approved.
6. Realized P&L semantics and `WIN` / `LOSS` classification parameters are
   approved; return, ROI, and broader performance metrics are explicitly
   excluded or separately governed.
7. Provenance, versions, canonicalization, ordering, and digest coverage are
   approved.
8. Fail-closed and missing-data behavior is approved.
9. P07 and P08-T01 through T06 ownership is explicitly preserved.
10. P09, model, strategy, risk, capital, and execution exclusions are
    explicitly preserved.
11. A separate implementation authorization is recorded.
12. Focused validation and regression requirements are specified after, not
    before, the contract is approved.

This draft itself satisfies none of those implementation-authorization
conditions.

## 16. Specification draft conclusion

P08-T07 is not yet a complete executable contract. Governance now establishes
T07 as the read-only economic outcome interpretation boundary, with realized
P&L as a core output when admissible and `WIN` / `LOSS` as target
classifications derived from economic facts. The current repository still does
not define the economic evidence authority, settlement authority, exact
horizon parameters, formulas, numeric rules, output shape, or failure taxonomy
required to implement it safely.

The correct current behavior is therefore:

- preserve all upstream non-economic semantics;
- keep all unresolved calculation and admissibility parameters explicit;
- distinguish settled/realized P&L from valuation/mark-to-market;
- prevent open or incomplete positions from producing realized P&L or `WIN` /
  `LOSS`;
- derive `WIN` / `LOSS` only from economic facts through deterministic
  calculation;
- keep return, ROI, strategy attribution, and broader performance analysis
  outside core T07;
- fail closed for any attempted unsupported economic conclusion;
- do not implement runtime behavior;
- do not change P07, P08-T01 through T06, or P09; and
- require a new governance decision before implementation authorization.

**FINAL STATUS: P08-T07 SPECIFICATION DRAFT — READY FOR SECOND ARCHITECTURE REVIEW**