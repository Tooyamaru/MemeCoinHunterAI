# P05-T06 — Opportunity Record Materialization

**Status:** COMPLETE / CLOSED / AUDITED PASS
**Phase:** P05 — Opportunity Engine
**Task:** P05-T06
**Provider posture:** Provider-neutral; deterministic; local; no external I/O
**Contract version:** `p05-t06-v1`
**Evaluator version:** `p05-t06-record-v1`

## 1. Purpose and scope

P05-T06 is the narrow boundary after P05-T05 that materializes one
opportunity-level record from one validated P05-T05 `OpportunityScore`.

It preserves the complete score and its nested P05-T01 through P05-T05
identity, risk, feature, signal, ruleset, timestamp, and digest provenance. It
does not calculate another score, compare candidates, rank candidates, reduce a
candidate set, classify a market phase, aggregate quality, or produce an action.

The boundary is intentionally one-to-one:

```text
OpportunityScore (P05-T05)
        ↓
validate and preserve complete score/provenance
        ↓
OpportunityRecord (P05-T06)
```

This leaves candidate ranking/reduction, market-phase analysis, and any broader
opportunity quality contract for separately specified future P05 tasks.

## 2. Input contract

The evaluator requires exactly one immutable input:

```python
score: OpportunityScore
```

The score must use:

- P05-T05 contract `p05-t05-v1`;
- P05-T05 evaluator `p05-t05-score-v1`;
- the authorized `p05-t05-rules-v1` ruleset;
- a canonical deterministic representation and matching digest;
- a matching ELIGIBLE P05-T04 evaluation;
- valid calculated authorized feature snapshots; and
- complete preserved upstream provenance.

P05-T06 must validate the existing P05-T05 object. It must not reconstruct a
score from partial fields or recompute feature values or scoring components.

## 3. Output contract

`OpportunityRecord` is a frozen immutable record with exactly these fields:

| Field | Type | Meaning |
|---|---|---|
| `candidate_id` | `str` | Candidate identity copied from the score. |
| `chain_id` | `str` | Candidate chain identity. |
| `token_identity` | `str` | Candidate token identity. |
| `reference_time` | `datetime` | Point-in-time context copied from the score. |
| `input_score_digest` | `str` | Exact P05-T05 score representation digest. |
| `opportunity_score` | `OpportunityScore` | Complete immutable matching P05-T05 result. |
| `evaluator_version` | `str` | Exactly `p05-t06-record-v1`. |
| `contract_version` | `str` | Exactly `p05-t06-v1`. |

The record exposes a deterministic canonical representation and SHA-256
representation digest. Its nested score is preserved by identity; no nested
contract is replaced with a digest-only reconstruction.

## 4. Validation and fail-closed behavior

The materializer raises `ValueError` and produces no record when:

- the input is not an `OpportunityScore`;
- a P05-T05 contract, evaluator, or ruleset version is unsupported;
- the score representation is non-canonical or its digest does not match;
- candidate identity or reference time is inconsistent;
- the nested P05-T04 risk gate is not ELIGIBLE;
- required P05-T04 feature values are missing, duplicated, non-calculated, or
  invalid; or
- any preserved P05-T01 through P05-T05 provenance is invalid.

Uncertainty is not converted into a valid opportunity record. P05-T06 does not
add a replacement quality status, default value, reason code, confidence,
ranking, phase, decision, authorization, or execution field.

## 5. Determinism and immutability

P05-T06 is a pure local operation:

- no wall-clock reads;
- no randomness;
- no environment, filesystem, network, provider, API, database, RPC, wallet,
  or external-service access;
- no mutation of the score or any nested upstream object; and
- equivalent scores produce equal records, canonical representations, and
  digests.

The record preserves the score's existing reference time. It does not create a
new evaluation time.

## 6. Explicit non-responsibilities

P05-T06 does not:

- recalculate P04 features or P05-T05 scoring;
- reevaluate P05-T03 risk;
- compare, rank, prioritize, or reduce candidates;
- calculate aggregate opportunity quality;
- classify market phase or regime;
- predict or estimate probability;
- produce BUY, SELL, HOLD, WATCH, or another action;
- authorize capital or execution;
- call providers or perform external I/O; or
- implement P06 decision, authorization, execution, or AI behavior.

## 7. Acceptance criteria

1. Exactly one validated P05-T05 score is required.
2. The complete score object and its provenance are preserved.
3. Candidate identity and score digest linkage are exact.
4. Unsupported, tampered, non-canonical, or mismatched inputs fail closed.
5. The output is frozen, deterministic, and locally reproducible.
6. No ranking, phase, quality aggregation, decision, action, execution, or
   external I/O is introduced.
