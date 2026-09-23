# Post-P01-RTI-12 Next-Gate Selection

## Status

- **Base state:** P01-RTI-12 COMPLETE / CLOSED / CI PASS
- **Selection result:** P01-RTI-13 recommended
- **Recommended gate:** P01-RTI-13 — Deterministic OpportunityContext-to-Decision Continuation
- **Current action:** specification/readiness only
- **Implementation:** NOT AUTHORIZED by this selection record

## Repository findings

P01-RTI-12 now terminates at one canonical P05-T08 `OpportunityContext`.

Repository evidence shows:

- P06-T01 `DecisionIntent` is COMPLETE / CLOSED / AUDITED PASS;
- P06-T02 deterministic evaluation is COMPLETE / CLOSED / AUDITED PASS;
- P06-T02 consumes exactly one validated P05-T08 `OpportunityContext`;
- P06-T02 applies one immutable `DecisionEvaluationRuleset`;
- P06-T02 produces one P06-T01 `DecisionIntent`;
- P06-T02 performs no ranking, capital authorization, execution, wallet,
  signing, RPC, DEX routing, or broadcast;
- P01-RTI-01 already consumes an `OpportunityContext` and independently calls
  P06-T02 as part of a larger paper-admission flow.

P01-RTI-13 therefore fills only the missing bounded application continuation
between the newly closed RTI-12 result and the already closed P06-T02 owner.

## Candidate assessment

| Candidate | Readiness | Primary concern | Decision |
| --- | --- | --- | --- |
| RTI-12 → P06-T02 decision continuation | High | Requires explicit ruleset/time and exact P06 output validation | **Recommended** |
| Concrete runtime caller | Low/partial | Caller/config/source cadence authority still unresolved | Defer |
| RTI-12 → RTI-01 paper admission | Medium | Would cross decision + Risk/Capital + P07 in one step | Defer |
| Persistence/publication of RTI-12/P06 output | Low | New storage/publication authority | Defer |
| API/dashboard publication | Low | Presentation/runtime surface without caller owner | Defer |
| G2/G3/G4/P09 | Blocked/unauthorized | Separate economic/execution authority | Ineligible |

## Recommended bounded shape

P01-RTI-13 should:

1. accept exactly one canonical `P01Rti12ContinuationResult`;
2. require one explicit canonical `DecisionEvaluationRuleset`;
3. require one explicit timezone-aware `decision_time`;
4. continue only when RTI-12 outcome is exactly `CONTEXT_MATERIALIZED`;
5. pass the exact P05-T08 `OpportunityContext`, exact ruleset, and exact
   decision time to P06-T02 exactly once;
6. require one canonical P06-T01 `DecisionIntent` linked to the exact input
   context and exact P06-T02 ruleset/evaluator versions;
7. stop at `DecisionIntent`;
8. not call Risk/Capital, P07, RTI-01, paper lifecycle, persistence, provider,
   API, runtime caller, wallet, or execution.

## Key repository-specific constraints

P06-T02 has no separate result wrapper or `P06_T02_CONTRACT_VERSION`.
The authoritative bindings are:

- P06-T01 contract: `p06-t01-v1`;
- P06-T02 ruleset: `p06-t02-rules-v1`;
- P06-T02 evaluator: `p06-t02-evaluator-v1`.

P06-T02 exposes `evaluate_decision_intent(...)` as the canonical evaluator.
The alias `evaluate_decision` exists but must not be used as a fallback.

P06-T02 can default `decision_time` to the context reference time and has a
module default ruleset, but P01-RTI-13 should require both values explicitly so
the application boundary has no hidden caller policy or ambient default.

## Governance boundary

P01-RTI-13 must remain analytical only.

A P06 `BUY` action is not:

- capital authorization;
- permission to enter;
- an order;
- a transaction request;
- wallet authority;
- execution authority.

The gate must stop before the independent Risk/Capital Authority.

It must not open:

- concrete runtime caller;
- provider/network runtime;
- persistence/publication;
- API/WebSocket;
- Risk/Capital;
- P07;
- P01-RTI-01 or later paper lifecycle;
- retry/polling;
- worker/scheduler/queue;
- dashboard/Hunter Room;
- wallet/signing/RPC/DEX;
- economic realization;
- execution/live trading;
- G2/G3/G4/P09.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.

## Controller recommendation

Proceed to a formal P01-RTI-13 specification that locks:

- exact three-input boundary;
- exact success/non-success behavior;
- exact P06-T01/P06-T02 version binding;
- validation versus bounded wrapper failure;
- exact once-only delegation;
- exact context object identity and provenance continuity;
- explicit decision-time semantics;
- deterministic RTI-13 result digest;
- analytical-only semantics;
- hard unreachability of Risk/Capital and all later authority surfaces.

This selection document does not authorize implementation.
