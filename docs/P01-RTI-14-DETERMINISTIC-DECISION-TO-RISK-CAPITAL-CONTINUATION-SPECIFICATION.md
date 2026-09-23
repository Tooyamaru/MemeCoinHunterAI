# P01-RTI-14 — Deterministic Decision-to-Risk/Capital Continuation Specification

## Status

- **Gate:** P01-RTI-14
- **Title:** Deterministic Decision-to-Risk/Capital Continuation
- **Specification status:** COMPLETE / READY FOR CONTROLLER REVIEW
- **Implementation status:** NOT AUTHORIZED
- **Runtime status:** NO CONCRETE RUNTIME CALLER AUTHORIZED
- **Proposed contract version:** `p01-rti-14-v1`

## 1. Purpose

P01-RTI-13 terminates at one canonical P06-T01 `DecisionIntent`.

The existing paper-only Risk/Capital Authority consumes exactly one immutable
`DecisionIntent` and one immutable `PaperRiskCapitalPolicySnapshot`, then
returns one immutable `PaperRiskCapitalAuthorizationResult`.

P01-RTI-14 defines only this missing bounded application continuation:

```
canonical P01-RTI-13 result
        ↓ only if DECISION_MATERIALIZED
exact DecisionIntent
+ exact PaperRiskCapitalPolicySnapshot
        ↓ authority exactly once
PaperRiskCapitalAuthorizationResult
        ↓
STOP
```

The gate does not create policy, does not create P07 input, and does not execute
or persist anything.

## 2. Dependencies and readiness

| Dependency | Status | RTI-14 use |
| --- | --- | --- |
| P01-RTI-13 | COMPLETE / CLOSED / CI PASS | Sole upstream result |
| P06-T01 DecisionIntent | COMPLETE / CLOSED / AUDITED PASS | Exact authority input |
| Paper Risk/Capital policy | COMPLETE / CLOSED / AUDITED PASS | Explicit caller-owned policy |
| Paper Risk/Capital Authority | COMPLETE / CLOSED / AUDITED PASS | Exactly one delegate call |
| P07 | COMPLETE / CLOSED downstream owner | Prohibited in RTI-14 |
| Runtime caller | Not selected | Prohibited |
| G2/G3/G4/P09 | Blocked/unauthorized | Prohibited |

## 3. Exact input contract

A future RTI-14 service accepts exactly two caller-supplied inputs:

```python
upstream_result: P01Rti13DecisionContinuationResult
policy_snapshot: PaperRiskCapitalPolicySnapshot
```

No policy field may be inferred from environment, defaults, wall clock,
database state, previous invocation, or a runtime caller.

## 4. Exact version binding

| Surface | Exact binding |
| --- | --- |
| RTI-14 | `p01-rti-14-v1` |
| RTI-13 | `p01-rti-13-v1` |
| P06 DecisionIntent | `p06-t01-v1` |
| P06 ruleset | `p06-t02-rules-v1` |
| P06 evaluator | `p06-t02-evaluator-v1` |
| Risk/Capital policy | `p08-risk-capital-policy-v1` |
| Risk/Capital result | `p08-risk-capital-authority-v1` |
| Risk/Capital evaluator | `p08-risk-capital-authority-evaluator-v1` |
| Authorization effect | `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY` |

No latest lookup, alias resolution, silent fallback, conversion, upgrade, or
downgrade is authorized.

## 5. Proposed RTI-14 wrapper outcomes

The exact wrapper outcome vocabulary is:

- `AUTHORIZATION_MATERIALIZED`
- `UPSTREAM_NOT_DECIDED`
- `AUTHORIZATION_UNAVAILABLE`

These are application-composition outcomes only.

They do not replace or reinterpret the domain-level
`AuthorizationStatus.APPROVED` or `AuthorizationStatus.REJECTED`.

## 6. Non-materialized upstream behavior

If a canonical RTI-13 result is not exactly `DECISION_MATERIALIZED`, including:

- `UPSTREAM_NOT_MATERIALIZED`;
- `DECISION_UNAVAILABLE`;

RTI-14 returns:

`UPSTREAM_NOT_DECIDED`

and:

- preserves the exact RTI-13 result and digest;
- preserves the exact explicit policy snapshot and digest;
- performs zero Risk/Capital calls;
- creates no authorization result;
- creates no P07 material.

## 7. Exact success flow

Only for canonical RTI-13 `DECISION_MATERIALIZED`:

1. require the exact embedded `DecisionIntent`;
2. validate exact RTI-13/P06 identity and version bindings;
3. validate the exact explicit `PaperRiskCapitalPolicySnapshot`;
4. require exact policy contract/evaluator versions;
5. require the policy's decision and context digests to match the exact
   `DecisionIntent`;
