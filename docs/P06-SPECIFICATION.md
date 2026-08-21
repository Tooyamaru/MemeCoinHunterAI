# P06 — Deterministic Decision Engine Architecture Gate

**Status:** P06-T03 COMPLETE / CLOSED
**Phase:** P06 — AI Decision Engine
**Implementation status:** No P06 runtime implementation authorized
**Provider posture:** Provider-neutral; deterministic hot path; no execution I/O
**Authority:** V1.1 architecture, Decision Engine principles, and evidence-first
P05-T06 through P05-T08 contracts

## 1. Purpose and approved boundary

P06 is the analytical Decision Engine boundary after the completed P05
opportunity context. It converts one validated, point-in-time
`OpportunityContext` into one bounded, versioned decision intent. It does not
authorize capital or perform execution.

```text
P05-T08 Final Opportunity Context
        ↓
optional bounded deep analysis (non-authoritative)
        ↓
deterministic P06 Decision Engine
        ↓
Decision Intent
        ↓
independent Risk / Capital Authorization
        ↓
Execution Request
        ↓
isolated Signing Boundary → Broadcast → Reconciliation → Journal
```

P06 is not a ranking, portfolio, authorization, wallet, execution, or
transaction-submission boundary. It processes one candidate context at a time;
candidate comparison and prioritization are outside this gate.

## 2. Required input

The future implementation accepts exactly one validated P05-T08
`OpportunityContext`, plus an explicitly versioned deterministic decision
configuration. The context must retain the direct P05 objects and linkages:

- candidate and token identity;
- hard-risk/disqualification state, flags, reason codes, evidence references,
  and UNKNOWN/invalidated state;
- authorized feature identity/version and feature evaluation;
- signal snapshot and provenance;
- P05-T05 score, ruleset, evaluator, and digest;
- P05-T06 record identity and digest;
- P05-T07 history identity and digest;
- reference and evaluation timestamps;
- uncertainty and invalidation context; and
- all contract/evaluator/version identities needed for reproduction.

P06 must reject stale, tampered, non-canonical, unsupported, incomplete, or
inconsistent context. It must never reconstruct missing evidence, turn UNKNOWN
into PASS, or infer evidence not present in the P05 context.

## 3. Deterministic decision boundary

The deterministic engine is the authority for the P06 decision result. Its
rules, thresholds, configuration, and evaluator version must be explicit,
immutable for an evaluation, versioned, reproducible, and fail closed.

The decision result may include the approved analytical action vocabulary:

- `BUY`
- `WATCH`
- `HOLD`
- `TAKE_PROFIT`
- `REDUCE`
- `EXIT`
- `AVOID`
- `NO_TRADE`

An action is not an execution instruction. Decision and entry remain separate;
for example, `BUY` may carry an entry posture of `WAIT` rather than an immediate
entry instruction. The output must include the evidence, risk context,
uncertainty, invalidation conditions, expected-edge assumptions, point-in-time
references, and ruleset/configuration provenance used to reach the result.

Confidence is an analytical field only. It is not a guaranteed probability of
profit, a capital limit, an authorization, or a reason to bypass the Risk
Governor. Failure or uncertainty in required evidence or execution assumptions
produces `NO_TRADE` or an explicit invalid result according to the deterministic
contract; it must not produce a permissive fallback.

## 4. Optional AI/LLM assistance

The architecture permits optional bounded statistical, classical, ML, or
narrative/LLM analysis as a separate input to the deterministic boundary. This
is not required for P06 and is not part of the hot-path authority.

If later authorized by a separate implementation specification, assistance must:

1. consume only the supplied point-in-time context;
2. be versioned, bounded, auditable, and clearly identified as non-deterministic
   or deterministic as applicable;
3. preserve source/evidence references and distinguish observations from
   generated narrative;
4. never invent, overwrite, or downgrade evidence or risk state;
5. never independently trigger `BUY` or any other action;
6. never block the deterministic critical path; and
7. be safely ignored without changing the deterministic result when unavailable.

No P06 implementation may invoke an LLM until a later task explicitly
authorizes that interface and its validation contract.

## 5. Decision intent output

The future immutable decision-intent record must preserve:

- candidate/token identity and the P05-T08 context digest;
- decision action and separate entry posture;
- point-in-time reference and decision timestamps;
- hard-risk result and risk/evidence references;
- feature and signal provenance;
- uncertainty and invalidation conditions;
- expected-edge assumptions and confidence, explicitly not profit probability;
- deterministic ruleset, evaluator, model/analysis, and configuration versions;
- canonical representation and deterministic digest; and
- any bounded analysis provenance, if separately authorized and present.

