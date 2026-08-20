# P05-T04 — Per-Candidate Feature and Quality Evaluation

**Status:** SPECIFICATION READY / IMPLEMENTATION NOT STARTED  
**Phase:** P05 — Opportunity Engine  
**Task:** P05-T04  
**Provider posture:** Provider-neutral; deterministic; local; no external I/O  
**Contract version:** `p05-t04-v1`  
**Evaluator version:** `p05-t04-features-v1`

## 1. Purpose and scope

P05-T04 is the narrow boundary after P05-T03 that evaluates the availability
and quality state of the feature snapshots already attached to one opportunity
candidate.

It is not a new market-data or feature-calculation boundary. The existing
repository already defines and calculates the authorized P04 features at
P04-T09, then captures them as immutable P04-T10 snapshots. P05-T04 may
validate and expose those existing results for one candidate, but it must not
recalculate them from snapshot inputs or invent additional formulas.

P05-T04 shall:

1. consume exactly one normalized P05-T02 candidate and its matching P05-T03
   hard-risk evaluation;
2. apply the P05-T03 viability result as a mandatory gate;
3. validate the candidate's immutable P04-T10 feature snapshots;
4. preserve existing feature values, statuses, reason codes, timestamps, and
   provenance;
5. preserve the candidate's signal-snapshot quality and provenance as context;
6. return an immutable, deterministic per-candidate evaluation record; and
7. fail closed when the risk gate, input contract, feature snapshot, or
   provenance requirements are not satisfied.

P05-T04 does not select among candidates, compare candidates, calculate a
composite score, or produce an action.

## 2. Repository-grounded boundary

The legitimate boundary is:

```text
NormalizedOpportunityCandidate (P05-T02)
        + matching CandidateRiskEvaluation (P05-T03)
        ↓
P05-T03 eligibility gate
        ↓
validate existing candidate feature snapshots and preserve quality/provenance
        ↓
immutable CandidateFeatureEvaluation (P05-T04)
```

The current repository contains no P05-T04 implementation. This document
defines the smallest contract that can be implemented from the contracts
already present. It does not claim that P05-T04 code or tests exist.

The current repository's `PROJECT_STATE.md` and `docs/MASTER_BLUEPRINT.md`
still describe the formal project state as P04 and P05 as not started. Those
governance documents are intentionally not modified by this specification-only
task.

## 3. Exact upstream input contract

P05-T04 requires exactly two immutable inputs belonging to the same candidate:

```python
candidate: NormalizedOpportunityCandidate
risk_evaluation: CandidateRiskEvaluation
```

An implementation may expose a function with this equivalent contract:

```python
evaluate_candidate_features(
    candidate: NormalizedOpportunityCandidate,
    risk_evaluation: CandidateRiskEvaluation,
    *,
    evaluated_at: datetime | None = None,
) -> CandidateFeatureEvaluation
```

The function name is not an authorization to add another vocabulary or
implementation module; the output and validation behavior in this document
are the contract.

### 3.1 P05-T02 candidate requirements

The normalized candidate must:

- be a `NormalizedOpportunityCandidate`;
- declare `contract_version == "p05-t02-v1"`;
- preserve a P05-T01 candidate with `contract_version == "p05-t01-v1"`;
- have non-empty `candidate_id`, `chain_id`, and `token_identity`;
- have a timezone-aware UTC-normalizable `reference_time`;
- have a valid `OpportunityCandidateState`;
- preserve a `DerivedEligibilityOutput`;
- preserve a valid `SignalEvidenceSnapshot`; and
- contain only valid immutable `FeatureCalculationSnapshot` values in
  `feature_snapshots`.

The candidate's existing construction and normalization boundaries remain the
authority for the detailed P05-T01, P05-T02, P04-T06, and P04-T10 validation
rules. P05-T04 must not weaken or bypass those rules.

### 3.2 P05-T03 risk-evaluation requirements

The risk evaluation must be a `CandidateRiskEvaluation` with:

- `contract_version == "p05-t03-v1"`;
- `evaluator_version == "p05-t03-rules-v1"`;
- a non-empty `candidate_id`;
- a non-empty `input_candidate_digest`;
- a supported `CandidateViabilityStatus`;
- a valid timezone-aware `evaluated_at`;
- valid immutable `risk_flags`;
- valid immutable `evidence_references`; and
- the canonical result representation and version fields required by P05-T03.

P05-T04 must verify both identity links before using the risk evaluation:

