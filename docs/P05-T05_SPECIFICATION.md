# P05-T05 — Per-Candidate Opportunity Score (Fast Pre-Score)

**Status:** IMPLEMENTED / PENDING FINAL AUDIT CLOSURE
**Phase:** P05 — Opportunity Engine  
**Task:** P05-T05  
**Provider posture:** Provider-neutral; deterministic; local; no external I/O  
**Contract version:** `p05-t05-v1`  
**Evaluator version:** `p05-t05-score-v1`  
**Ruleset version:** `p05-t05-rules-v1`

## 1. Purpose and scope

P05-T05 consumes exactly one validated, ELIGIBLE P05-T04
`CandidateFeatureEvaluation` and calculates one bounded per-candidate
opportunity pre-score from the two authorized P04-T09/P04-T10 numeric values:
`price_velocity` and `price_acceleration`.

P05-T05 does not recalculate features, reevaluate risk, compare candidates,
rank candidates, make a trading decision, authorize capital, execute trades,
invoke AI/LLM behavior, or perform external I/O. It is not P05-T06 deep
analysis.

## 2. Input contract

The evaluator requires exactly:

```python
feature_evaluation: CandidateFeatureEvaluation
ruleset: OpportunityScoringRuleset
```

The feature evaluation must:

- use P05-T04 contract `p05-t04-v1` and evaluator
  `p05-t04-features-v1`;
- contain a P05-T03 risk result with viability `ELIGIBLE`;
- retain its canonical deterministic representation;
- contain exactly one valid `CALCULATED` snapshot for each authorized pair:
  `("price_velocity", "price-velocity-v1")` and
  `("price_acceleration", "price-acceleration-v1")`;
- contain finite `Decimal` values in those snapshots; and
- preserve the complete T04 object and provenance without reconstruction in the
  output.

Unsupported feature snapshots remain upstream context but are not score inputs.
Missing, duplicate, malformed, or non-calculated required features fail closed.

## 3. Versioned scoring ruleset

This section is the implementation contract for the ruleset explicitly
authorized in `docs/P05-T05_ARCHITECTURAL_DECISION.md`. It introduces no
additional parameters or scoring behavior.

The initial immutable ruleset is `p05-t05-rules-v1`:

```text
velocity_scale = 1
acceleration_scale = 1
velocity_weight = 2
acceleration_weight = 1
```

For each value `x` and its positive scale `s`, calculate the bounded signal:

```text
bounded(x, s) = x / (s + |x|)
```

Then calculate:

```text
weighted_signal =
    (2 * bounded(price_velocity, 1)
     + 1 * bounded(price_acceleration, 1)) / 3

score = 50 * (1 + weighted_signal)
```

The score is a finite `Decimal` in the inclusive range `[0, 100]`. Decimal
arithmetic uses deterministic local precision of 50 digits and
`ROUND_HALF_EVEN` rounding; no binary floating-point conversion, recalculation
of upstream features, threshold lookup, or external data is allowed.

The ruleset's scales and weights are part of the canonical ruleset
representation and therefore part of the output provenance.

## 4. Output contract

`OpportunityScore` is an immutable record containing:

- candidate identity and point-in-time context;
- the complete matching P05-T04 `feature_evaluation`;
- the P05-T04 representation digest;
- the ruleset version and canonical ruleset;
- the two preserved upstream `Decimal` feature values;
- each bounded component signal; and
- the final bounded `score`.

The output has P05-T05 contract version `p05-t05-v1` and evaluator version
`p05-t05-score-v1`, plus a deterministic canonical representation and digest.
It contains no rank, comparison result, action, authorization, execution, or
AI field.

## 5. Fail-closed and purity requirements

The evaluator raises `ValueError` and produces no score when input types,
versions, identity, eligibility, provenance, feature availability, ruleset
values, or canonical representations are invalid.

The operation is pure and deterministic: it reads no wall clock, randomness,
environment, filesystem, network, provider, API, database, RPC, or wallet and
does not mutate the T04 input or nested upstream contracts.