The intent is an analytical recommendation for the next governance boundary.
It is not an order, quote, route, position, allocation, or transaction.

## 6. Separate boundaries and forbidden ownership

### P06 may produce

- one reproducible analytical decision intent for one validated candidate
  context;
- `NO_TRADE` when evidence, risk, uncertainty, invalidation, or execution
  assumptions do not satisfy the deterministic contract;
- auditable reason codes, evidence references, confidence, assumptions, and
  provenance for that intent.

### P06 must not produce or own

- risk/capital authorization, exposure allocation, or fund limits;
- unrestricted capital or execution infrastructure;
- private keys, seed phrases, wallets, signing, or transaction broadcast;
- RPC, DEX routing, venue/provider execution logic, or transaction submission;
- BUY/SELL transaction construction or pre-flight execution;
- portfolio aggregation, candidate ranking, or prioritization;
- autonomous capital movement;
- an entry instruction that bypasses authorization;
- an LLM as the primary trading brain or an autonomous AI loop.

The independent Risk Governor remains higher authority than P06 and may
`ALLOW`, `REDUCE`, `BLOCK`, or `EMERGENCY STOP`. Execution begins only after
that separate authorization and later pre-flight gates succeed.

## 7. Reproducibility and fail-closed requirements

P06 must be pure/local at the deterministic boundary: no provider, network,
filesystem, database, wallet, RPC, signing, broadcast, or execution I/O. It
must use only point-in-time information available at decision time and must
produce canonical, immutable, version-linked output.

The implementation gate is not passed until focused tests demonstrate valid
construction, complete P05 provenance preservation, deterministic canonical
representation and digest, unsupported-version rejection, tamper detection,
uncertainty/invalidation preservation, `NO_TRADE` fail-closed behavior, and
rejection of ranking, authorization, and execution semantics.

## 8. Explicit non-scope for this gate

This document authorizes architecture/specification work only. It does not
authorize P06 runtime code, AI/LLM integration, model installation, database
changes, provider integration, paper trading, wallet integration, RPC, DEX
routing, transaction submission, signing, broadcasting, or live trading.

## 9. P06-T01 contract closure

P06-T01 defines the immutable, provider-neutral `DecisionIntent` contract for
one validated P05-T08 `OpportunityContext`. The contract uses:

- `p06-t01-v1` as its contract version;
- `p06-t01-rules-v1` as its deterministic ruleset version; and
- `p06-t01-intent-v1` as its evaluator version.

The intent preserves the complete P05-T08 context by identity, adds only
analytical action, separate entry posture, explicit assumptions, uncertainty,
invalidation conditions, bounded analytical confidence, point-in-time decision
time, canonical representation, and a deterministic SHA-256 digest. It has no
ranking, authorization, execution, wallet, RPC, DEX, signing, broadcast, or
LLM fields or behavior. Uncertain or invalid evidence can only produce
`NO_TRADE`; no evidence is invented or downgraded.

## 10. P06-T02 evaluation closure

P06-T02 defines the deterministic evaluation boundary that consumes exactly one
validated P05-T08 `OpportunityContext` and reuses the P06-T01 `DecisionIntent`
contract. Its immutable ruleset is `p06-t02-rules-v1` and its evaluator version
is `p06-t02-evaluator-v1`.

The default thresholds are `BUY >= 75`, `WATCH >= 50`, and `NO_TRADE` below
`50`. Stale, future, invalid, unsupported, uncertain, invalidated, or tampered
evidence fails closed. The evaluator uses only supplied point-in-time context
and configuration; it never reads an uncontrolled wall clock. No ranking,
comparison, authorization, capital allocation, execution, wallet, RPC, DEX,
signing, broadcast, or LLM behavior is included.

## 11. P06-T03 bounded deep-analysis closure

P06-T03 adds the optional standalone `BoundedDeepAnalysis` record described in
`docs/P06-T03_SPECIFICATION.md`. It is immutable, versioned as `p06-t03-v1`,
bounded, provenance-preserving, canonical, and deterministically digested.
Supplied observations and generated narrative are represented separately.
Stale, future, incomplete, unsupported, non-canonical, tampered, and oversized
records are rejected using caller-supplied timestamps only.

The record is non-authoritative analytical context. P06-T02 remains the sole
authority for deterministic evaluation, and its result is unchanged when this
optional record is absent. No action, ranking, authorization, capital,
execution, provider I/O, or LLM behavior was added.