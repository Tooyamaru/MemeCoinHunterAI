# Post-P01-RTI-13 Next-Gate Selection

## Status

- **Base state:** P01-RTI-13 COMPLETE / CLOSED / CI PASS
- **Selection result:** P01-RTI-14 recommended
- **Recommended gate:** P01-RTI-14 — Deterministic Decision-to-Risk/Capital Continuation
- **Current action:** specification/readiness only
- **Implementation:** NOT AUTHORIZED by this selection record

## Repository findings

P01-RTI-13 now terminates at one canonical P06-T01 `DecisionIntent`.

Repository evidence shows that the existing paper-only Risk/Capital Authority:

- consumes exactly one `DecisionIntent`;
- consumes exactly one immutable `PaperRiskCapitalPolicySnapshot`;
- validates the decision, policy, nested state digests, scope identity,
  provenance, freshness, policy validity, and capital/exposure limits;
- returns one immutable `PaperRiskCapitalAuthorizationResult`;
- exposes only `APPROVED` or `REJECTED` domain status;
- preserves a deterministic reason precedence for rejection;
- sets `authorization_effect` exactly to
  `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`;
- is explicitly not an order and does not execute.

The existing P01-RTI-01 path currently recomputes the P06 decision from an
`OpportunityContext` before invoking this Risk/Capital Authority. Now that
P01-RTI-13 already owns the bounded continuation to the canonical
`DecisionIntent`, the smallest next integration gate is a direct continuation
from that RTI-13 result into the existing Risk/Capital owner.

## Candidate assessment

| Candidate | Readiness | Primary concern | Decision |
| --- | --- | --- | --- |
| RTI-13 → Risk/Capital Authority | High | Exact policy/intent identity and paper-only authority must remain locked | **Recommended** |
| RTI-13 → P07 directly | Ineligible | Would bypass independent Risk/Capital authority | Reject |
| RTI-13 → RTI-01 | Medium | Re-evaluates P06 and crosses multiple owners | Defer |
| Concrete runtime caller | Low/partial | Caller/config/cadence authority remains unresolved | Defer |
| Persistence/publication/API/dashboard | Low | New runtime/presentation authority before composition is closed | Defer |
| G2/G3/G4/P09 | Blocked/unauthorized | Separate economic/execution authority | Ineligible |

## Recommended bounded shape

P01-RTI-14 should:

1. accept exactly one canonical `P01Rti13DecisionContinuationResult`;
2. accept exactly one explicit canonical `PaperRiskCapitalPolicySnapshot`;
3. continue only when RTI-13 outcome is exactly `DECISION_MATERIALIZED`;
4. pass the exact embedded `DecisionIntent` and exact policy snapshot to
   `evaluate_paper_risk_capital_authorization(...)` exactly once;
5. accept either canonical `APPROVED` or canonical `REJECTED` as a valid
   Risk/Capital domain result;
6. preserve exact decision/policy/result identity, provenance, versions, scope,
   reason codes, authorization id, and digests;
7. stop at `PaperRiskCapitalAuthorizationResult`;
8. not create `AuthorizationObservation`, P07 input, paper lifecycle, fill,
   position, ledger, persistence, runtime caller, wallet, or execution.

## Key repository-specific constraints

Exact current Risk/Capital bindings are:

- policy contract: `p08-risk-capital-policy-v1`;
- authority contract: `p08-risk-capital-authority-v1`;
- authority evaluator: `p08-risk-capital-authority-evaluator-v1`;
- authorization effect:
  `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`.

The canonical owner is:

`evaluate_paper_risk_capital_authorization(decision_intent, policy_snapshot)`.

Aliases exist, but RTI-14 must not use alias fallback.

The policy snapshot itself binds:

- `decision_intent_digest`;
- `context_digest`;
- candidate / chain / token scope;
- paper lifecycle and paper portfolio scope;
- risk state;
- paper capital state;
- paper exposure state;
- policy validity/freshness;
- provenance and state digests.

RTI-14 must not construct, infer, repair, or default any of these facts.

## Governance boundary

The existing authority result remains **paper-only**.

Even an `APPROVED` result authorizes only:

`PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`

It is not:

- live capital authorization;
- an exchange/DEX order;
- a transaction request;
- signing authority;
- wallet authority;
- broadcast permission;
- proof of execution;
- proof of economic settlement.

P07 remains a separate downstream owner.

## Controller recommendation

Proceed to a formal P01-RTI-14 specification that locks:

- exact two-input boundary;
- exact wrapper outcomes;
- exact policy/decision identity linkage;
- exact authority version/effect binding;
- exact once-only delegation;
- APPROVED and REJECTED as equally valid domain results;
- validation versus bounded owner failure semantics;
- deterministic RTI-14 result digest;
- paper-only authority semantics;
- hard unreachability of P07 and all later execution/economic surfaces.

This selection document does not authorize implementation.
