# P08-T01 — Immutable Outcome Learning Observation

**Status:** COMPLETE / CLOSED / AUDITED PASS
**Phase:** P08 — Outcome Learning
**Task:** P08-T01
**Contract:** `p08-t01-v1`
**Evaluator:** `p08-t01-outcome-observation-v1`
**Nature:** Immutable, deterministic, provider-neutral, read-only

## 1. Purpose and bounded scope

P08-T01 establishes the first read-only learning boundary: one immutable
observation linking one validated P06 `DecisionIntent` to one validated P07
paper-simulation input and one selected validated P07 paper-simulation result
retained by a P07-T07 history snapshot.

The observation preserves point-in-time decision and simulation context for later
analysis. It does not interpret the result as a win, loss, missed opportunity,
avoided loss, profit, expectancy, drawdown, or edge. Those semantics and any
aggregation are outside P08-T01.

P08-T01 does not implement P08-T02 or any later task.

## 2. Input contract

The constructor requires exactly:

```python
decision_intent: DecisionIntent
simulation_input: PaperSimulationInput
paper_result: PaperSimulationResult
history: PaperSimulationResultHistory
```

All three inputs must be the existing immutable contracts at their supported
versions. Each input is revalidated from its canonical representation before an
observation is accepted.

The provenance chain must be exact:

```text
DecisionIntent.digest
        = PaperSimulationInput.decision_intent.decision_intent_digest
PaperSimulationInput.digest
        = PaperSimulationResult.input_digest
```

The input records are preserved as complete nested objects. No missing material
is reconstructed, fetched, or silently replaced.

The selected paper result must be retained by the supplied P07-T07 history
snapshot. The history is copied into an immutable tuple and its
`p07-t07-v1` history digest is preserved.

## 3. Output contract

`OutcomeLearningObservation` is a frozen record containing:

- the complete validated P06 `DecisionIntent`;
- the complete validated P07 `PaperSimulationInput`;
- the complete validated P07 `PaperSimulationResult`;
- the immutable P07-T07 history snapshot and history digest;
- P08-T01 contract and evaluator versions; and
- a deterministic canonical representation and SHA-256 digest.

Convenience accessors expose candidate identity, point-in-time timestamps,
provenance digests, and the already-recorded paper outcome statuses. They do not
derive a performance classification or recommendation.

## 4. Determinism, immutability, and provenance

Equivalent validated inputs produce equivalent canonical representations and
digests. The operation uses no wall clock, randomness, environment, filesystem,
database, network, provider, wallet, RPC, DEX, signing, broadcast, or external
authority.

The output is immutable and does not mutate any P06 or P07 input. Nested
canonical representations are frozen. Upstream digests remain auditable and the
P08 digest covers the complete canonical observation.

## 5. Explicit non-scope and safety boundary

P08-T01 does not:

- calculate wins, losses, missed opportunities, avoided losses, profit,
  expectancy, drawdown, slippage, latency, failure rate, or infrastructure
  cost;
- aggregate, compare, rank, prioritize, optimize, or select candidates;
- train, update, promote, or modify any model, threshold, weight, strategy, or
  risk limit;
- create a decision, authorization, execution request, order, or live authority;
- access wallets, signing, broadcast, RPC, DEXs, Jupiter, Jito, providers, or
  networks; or
- implement P08-T02, P09, or any later phase.

## 6. Fail-closed requirements

The boundary raises `ValueError` and produces no observation for invalid or
unsupported versions, non-canonical or tampered upstream records, invalid
types, or broken decision/input/result digest links.

## 7. Verification

Focused tests cover valid preservation, deterministic provenance, broken links,
tampered upstream records, unsupported versions, immutability, and absence of
learning or execution authority.