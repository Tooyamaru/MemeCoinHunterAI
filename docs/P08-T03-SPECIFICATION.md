# P08-T03 — Outcome Interpretation Boundary

**Status:** SPECIFICATION DRAFT / IMPLEMENTATION NOT AUTHORIZED  
**Phase:** P08 — Outcome Learning  
**Task:** P08-T03  
**Contract:** `p08-t03-v1` (proposed)  
**Nature:** Immutable, deterministic, provider-neutral, read-only

## 1. Purpose and bounded responsibility

P08-T03 is proposed as the first outcome-interpretation boundary after the
validated P08-T02 dataset snapshot. Its purpose is to make the interpretation
of already-recorded outcome evidence explicit and auditable without silently
turning paper status into financial performance.

The narrowest defensible responsibility is a per-observation, read-only
interpretation record. It may state whether an observation is interpretable and
preserve the evidence state, but it must not claim WIN, LOSS, MISSED
OPPORTUNITY, AVOIDED LOSS, profit, expectancy, or edge until governance
approves the required evidence and evaluation horizon.

This boundary belongs after T02 because T02 provides the immutable,
point-in-time, duplicate-free collection and its source digests. T03, if
approved, would interpret that fixed evidence without changing membership or
provenance. It must not rebuild a dataset or fetch additional evidence.

## 2. Input contract

The sole currently justified input is exactly one validated:

```python
dataset: OutcomeLearningDatasetSnapshot
```

The input must use the supported P08-T02 contract `p08-t02-v1`, contain
validated P08-T01 observations, and retain its canonical dataset digest and
ordered observation digests. T03 must revalidate the dataset from its canonical
representation before any interpretation.

Every output record must preserve, at minimum:

- the source dataset digest;
- the source observation digest;
- candidate identity and point-in-time timestamps;
- the complete source observation or an identity-preserving reference to it;
- P08-T01 and P08-T02 contract/evaluator versions; and
- the T03 contract/evaluator versions.

No external evidence is currently allowed in T03. The existing P08 contracts do
not define an immutable future-price window, target/stop event stream, fee
source, venue truth, or benchmark. Adding such evidence would be a separate
input contract and requires separate approval.

## 3. Outcome taxonomy

### 3.1 What the current evidence supports

The existing records provide paper simulation status and reconciliation status,
not a verified economic result. The narrowest taxonomy justified without
inventing trading semantics is an evidence-interpretation state:

- `UNCLASSIFIED` — the observation is valid, but no approved outcome rule and
  evaluation horizon can assign an economic class;
- `UNKNOWN` — a required source state is explicitly unknown;
- `UNAVAILABLE` — a required source state is explicitly unavailable; and
- `INCOMPLETE` — required evidence for the approved interpretation is absent.

These values describe interpretability, not profitability. They must not be
collapsed into WIN or LOSS. A future approved T03 implementation may preserve
the source paper status (`FILLED`, `PARTIAL`, `FAILED`, `REJECTED`,
`UNAVAILABLE`, or `INVALID`) and reconciliation status (`RECONCILED`,
`DISAGREEMENT`, or `UNKNOWN`) as separate provenance fields.

### 3.2 Unresolved taxonomy decision

The repository does not justify selecting an economic taxonomy. Governance must
choose one of the following before implementation:

1. **Evidence-state only:** T03 emits only interpretability states and leaves
   WIN/LOSS semantics to a later analysis task.
2. **Per-observation economic class:** T03 emits an approved class such as WIN,
   LOSS, MISSED_OPPORTUNITY, AVOIDED_LOSS, PARTIAL, or UNCLASSIFIABLE.
3. **Two-axis result:** T03 preserves evidence state separately from an
   economic class, allowing a valid but non-classifiable observation.

The minimum decision required for authorization is the selected taxonomy,
including exact allowed values and whether classification is allowed for each
paper/reconciliation status. The current recommendation is option 1 or 3;
option 2 is not supportable until the horizon and evidence contract are
approved.

## 4. Evaluation horizon

No evaluation horizon is defined by P06, P07, P08-T01, or P08-T02. Therefore
T03 must not assign a time-based or price-based outcome in its current draft.

Governance must choose and specify one of these mechanisms before economic
classification is authorized:

- a fixed duration after `simulation_reference_time`;
- an explicit expiry timestamp;
- target/stop conditions evaluated against an immutable market-observation
  window; or
- another explicitly versioned, reproducible mechanism.

The choice must define the reference timestamp, required observations, end
condition, treatment of gaps, and precedence when multiple conditions occur.
Numerical durations, targets, stops, fees, slippage, or price sources cannot be
invented from the current repository.

Until that decision is made, the only valid T03 interpretation is
`UNCLASSIFIED`, `UNKNOWN`, `UNAVAILABLE`, or `INCOMPLETE` as applicable; no
future market data may be fetched or joined implicitly.

## 5. Missing and unknown information

T03 must preserve uncertainty and fail closed:

- `UNAVAILABLE` paper status remains `UNAVAILABLE`; it is never a win or loss.
- `UNKNOWN` reconciliation remains `UNKNOWN`; disagreement or lack of
  reconciliation is not economic evidence.
- `PARTIAL` results remain partial unless an approved rule states how partial
  evidence is interpreted.
- `FAILED` and `REJECTED` results remain their recorded paper states and do not
  imply a market loss.
- Incomplete price, horizon, target/stop, fee, slippage, or outcome evidence
  yields `INCOMPLETE` or the approved unknown state, never an imputed result.
