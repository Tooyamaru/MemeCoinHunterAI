# P08-T03 — Outcome Interpretation Boundary

**Status:** COMPLETE / CLOSED / AUDITED PASS
**Phase:** P08 — Outcome Learning
**Task:** P08-T03
**Contract:** `p08-t03-v1`
**Nature:** Immutable, deterministic, provider-neutral, read-only

## 1. Purpose and bounded responsibility

P08-T03 is the first evidence-state interpretation boundary after the
validated P08-T02 dataset snapshot. Its purpose is to make the interpretation
of already-recorded outcome evidence explicit and auditable without silently
turning paper status into financial performance.

The narrowest defensible responsibility is a per-observation, read-only
interpretation record. It may state whether an observation is interpretable and
preserve the evidence state without assigning WIN, LOSS,
MISSED_OPPORTUNITY, AVOIDED_LOSS, profit, expectancy, edge, or any other
economic-performance classification. Economic classification requires a
separate future evidence and evaluation contract.

This boundary belongs after T02 because T02 provides the immutable,
point-in-time, duplicate-free collection and its source digests. T03 interprets
that fixed evidence without changing membership or provenance. It must not
rebuild a dataset or fetch additional evidence.

## 2. Input contract

The sole approved input is exactly one validated:

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

No external evidence is allowed in T03. The existing P08 contracts do
not define an immutable future-price window, target/stop event stream, fee
source, venue truth, or benchmark. Adding such evidence would be a separate
input contract and requires separate approval.

## 3. Outcome taxonomy

### 3.1 Evidence-state rationale

The existing records provide paper simulation status and reconciliation status,
not a verified economic result. The narrowest taxonomy justified without
inventing trading semantics is an evidence-interpretation state:

- `UNCLASSIFIED` — the observation is valid, but P08-T03 does not assign
  an economic class;
- `UNKNOWN` — a required source state is explicitly unknown;
- `UNAVAILABLE` — a required source state is explicitly unavailable; and
- `INCOMPLETE` — required evidence for the approved interpretation is absent.

These values describe interpretability, not profitability. They must not be
collapsed into WIN or LOSS. Any future T03 implementation shall preserve
the source paper status (`FILLED`, `PARTIAL`, `FAILED`, `REJECTED`,
`UNAVAILABLE`, or `INVALID`) and reconciliation status (`RECONCILED`,
`DISAGREEMENT`, or `UNKNOWN`) as separate provenance fields.

### 3.2 Final governance decision

P08-T03 is an **evidence-state interpretation boundary only**.

T03 does not assign an economic WIN/LOSS class. It does not infer
profitability, expectancy, edge, avoided loss, missed opportunity, or any
other financial-performance result from the existing P08-T01/P08-T02
evidence.

The approved interpretation taxonomy is:

- `UNCLASSIFIED` — the observation is valid, but the current evidence does not
  support an approved economic classification;
- `UNKNOWN` — a required source state is explicitly unknown;
- `UNAVAILABLE` — a required source state is explicitly unavailable; and
- `INCOMPLETE` — required evidence for the approved evidence interpretation is
  absent.

These states describe evidence interpretability only. They are not trading
performance labels.

P08-T03 preserves the source paper outcome status and reconciliation status as
provenance. It must not reinterpret:

- `FILLED`;
- `PARTIAL`;
- `FAILED`;
- `REJECTED`;
- `UNAVAILABLE`;
- `INVALID`;
- `RECONCILED`;
- `DISAGREEMENT`; or
- `UNKNOWN`

as economic success or failure.

Economic outcome classification, including WIN/LOSS, MISSED_OPPORTUNITY,
AVOIDED_LOSS, profitability, expectancy, or edge, is explicitly outside
P08-T03 and requires a separately approved evidence and evaluation contract.

## 4. Evaluation horizon

P08-T03 has **no economic evaluation horizon**.

The current P08 contracts do not define an immutable future-price window,
target/stop event stream, fee source, slippage source, venue truth, benchmark,
or other evidence required to establish financial performance.

Therefore T03 does not:

- fetch future market data;
- join external price observations;
- evaluate targets or stops;
- calculate returns;
- calculate fees or slippage;
- determine profitability; or
- assign WIN/LOSS or another economic class.

The T03 interpretation is restricted to the evidence already present in the
validated P08-T02 snapshot.

A future economic-classification boundary may define a versioned evaluation
horizon and evidence contract separately. That future boundary is not part of
P08-T03.

## 5. Missing and unknown information

T03 must preserve uncertainty and fail closed:

- `UNAVAILABLE` paper status remains `UNAVAILABLE`; it is never a win or loss.
- `UNKNOWN` reconciliation remains `UNKNOWN`; disagreement or lack of
  reconciliation is not economic evidence.
- `PARTIAL` results remain partial in the preserved source outcome status; T03
  does not convert partial evidence into an economic classification.
- `FAILED` and `REJECTED` results remain their recorded paper states and do not
  imply a market loss.
- Incomplete evidence yields the applicable approved evidence-state result,
  never an imputed result. T03 has no price, horizon, target/stop, fee, or
  slippage evidence contract.
- Invalid or tampered T02 input is rejected and produces no T03 output.

A valid observation with missing classification evidence produces the
explicit evidence-state result defined by the approved taxonomy. T03 must not
silently drop, repair, impute, or replace an observation.

## 6. Approved output shape

The approved output shape is one immutable result per source observation,
collected in a deterministically ordered T03 snapshot:

| Field | Type | Required meaning |
|---|---|---|
| `source_dataset_digest` | `str` | Exact P08-T02 dataset digest consumed. |
| `source_observation_digest` | `str` | Exact P08-T01 observation digest. |
| `candidate_id` | `str` | Identity copied from the source observation. |
| `chain_id` | `str` | Identity copied from the source observation. |
| `token_identity` | `str` | Identity copied from the source observation. |
| `reference_time` | `datetime` | Source simulation reference time in UTC. |
| `interpretation_status` | enum | One approved evidence-state value. |
| `source_outcome_status` | `str` | Preserved P07 paper status. |
| `source_reconciliation_status` | `str` | Preserved P07 reconciliation status. |
| `contract_version` | `str` | Exact `p08-t03-v1` contract version. |
| `evaluator_version` | `str` | Exact T03 evidence-state interpretation evaluator version. |
| `representation_digest` | `str` | SHA-256 of the complete canonical result. |

The enclosing snapshot preserves the source T02 dataset digest, the
ordered result tuple, result digests, the T02 cutoff, and its own canonical
SHA-256 digest. The implementation must preserve the exact field meanings,
cardinality, provenance linkage, evaluator versioning, canonical
representation, and snapshot digest requirements defined by this contract.

## 7. Determinism, provenance, and failure behavior

Any future T03 implementation must:

- consume only one validated T02 snapshot;
- preserve source dataset and observation identity by exact digest;
- produce exactly one result per source observation;
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

The approved contract addresses:

- **Look-ahead/future information:** only evidence in the validated T02
  snapshot may be used; future observations cannot be joined implicitly.
- **Survivorship bias:** T02 membership and rejected/unavailable observations
  must not be silently filtered based on outcome.
- **Selection bias:** T03 must evaluate the complete supplied snapshot, not a
  favorable subset or rank-selected sample.
- **Regime leakage:** T03 does not introduce regime or market-phase labels.
  Any later such label would require its own point-in-time evidence.
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

Economic classification, performance metrics, aggregation, bias correction, model training, and promotion are explicitly outside P08-T03. None is authorized by this specification.

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

Runtime implementation is not authorized by this specification. If a later
governance action separately authorizes implementation, it must require:

1. P08-T01 and P08-T02 remain complete, immutable, and auditable;
2. the supplied T02 snapshot contains the observations required for the
evidence-state interpretation;
3. the implementation conforms exactly to the approved T03 input/output
   fields, versions, cardinality, and digest coverage;
4. the implementation conforms to the approved evidence-state taxonomy and its
   non-economic scope;
5. paper/reconciliation and missing-data semantics are preserved;
6. point-in-time, look-ahead, survivorship, selection, regime, and feedback-loop
   controls are preserved;
7. read-only, reproducibility, provenance, and failure behavior are preserved;
   and
8. focused tests are defined for every valid and fail-closed path.

## 11. Exit criteria and authorization states

T03 is **specification complete** when the exact evidence-state-only contract defined in this document is recorded in governance.

T03 is **implementation authorized** only by a separate explicit governance
decision. This specification records the contract but does not authorize
runtime code.

T03 is **complete** only after the implementation, focused tests, full
regression suite, canonical/digest checks, provenance checks, immutability
checks, and scope audit pass, with no execution or model-modification
capability introduced.

Current state: COMPLETE / CLOSED / AUDITED PASS. Implementation was verified against this specification with 18 focused tests and a full regression suite of 669 passing tests.
The evidence-state-only taxonomy, exact output shape, missing-data behavior,
provenance requirements, and explicit exclusion of economic classification and
performance metrics are fixed. No economic evaluation horizon or external
evidence source is part of T03.