```text
risk_evaluation.candidate_id
    == candidate.candidate_id

risk_evaluation.input_candidate_digest
    == candidate.representation_digest
```

A mismatch is invalid input. P05-T04 must not use a risk result from a
different candidate or silently replace the candidate digest.

## 4. P05-T03 eligibility gate

P05-T04 is gated by the existing P05-T03 `viability_status`. The mapping is:

| P05-T03 viability status | P05-T04 gate | P05-T04 feature-value behavior |
|---|---|---|
| `CandidateViabilityStatus.ELIGIBLE` | Open | Existing feature snapshots may be evaluated for availability. |
| `CandidateViabilityStatus.DISQUALIFIED` | Closed | No feature value is admitted as an evaluated candidate feature. |
| `CandidateViabilityStatus.INSUFFICIENT_EVIDENCE` | Closed | No feature value is admitted as an evaluated candidate feature. |

The gate is closed for every P05-T03 result other than
`CandidateViabilityStatus.ELIGIBLE`.

When the gate is closed, P05-T04 must:

- preserve the complete matching P05-T03 result object, including its digest,
  viability status, flags, rejection reason, evidence references, timestamps,
  evaluator version, and contract version;
- preserve candidate and upstream provenance;
- not recalculate, reinterpret, or promote any feature value; and
- not treat a non-eligible P05-T03 result as permission to use the feature
  snapshots as an evaluated opportunity input.

P05-T04 does not reevaluate safety evidence and does not derive a second
eligibility result. The P05-T03 result remains the sole hard-risk gate.

## 5. Evidence and features actually available

### 5.1 Candidate identity and point-in-time context

The normalized candidate provides:

- `candidate_id`;
- `chain_id`;
- `token_identity`;
- `reference_time`;
- candidate state and candidate reason codes;
- an immutable analytical-context mapping; and
- immutable upstream references and digests.

`analytical_context` is not a typed market-evidence contract. P05-T04 must
preserve it only through the candidate digest/provenance and must not interpret
arbitrary keys as hidden feature inputs.

### 5.2 P05-T03 hard-risk context

The P05-T03 result provides:

- the matching candidate ID;
- the input normalized-candidate digest;
- the hard-risk viability status;
- boundary risk flags;
- rejection reason when not eligible;
- upstream eligibility evidence references;
- P05-T03 evaluator and contract versions;
- deterministic evaluation time; and
- its own canonical representation digest.

It does not contain raw safety evidence, safety-domain values, market
observations, signal values, or feature values.

### 5.3 Signal snapshot context

The candidate's `SignalEvidenceSnapshot` provides only the already-snapshotted
signal trace, including:

- signal statuses;
- optional signal quality status;
- evaluated signal status;
- evidence references;
- signal provenance;
- observation timestamps;
- normalized-evidence, evaluation, and aggregation digests; and
- the P04 contract versions.

The snapshot does not expose the original `SignalEvidence` objects or a
numeric signal-confidence input to P05-T04. P05-T04 may preserve the signal
snapshot digest, quality status, evidence references, and provenance, but may
not infer a numeric feature from them.

### 5.4 Feature snapshot context

Each `FeatureCalculationSnapshot` provides the already-created P04-T09 result
as an immutable P04-T10 record, including:

- `feature_id` and `feature_version`;
- `FeatureCalculationStatus`;
- reason codes;
- `Decimal` value only for `CALCULATED` results;
- value and source units;
- quote asset;
- source, chain, token, and market-subject identity;
- reference time and freshness policy;
- input references and upstream P02 state references;
- input-set digest;
- snapshot linkage;
- source-result digest; and
- snapshot contract version.

P05-T04 may consume this snapshot representation. It must not go back to raw
P02 observations, perform a hidden lookup, or recalculate a formula from the
snapshot's `inputs`.

## 6. Features that may be exposed and features that cannot be computed

### 6.1 Existing authorized features

The repository's P04-T09 implementation defines exactly two numeric feature
families:

| Feature | Definition version | P05-T04 treatment |
|---|---|---|
| `price_velocity` | `price-velocity-v1` | Expose the existing value only when an attached P04-T10 snapshot is `CALCULATED` and valid. |
| `price_acceleration` | `price-acceleration-v1` | Expose the existing value only when an attached P04-T10 snapshot is `CALCULATED` and valid. |