- Invalid or tampered T02 input is rejected and produces no T03 output.

The specification must later decide whether a valid observation with missing
classification evidence produces an explicit non-classifiable record or causes
the whole T03 evaluation to fail. Neither behavior may silently drop an
observation.

## 6. Proposed output shape

No implementation output is approved yet. The smallest reviewable structural
shape is one immutable result per source observation, collected in a
deterministically ordered T03 snapshot:

| Field | Type | Required meaning |
|---|---|---|
| `source_dataset_digest` | `str` | Exact P08-T02 dataset digest consumed. |
| `source_observation_digest` | `str` | Exact P08-T01 observation digest. |
| `candidate_id` | `str` | Identity copied from the source observation. |
| `chain_id` | `str` | Identity copied from the source observation. |
| `token_identity` | `str` | Identity copied from the source observation. |
| `reference_time` | `datetime` | Source simulation reference time in UTC. |
| `interpretation_status` | proposed enum | One approved evidence/economic state. |
| `source_outcome_status` | `str` | Preserved P07 paper status. |
| `source_reconciliation_status` | `str` | Preserved P07 reconciliation status. |
| `contract_version` | `str` | Proposed `p08-t03-v1`. |
| `evaluator_version` | `str` | Must be approved with the rule. |
| `representation_digest` | `str` | SHA-256 of the complete canonical result. |

The enclosing snapshot would preserve the source T02 dataset digest, the
ordered result tuple, result digests, the T02 cutoff, and its own canonical
SHA-256 digest. This shape is a proposal, not an authorization to add a class.
Governance must approve the exact class name, cardinality, whether complete
source observations are nested, evaluator/ruleset fields, and snapshot versus
single-record contract before implementation.

## 7. Determinism, provenance, and failure behavior

An approved T03 implementation must:

- consume only one validated T02 snapshot;
- preserve source dataset and observation identity by exact digest;
- produce one result per source observation unless an approved contract states
  otherwise;
- use canonical UTC timestamps and canonical serialization;
- order results only by canonical source representation or source digest;
- reject duplicate source observation digests and inconsistent source links;
- produce stable SHA-256 digests covering all output and provenance fields;
- produce equivalent output from equivalent validated input regardless of input
  order or process state;
- use no wall clock, randomness, environment, filesystem, database, network,
  provider, or external authority; and
- reject invalid, non-canonical, tampered, unsupported, future-inconsistent, or
  partially accepted input rather than silently repairing it.

## 8. Bias and leakage controls

The approved contract must explicitly address:

- **Look-ahead/future information:** only evidence at or before the declared
  evaluation boundary may be used; future observations cannot be joined
  implicitly.
- **Survivorship bias:** T02 membership and rejected/unavailable observations
  must not be silently filtered based on outcome.
- **Selection bias:** T03 must evaluate the complete supplied snapshot, not a
  favorable subset or rank-selected sample.
- **Regime leakage:** any regime or market-phase label requires its own
  point-in-time evidence and must not use post-outcome information.
- **Feedback loops:** T03 cannot alter decisions, thresholds, weights,
  strategies, risk limits, or future dataset membership.

## 9. Explicit scope boundary

P08-T03 does not perform ranking, scoring, opportunity selection, model
training/fitting, parameter optimization, strategy modification, promotion,
metrics, expectancy, profitability, drawdown, slippage, latency, failure-rate,
cost, confidence intervals, walk-forward validation, or broad aggregation
beyond the exact approved per-observation interpretation contract.

It does not execute or trade, access wallets, sign or broadcast transactions,
call RPCs, DEXs, Jupiter, Jito, providers, live networks, databases, or
persistence systems. It does not implement P08-T04 or any later P08 task.

The placement of economic classification, performance metrics, aggregation,
bias correction, model training, and promotion remains unresolved; none is
authorized merely by this specification draft.

## 10. Dependencies and entry criteria

The dependency chain is:

```text
P06 decision and provenance
        ↓
P07 paper simulation and result history
        ↓
P08-T01 OutcomeLearningObservation
        ↓
P08-T02 OutcomeLearningDatasetSnapshot
        ↓
P08-T03 approved interpretation boundary
```

Implementation may begin only when:

1. P08-T01 and P08-T02 remain complete, immutable, and auditable;
2. sufficient historical observations exist for the selected interpretation;
3. the T03 input/output fields, versions, cardinality, and digest coverage are
   approved;
4. the taxonomy and evaluation horizon are approved;
5. paper/reconciliation and missing-data semantics are approved;
6. point-in-time, look-ahead, survivorship, selection, regime, and feedback-loop
   controls are specified;
7. read-only, reproducibility, provenance, and failure behavior are approved;
   and
8. focused tests are defined for every valid and fail-closed path.

## 11. Exit criteria and authorization states

T03 is **specification approved** only after the unresolved decisions in this
document are resolved and governance records the exact contract.

T03 is **implementation authorized** only after the approved specification
explicitly authorizes runtime work. Specification approval alone does not
authorize code.

T03 is **complete** only after the implementation, focused tests, full
regression suite, canonical/digest checks, provenance checks, immutability
checks, and scope audit pass, with no execution or model-modification
capability introduced.

Current state: this is a reviewable specification draft, not an
implementation-ready contract. The minimum authorization decision is to
approve the taxonomy, evaluation horizon/evidence source, missing-data result
behavior, exact output shape, and placement of metrics/aggregation.