6. require policy candidate/chain/token scope to match the exact decision;
7. delegate exactly once to:
   `evaluate_paper_risk_capital_authorization(decision_intent, policy_snapshot)`;
8. require one canonical `PaperRiskCapitalAuthorizationResult`;
9. accept either canonical `APPROVED` or canonical `REJECTED` as successful
   authority materialization;
10. preserve exact result status, reason precedence, identity, scope,
    provenance, authorization id, and digest;
11. require authorization effect exactly
    `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`;
12. return `AUTHORIZATION_MATERIALIZED`;
13. stop.

The aliases `evaluate_risk_capital_authority`, `authorize_paper_lifecycle`,
and `evaluate` must not be tried as fallbacks.

## 8. Policy pre-delegation requirements

The policy must be canonical under the existing owner contract.

RTI-14 must reject before delegation when any of the following is malformed,
unsupported, tampered, or mismatched:

- policy contract/evaluator version;
- policy snapshot digest;
- nested risk state digest;
- nested paper capital state digest;
- nested paper exposure state digest;
- policy provenance shape;
- decision intent digest;
- context digest;
- candidate identity;
- chain identity;
- token identity.

RTI-14 must not pre-decide policy freshness, budget, exposure, risk state, or
approval/rejection. Those semantics remain owned by the Risk/Capital evaluator.

## 9. APPROVED and REJECTED are both valid owner outputs

RTI-14 must not treat a canonical `REJECTED` result as an application failure.

A canonical rejected authority result remains:

`AUTHORIZATION_MATERIALIZED`

with the exact owner-provided:

- `status = REJECTED`;
- `primary_reason_code`;
- ordered `reason_codes`;
- authorization identity;
- provenance;
- result digest.

Likewise a canonical approved result is:

`AUTHORIZATION_MATERIALIZED`

with:

- `status = APPROVED`;
- no rejection reasons;
- exact owner identity and digest.

RTI-14 must not upgrade REJECTED to APPROVED, suppress reasons, or invent a
second classification layer.

## 10. Result success predicate

A returned owner result is valid only when:

- it is a `PaperRiskCapitalAuthorizationResult`;
- contract version equals `p08-risk-capital-authority-v1`;
- evaluator version equals `p08-risk-capital-authority-evaluator-v1`;
- authorization effect equals `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`;
- status is exactly `APPROVED` or `REJECTED`;
- decision intent digest equals the exact RTI-13 DecisionIntent digest;
- context digest equals the exact DecisionIntent context digest;
- policy snapshot id/digest equal the exact supplied policy;
- scope equals the policy scope;
- paper lifecycle id matches policy scope;
- candidate/chain/token scope remains exact;
- provenance binds decision, context, policy, nested states, and versions;
- authorization id is canonical;
- canonical and deterministic representations match;
- result digest recomputes exactly.

## 11. Validation semantics

The following remain raised application validation failures (`ValueError`):

- malformed upstream type;
- non-canonical/tampered RTI-13 result;
- unsupported RTI-13 version;
- malformed policy type;
- policy contract/evaluator version mismatch;
- policy/nested digest tampering;
- policy provenance structural failure;
- explicit decision/context digest mismatch;
- explicit candidate/chain/token scope mismatch;
- malformed/tampered DecisionIntent;
- Risk/Capital owner `ValueError`.

Owner `ValueError` must become one standardized safe RTI-14 validation
message. Raw exception details must not leak.

## 12. Bounded owner failure semantics

Unexpected non-validation exceptions from the authority map to:

- outcome: `AUTHORIZATION_UNAVAILABLE`;
- reason: `RISK_CAPITAL_UNAVAILABLE`.

Invalid owner return type or invalid canonical owner result maps to:

- outcome: `AUTHORIZATION_UNAVAILABLE`;
- reason: `RISK_CAPITAL_INVALID_RESULT`.

No raw exception text/type/traceback enters result or digest.

There is no retry.

## 13. Delegation cardinality

| Condition | Risk/Capital calls |
| --- | ---: |
| canonical RTI-13 `DECISION_MATERIALIZED` with valid explicit policy | exactly 1 |
| canonical RTI-13 non-decision outcome | 0 |
| validation failure before delegation | 0 |

No second evaluation, fallback alias, repair, or policy reconstruction is
permitted.

## 14. Identity and provenance continuity

RTI-14 preserves exact:

- RTI-13 result and digest;
- DecisionIntent object and digest;
- OpportunityContext lineage;
- P05/P06 versions and provenance;
- policy object and policy snapshot digest;
- policy risk/capital/exposure state digests;
- policy scope;
- authority status and reasons;
- authority authorization id and result digest.