P05-T04 does not repeat either formula. The authoritative formulas, numeric
conversion, precision, timestamp selection, freshness checks, and input
selection remain P04-T09 behavior.

Authorization is the exact pair `(feature_id, feature_version)`. A candidate
feature snapshot is authorized only when it matches one of these pairs:

```text
("price_velocity", "price-velocity-v1")
("price_acceleration", "price-acceleration-v1")
```

A matching feature ID with a different version is not authorized. If a
candidate contains a valid snapshot outside these exact pairs, P05-T04 must
not infer its meaning. It must preserve the snapshot and preserve its existing
upstream `UNSUPPORTED_FEATURE` reason when that reason is already present.

### 6.2 Deterministic feature availability evaluation

P05-T04 may deterministically evaluate only these non-numeric conditions:

1. the P05-T03 gate is open;
2. every supplied feature snapshot is a valid immutable P04-T10 snapshot;
3. a supplied feature snapshot has an authorized `(feature_id,
   feature_version)` pair;
4. a supplied feature snapshot has `CALCULATED` status and therefore a
   validated finite `Decimal` value and value unit; and
5. the snapshot's existing reason codes and provenance are preserved.

These checks describe availability of existing feature results. They do not
produce an aggregate P05-T04 status, quality score, confidence value, ranking,
or prediction. The existing `FeatureCalculationStatus` on each preserved
snapshot remains the only feature-result status.

### 6.3 Features not computable from existing contracts

P05-T04 must not calculate or infer any of the following because the current
candidate/snapshot contracts do not provide a legitimate P05-T04 input
definition for them:

- transaction frequency or transaction counts;
- volume, volume acceleration, or relative volume;
- buy/sell pressure or flow imbalance;
- liquidity behavior, depth, reserves, or slippage;
- volatility or momentum composites;
- market phase or regime;
- holder, wallet, funding, or developer behavior;
- social or narrative signals;
- sellability or execution behavior;
- a composite opportunity/trade score;
- a prediction or probability; or
- any value derived from the number or order of snapshots.

The P04-T09 specification explicitly defers transaction frequency and broader
feature families. P05-T04 must report the limitation rather than invent a
formula, data source, window, threshold, or hidden dependency.

## 7. Feature availability interpretation

P05-T04 does not introduce a candidate-level feature-quality status. The
existing statuses remain authoritative:

- `CandidateViabilityStatus` describes the P05-T03 hard-risk gate;
- `FeatureCalculationStatus` describes each feature snapshot; and
- existing signal status and quality enums describe the signal snapshot.

When the P05-T03 viability status is `ELIGIBLE`, P05-T04 may inspect the
feature snapshots for availability. A snapshot is available as an upstream
feature result only when its exact authorized feature pair is present, its
existing status is `CALCULATED`, and its immutable snapshot contract is valid.

When the P05-T03 viability status is not `ELIGIBLE`, P05-T04 preserves the
matching risk result and feature snapshots but does not admit any feature
snapshot as an evaluated opportunity input. It does not emit a replacement
aggregate status.

An empty `feature_snapshots` tuple is valid and remains empty. It does not
produce a synthetic status or reason code. A snapshot with `UNKNOWN`, `INVALID`,
or `UNSUPPORTED` status remains present with its existing status and reason
codes; it is never silently dropped or converted into a calculated result.

## 8. Exact output contract

The proposed immutable output type is `CandidateFeatureEvaluation`. It has
exactly these fields:

| Field | Type | Meaning |
|---|---|---|
| `candidate_id` | `str` | Candidate identity copied from the normalized candidate. |
| `chain_id` | `str` | Candidate chain identity. |
| `token_identity` | `str` | Candidate token identity. |
| `reference_time` | `datetime` | Candidate point-in-time reference, normalized to UTC. |
| `evaluated_at` | `datetime` | P05-T04 evaluation time, normalized to UTC. |
| `input_candidate_digest` | `str` | Exact `candidate.representation_digest`. |
| `risk_evaluation` | `CandidateRiskEvaluation` | The complete matching immutable P05-T03 result, including its digest, viability status, flags, rejection reason, evidence references, timestamp, evaluator version, and contract version. |
| `feature_snapshots` | `tuple[FeatureCalculationSnapshot, ...]` | Exact immutable candidate snapshots, in their existing candidate order. |
| `signal_snapshot` | `SignalEvidenceSnapshot` | The complete matching immutable P04-T06 signal snapshot, including its digest, evidence references, provenance, observation timestamps, status fields, and contract/version information. |
| `upstream_references` | `tuple[OpportunityUpstreamReference, ...]` | Candidate's immutable P03/P04 upstream references. |
| `evaluator_version` | `str` | Exactly `p05-t04-features-v1`. |
| `contract_version` | `str` | Exactly `p05-t04-v1`. |

