# P08-T02 — Outcome Learning Dataset Snapshot Boundary

**Status:** COMPLETE / CLOSED / AUDITED PASS
**Phase:** P08 — Outcome Learning
**Task:** P08-T02
**Contract:** `p08-t02-v1`
**Nature:** Immutable, deterministic, provider-neutral, read-only

## 1. Purpose and bounded scope

P08-T02 defines the dataset boundary immediately after P08-T01. It creates one
deterministic snapshot from a finite collection of validated
`OutcomeLearningObservation` records, using an explicit point-in-time cutoff.

This boundary prepares evidence for later analysis but does not calculate
performance, expectancy, drawdown, slippage, latency, failure rate, edge,
win/loss classifications, or any other learning metric. It does not train,
update, compare, promote, or modify a model, strategy, threshold, weight, or
risk limit.

This document is a specification proposal only. It does not authorize runtime
implementation or any later P08 task.

## 2. Evidence-derived input contract

The proposed immutable input contract is:

```python
observations: tuple[OutcomeLearningObservation, ...]
as_of_time: datetime
```

The collection must contain complete P08-T01 observations. Every observation is
revalidated from its canonical representation before inclusion.

`as_of_time` must be timezone-aware and is the dataset's point-in-time boundary.
An observation is eligible for the snapshot only when its
`simulation_reference_time` is less than or equal to `as_of_time`. Future
observations are rejected rather than silently excluded.

The collection must be non-empty and must contain no duplicate observation
digests. Ordering supplied by the caller is not meaningful and must not affect
the resulting snapshot.

## 3. Proposed output contract

The proposed immutable `OutcomeLearningDatasetSnapshot` contains:

- the validated observation tuple in deterministic canonical order;
- the UTC `as_of_time`;
- P08-T02 contract version `p08-t02-v1`;
- the P08-T01 contract/evaluator versions represented by its observations;
- the ordered observation digests; and
- a deterministic canonical representation and SHA-256 digest.

The snapshot preserves the complete P06/P07 provenance nested inside every
P08-T01 observation. It does not replace upstream records with partial rows.

## 4. Determinism, bias controls, and missing data

Equivalent validated inputs produce equivalent ordering, canonical
representation, and digest. Ordering must be based only on canonical
observation representation or its deterministic digest, never insertion time,
process state, wall-clock time, or external data.

The point-in-time cutoff prevents future-data and look-ahead leakage. No
imputation, silent dropping, partial acceptance, or synthetic outcome is
permitted. Invalid, non-canonical, duplicated, unsupported, or future-dated
observations fail closed.

The snapshot is read-only and must not mutate supplied P08-T01 observations or
their P06/P07 inputs.

## 5. Explicit non-scope

P08-T02 does not:

- classify outcomes as wins, losses, missed opportunities, or avoided losses;
- calculate expectancy, drawdown, slippage, latency, failure rate, cost, or edge;
- aggregate performance by regime, strategy, feature, decision, entry, or exit;
- compare production and challenger models;
- perform walk-forward validation or calculate confidence intervals;
- train, update, promote, or modify models, parameters, strategies, thresholds,
  weights, or risk limits;
- rank, compare, prioritize, decide, authorize, execute, or trade;
- access wallets, signing, broadcast, RPC, DEXs, Jupiter, Jito, providers,
  networks, databases, or external authorities.

## 6. Implementation acceptance

The implementation is accepted only when verification demonstrates:

1. the exact field-level input/output contract and version;
2. the non-empty and duplicate semantics;
3. the point-in-time cutoff and canonical ordering rule;
4. missing-data and invalid-record fail-closed behavior;
5. look-ahead, survivorship, regime, and feedback-loop controls;
6. focused tests for all fail-closed paths; and
7. separation from later outcome interpretation and analysis.

The accepted implementation adds no worker, persistence, aggregation, metric,
model, or external integration.