# P06-T02 — Deterministic Decision Evaluation Boundary

**Status:** COMPLETE / CLOSED / AUDITED PASS
**Phase:** P06 — AI Decision Engine
**Input:** Exactly one validated P05-T08 `OpportunityContext`
**Output:** One immutable P06-T01 `DecisionIntent`
**Ruleset version:** `p06-t02-rules-v1`
**Evaluator version:** `p06-t02-evaluator-v1`

## 1. Boundary

P06-T02 is a pure, local, provider-neutral analytical evaluator:

```text
P05-T08 OpportunityContext
        ↓
P06-T02 deterministic evaluation
        ↓
P06-T01 DecisionIntent
        ↓
future independent Risk / Capital Authorization
```

The evaluator reads only point-in-time evidence already preserved in the
context. It does not fetch, reconstruct, rank, compare, prioritize, authorize,
allocate capital, or execute.

## 2. Explicit ruleset

`DecisionEvaluationRuleset` is immutable, canonical, versioned, and
reproducible. The default ruleset is:

- `BUY` when score is at least `75`;
- `WATCH` when score is at least `50` and below the BUY threshold;
- `NO_TRADE` below the WATCH threshold; and
- `NO_TRADE` for stale, invalid, uncertain, unsupported, or tampered evidence.

Evidence age is evaluated against the supplied deterministic decision timestamp
and the configured `max_evidence_age_seconds`. No uncontrolled wall-clock time
is read.

## 3. Fail-closed behavior

P05 hard-risk state remains authoritative. Invalid or non-canonical context,
unsupported ruleset, stale evidence, future evidence, and tampered provenance
are rejected or produce the explicit analytical `NO_TRADE` result. UNKNOWN,
invalidation, and risk-failure reasons are preserved; no evidence is invented
or converted into PASS.

## 4. Non-scope

P06-T02 does not implement candidate ranking or comparison, portfolio
aggregation, capital authorization, Risk Governor behavior, position sizing,
wallets, private keys, signing, RPC, DEX routing, transaction construction,
pre-flight, broadcast, reconciliation, live trading, or AI/LLM behavior.
`BUY + WAIT` remains an analytical result only.