The output must not contain:

- a numeric score;
- a ranking or rank;
- a candidate-reduction result;
- a prediction or confidence probability;
- `BUY`, `SELL`, `HOLD`, or another action;
- a capital or authorization field; or
- wallet, execution, RPC, API, database, network, or external-service data.

The existing `FeatureCalculationSnapshot.value` fields are preserved only as
already-calculated upstream analytical values. P05-T04 does not create or
alter them. The nested `CandidateRiskEvaluation` and
`SignalEvidenceSnapshot` objects are preserved directly rather than
reconstructed from partial digest fields.

## 9. Reason-code behavior

P05-T04 does not define an aggregate `reason_codes` field. Reason codes remain
on their existing immutable upstream objects and are preserved without
reinterpretation. In particular, P05-T04 may preserve:

- P05-T03 risk flags and rejection reason;
- candidate reason codes;
- feature-snapshot reason codes; and
- the existing P04-T09 reason `UNSUPPORTED_FEATURE`.

Existing upstream `reason_codes` may be empty for a successful or available
result. P05-T04 must not require them to be non-empty and must not create
synthetic fallback reasons. A missing feature snapshot is represented by the
valid empty tuple already present on the candidate.

## 10. Fail-closed behavior

### 10.1 Contract violations

The evaluator must raise a deterministic `ValueError` and produce no
`CandidateFeatureEvaluation` when:

- either required input has the wrong type;
- the P05-T02, P05-T03, P04-T06, or P04-T10 contract version is unsupported;
- candidate identity and risk-result identity do not match;
- the risk result's input digest does not equal the normalized candidate digest;
- a candidate snapshot is not a `FeatureCalculationSnapshot`;
- a snapshot is tampered, non-canonical, or has invalid provenance/linkage;
- a required identity, digest, or timestamp is missing or malformed; or
- an enum/status cannot be normalized to its supported contract value.

P05-T04 must not repair an invalid object from partial fields or use an
external lookup to make it valid.

### 10.2 Data-level non-success

When the input contracts are valid but the upstream evidence is not available
for feature use, P05-T04 must preserve the upstream objects without creating an
aggregate replacement status:

- a closed P05-T03 gate preserves the matching risk result and does not admit
  its feature snapshots as an evaluated opportunity input;
- no feature snapshots preserves the valid empty tuple already supplied by the
  candidate;
- a non-calculated feature snapshot preserves its existing status and reason
  codes;
- an unauthorized feature pair preserves the snapshot and any existing
  upstream `UNSUPPORTED_FEATURE` reason; and
- missing optional signal quality preserves `None` and is never treated as
  acceptable quality or as a numeric feature.

No non-success condition may produce a new numeric value, a default value,
zero, a synthetic reason code, or a successful fallback.

## 11. Versioning and provenance

Every result must preserve:

- P05-T04 contract version `p05-t04-v1`;
- P05-T04 evaluator version `p05-t04-features-v1`;
- P05-T02 input candidate digest and contract version through the candidate;
- the complete immutable P05-T03 risk result, including its digest, contract
  version, evaluator version, status, flags, rejection reason, evidence
  references, and timestamp;
- each P04-T10 feature snapshot and its own calculation/snapshot versions;
- each feature snapshot's result, input-set, snapshot-linkage, and upstream
  state digests;
- the complete immutable P04 signal snapshot, including its digest, quality
  status, evidence references, provenance, observation timestamps, evaluation
  and aggregation digests, and contract/version information;
- candidate upstream P03/P04 references; and
- candidate/reference and evaluation timestamps.

P05-T04 must preserve evidence references as references. It must not dereference
them, replace them with newly collected data, or claim that a digest alone is
the underlying evidence.

## 12. Determinism and timestamp behavior

P05-T04 must be a pure local operation:

- no wall-clock reads;
- no random values;
- no environment-dependent behavior;
- no filesystem, network, provider, API, database, RPC, or wallet access; and
- no mutation of either input.

If `evaluated_at` is omitted, it must equal `candidate.reference_time`.
If supplied, it must be timezone-aware and normalized to UTC. It is an
evaluation-record timestamp only; it must not replace any feature snapshot
reference time or observation timestamp.