RTI-14 must not synthesize or reconstruct:

- DecisionIntent;
- policy snapshot;
- lifecycle identity;
- portfolio identity;
- risk state;
- capital state;
- exposure state;
- provenance;
- approval/rejection reasons.

## 15. Proposed immutable RTI-14 result

A future immutable wrapper should contain only:

- RTI-14 contract version;
- wrapper outcome;
- canonical finite reason codes;
- exact upstream RTI-13 result;
- exact explicit policy snapshot;
- optional exact authority result;
- deterministic RTI-14 result digest.

It must not contain or create:

- P07 simulation input;
- fill;
- position;
- ledger;
- live capital balance;
- transaction;
- wallet;
- route;
- signature;
- broadcast;
- settlement;
- profit/ROI.

## 16. Deterministic RTI-14 result digest

Lowercase SHA-256 over canonical JSON using sorted keys, compact separators,
UTF-8, and `ensure_ascii=True`.

The digest must bind exactly:

- RTI-14 contract version;
- RTI-14 outcome;
- RTI-14 reason codes;
- RTI-13 contract version;
- RTI-13 outcome;
- RTI-13 result digest;
- policy contract version;
- policy evaluator version;
- policy snapshot id;
- policy snapshot digest;
- authority contract version, where present;
- authority evaluator version, where present;
- authority status, where present;
- authorization effect, where present;
- authorization id, where present;
- authority result digest, where present.

It must exclude wall-clock state, environment, callable identity, exception
details, object address, filesystem order, unordered iteration, and shared
mutable state.

## 17. Paper-only authority boundary

A successful owner result remains paper-only.

Even:

`status = APPROVED`

does **not** authorize live trading.

Its exact effect remains:

`PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`.

RTI-14 cannot:

- create P07 input;
- start paper simulation;
- mutate capital;
- place an order;
- create an execution request;
- sign;
- broadcast;
- access a wallet;
- claim economic realization.

## 18. No-side-effect and unreachability requirements

RTI-14 must not reach:

- P07;
- P01-RTI-01;
- paper lifecycle;
- fill/position/ledger/reconciliation;
- persistence/publication;
- API/WebSocket;
- concrete runtime caller;
- provider/network;
- retry/polling;
- worker/scheduler/queue;
- dashboard/Hunter Room;
- wallet/private key/signing;
- RPC/DEX routing;
- broadcast;
- G2 realization/settlement;
- G3/G4/P09;
- live execution/trading.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.

## 19. Future focused test matrix

A separately authorized implementation must prove:

1. exact APPROVED authority materialization;
2. exact REJECTED authority materialization;
3. non-decision RTI-13 outcomes invoke authority zero times;
4. malformed/tampered RTI-13 fails before authority;
5. malformed/tampered policy fails before authority;
6. policy decision/context digest mismatch fails before authority;
7. policy candidate/chain/token scope mismatch fails before authority;
8. exact once-only delegation;
9. exact DecisionIntent object identity passed to owner;
10. exact policy object identity passed to owner;
11. owner `ValueError` becomes standardized validation failure;
12. unexpected owner exception becomes bounded unavailable;
13. invalid owner type becomes bounded invalid-result;
14. wrong status/version/effect/digest/scope/provenance result is rejected;
15. deterministic wrapper digest;
16. rejection reason order preserved exactly;
17. no retry/fallback;
18. P07 and forbidden runtime surfaces remain unreachable.

Relevant regression must include:

- P01-RTI-13;
- P06-T01/T02;
- Risk/Capital authority focused tests;
- P01-RTI-01 regression unchanged;
- full Python suite;
- static/compile checks;
- TypeScript typecheck/build as required by CI;
- whitespace/diff check.

## 20. Expected future implementation scope

Only after separate implementation authorization:

- `backend/application/decision_to_risk_capital_continuation.py`;
- `tests/test_decision_to_risk_capital_continuation.py`;
- minimal `backend/application/__init__.py` export;
- governance documentation.

No database model, migration, repository, session, API route, dependency,
configuration, secret, concrete runtime caller, P07 integration, or execution
surface is authorized.

## 21. Controller recommendation

Approve this specification as the final P01-RTI-14 contract.

Implementation should remain separately authorized and confined to one thin
application service, one focused test module, minimal export, and governance
documentation.

No P07, paper lifecycle, persistence, provider loop, API/dashboard, wallet,
execution, G2, G3, G4, or P09 authority is authorized by this specification.

`SPECIFICATION READY FOR CONTROLLER REVIEW`