Equivalent candidate/risk inputs and the same effective evaluation timestamp
must produce the same:

- the same upstream statuses and reason codes;
- the same feature and signal provenance;
- canonical representation; and
- representation digest.

Feature snapshot order must be preserved from the normalized candidate. P05-T04
must not sort snapshots into a ranking or use order as a quality preference.

## 13. Immutability

`CandidateFeatureEvaluation` must be a frozen, immutable record. Its nested
feature snapshots and upstream references are already immutable contracts and
must remain immutable in the result. Tuple fields must remain tuples, and any
canonical mapping exposed by the result must be an immutable read view.

The result must expose a deterministic canonical representation and digest.
The canonical representation must include all output fields in this
specification, including both P05-T04 version fields and the complete
canonical representations of the nested P05-T03 risk result, feature
snapshots, and P04 signal snapshot.

Creating or reading the result must not mutate:

- the normalized candidate;
- the candidate's P03/P04 upstream contracts;
- the P05-T03 risk evaluation;
- feature snapshots;
- signal snapshots; or
- caller-owned collections.

## 14. Explicit non-responsibilities

P05-T04 does not:

- calculate `price_velocity` or `price_acceleration` again;
- read raw P02 observations or reconstruct a price series;
- calculate transaction frequency, volume, liquidity, volatility, momentum,
  regime, wallet, holder, social, or execution features;
- reevaluate safety evidence or replace P05-T03;
- add evidence domains, evidence sources, thresholds, or freshness policies;
- score, rank, prioritize, compare, or reduce candidates;
- create a composite trade/opportunity score;
- predict, classify a market phase, or estimate profit probability;
- make a BUY/SELL/HOLD/AVOID or any other decision;
- authorize capital or execution;
- access wallets, RPC, APIs, databases, networks, or external I/O;
- persist, schedule, stream, backfill, or retrieve missing evidence; or
- modify P05-T01/T02/T03 code, tests, specifications, roadmap, or governance
  documents as part of this boundary.

## 15. Important limitations discovered

The existing contracts impose these hard limitations:

1. `CandidateRiskEvaluation` alone contains no feature data. A legitimate
   P05-T04 evaluator therefore requires the matching normalized candidate too.
2. P05-T03 exposes no raw safety evidence or safety-domain measurements.
   P05-T04 can preserve only its result and references.
3. `SignalEvidenceSnapshot` exposes a signal trace and provenance, not the
   original signal records or a numeric confidence input.
4. P04-T10 snapshots expose already-calculated feature values and references,
   not permission to recalculate them at P05-T04.
5. The candidate may be `VALID` with an empty `feature_snapshots` tuple;
   therefore P05-T04 must represent missing feature evidence explicitly.
6. The current repository authorizes only `price_velocity` and
   `price_acceleration` as numeric P04 feature definitions. No broader
   opportunity feature catalog is available to P05-T04.
7. Arbitrary `analytical_context` is not an approved evidence contract and
   cannot be used as a hidden lookup or feature source.

If a future P05-T04 requirement needs any unavailable data, it requires a
separate upstream contract and specification. It must not be added through
implicit interpretation of existing fields.

## 16. Acceptance criteria for a future implementation

An implementation of this specification is acceptable only if it demonstrates
that:

1. exactly one matching normalized candidate and P05-T03 risk result are
   required;
2. candidate/risk identity and digest mismatches fail closed;
3. only P05-T03 `ELIGIBLE` opens the feature gate;
4. `DISQUALIFIED` and `INSUFFICIENT_EVIDENCE` never permit the feature
   snapshots to be used as an evaluated opportunity input;
5. existing P04-T10 calculated `price_velocity` and
   `price_acceleration` snapshots are preserved without recalculation;
6. an empty feature snapshot tuple remains valid and produces no synthetic
   status or reason code;
7. unknown, invalid, unsupported, or malformed feature snapshots never produce
   a new numeric value;
8. signal quality, evidence references, timestamps, digests, and provenance
   are preserved without reinterpretation;
9. no unsupported feature family, score, ranking, comparison, or decision is
   introduced;
10. repeated evaluation with identical canonical inputs produces identical
    output and digest without wall-clock or external I/O;
11. the output and nested representations are immutable; and
12. no upstream candidate, risk result, feature snapshot, signal snapshot, or
    evidence object is mutated.