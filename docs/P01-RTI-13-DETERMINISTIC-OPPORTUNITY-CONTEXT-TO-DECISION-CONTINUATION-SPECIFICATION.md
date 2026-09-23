# P01-RTI-13 — Deterministic OpportunityContext-to-Decision Continuation Specification

## Status

- **Gate:** P01-RTI-13
- **Title:** Deterministic OpportunityContext-to-Decision Continuation
- **Specification status:** APPROVED
- **Implementation status:** LIMITED IMPLEMENTATION AUTHORIZED / IN PROGRESS
- **Runtime status:** NO CONCRETE RUNTIME CALLER AUTHORIZED
- **Proposed contract version:** `p01-rti-13-v1`

## 1. Purpose

P01-RTI-12 terminates at one canonical P05-T08 `OpportunityContext`.

P06-T02 is already the deterministic owner that evaluates one validated
`OpportunityContext` using one versioned `DecisionEvaluationRuleset` and
produces one immutable P06-T01 `DecisionIntent`.

P01-RTI-13 defines only the missing bounded application continuation:

```
canonical P01-RTI-12 result
        ↓ only if CONTEXT_MATERIALIZED
exact OpportunityContext
+ exact DecisionEvaluationRuleset
+ exact explicit decision_time
        ↓ P06-T02 exactly once
canonical P06-T01 DecisionIntent
        ↓
STOP
```

The gate adds no decision algorithm, no new action semantics, no Risk/Capital
authority, and no paper/execution behavior.

## 2. Repository authority and dependency findings

| Dependency | Repository status | RTI-13 use |
| --- | --- | --- |
| P01-RTI-12 | COMPLETE / CLOSED / CI PASS | Sole upstream result |
| P05-T08 OpportunityContext | COMPLETE / CLOSED / AUDITED PASS | Exact decision context |
| P06-T01 DecisionIntent | COMPLETE / CLOSED / AUDITED PASS | Exact terminal domain output |
| P06-T02 deterministic evaluation | COMPLETE / CLOSED / AUDITED PASS | Exactly one delegate call |
| Risk/Capital Authority | Existing independent authority | Prohibited / downstream |
| P07 / paper admission | Existing downstream owners | Prohibited |
| Concrete runtime caller | Not selected | Prohibited |
| G2/G3/G4/P09 | Blocked/unauthorized | Prohibited |

P06-T02 does not expose a separate P06-T02 result contract. It directly returns
P06-T01 `DecisionIntent`.

## 3. Exact input contract

A future RTI-13 service accepts exactly three caller-supplied inputs:

```python
upstream_result: P01Rti12ContinuationResult
decision_ruleset: DecisionEvaluationRuleset
decision_time: datetime
```

No input may be inferred from:

- environment;
- wall clock;
- global configuration;
- module default ruleset;
- database;
- runtime state;
- provider state;
- previous invocation.

### 3.1 Upstream input

`upstream_result` must be one canonical `P01Rti12ContinuationResult` with
exact contract version:

```
p01-rti-12-v1
```

Tampering, structural mismatch, digest mismatch, or unsupported version is a
validation failure.

### 3.2 Ruleset input

`decision_ruleset` must be exactly one canonical
`DecisionEvaluationRuleset` with:

```
version = p06-t02-rules-v1
```

Its canonical representation and digest must validate under the existing P06
owner contract.

RTI-13 must not use `DEFAULT_DECISION_EVALUATION_RULESET` as an implicit
fallback.

### 3.3 Decision-time input

`decision_time` must be:

- an explicit `datetime`;
- timezone-aware;
- canonicalized to UTC by existing P06 semantics;
- not earlier than `OpportunityContext.reference_time`.

RTI-13 must never substitute wall-clock time or silently default to
`context.reference_time`.

## 4. Version binding

| Surface | Exact binding |
| --- | --- |
| RTI-13 | `p01-rti-13-v1` |
| RTI-12 | `p01-rti-12-v1` |
| P05-T08 context | `p05-t08-v1` |
| P05-T08 evaluator | `p05-t08-context-v1` |
| P06-T01 DecisionIntent | `p06-t01-v1` |
| P06-T02 ruleset | `p06-t02-rules-v1` |
| P06-T02 evaluator | `p06-t02-evaluator-v1` |

There is no:

- latest-version lookup;
- alias-based version resolution;
- fallback;
- silent upgrade;
- downgrade;
- conversion.

Adding a later version requires a separate governance decision.

## 5. Proposed RTI-13 outcome vocabulary

The exact RTI-13 wrapper outcomes are:

- `DECISION_MATERIALIZED`
- `UPSTREAM_NOT_MATERIALIZED`
- `DECISION_UNAVAILABLE`

No other RTI-13 outcome is authorized by this specification.

These wrapper outcomes describe application composition only. They do not
replace or reinterpret the P06 analytical `DecisionAction`.

## 6. Non-materialized upstream behavior

If `upstream_result` is canonical but its outcome is not exactly
`CONTEXT_MATERIALIZED`, including:

- `UPSTREAM_NOT_COMPOSED`;
- `MATERIALIZATION_UNAVAILABLE`;

RTI-13 returns:

```
UPSTREAM_NOT_MATERIALIZED
```

and:

- preserves the exact RTI-12 result;
- preserves exact RTI-12 outcome, reason codes, and result digest;
- does not invoke P06-T02;
- does not create or reconstruct an `OpportunityContext`;
- does not invoke Risk/Capital or any later owner.

## 7. Exact success flow

For one canonical RTI-12 result whose outcome is exactly
`CONTEXT_MATERIALIZED`:

1. require the exact embedded `OpportunityContext`;
2. require exact context contract/evaluator versions;
3. require exact object linkage back to the RTI-12 record/history/context chain;
4. validate explicit canonical P06-T02 ruleset;
5. validate explicit `decision_time`;
6. invoke exactly:
   `evaluate_decision_intent(context, ruleset=decision_ruleset, decision_time=decision_time)`;
7. invoke it exactly once;
8. require one canonical `DecisionIntent`;
9. require `DecisionIntent.context is upstream_result.context`;
10. require exact P06-T01/P06-T02 version bindings;
11. preserve exact P05/P06 provenance and digests;
12. return `DECISION_MATERIALIZED`;
13. stop.

The alias `evaluate_decision` must not be tried as a fallback.

## 8. DecisionIntent success predicate

A returned value is successful only when all of the following are true:

- it is a `DecisionIntent`;
- `contract_version == "p06-t01-v1"`;
- `ruleset_version == "p06-t02-rules-v1"`;
- `evaluator_version == "p06-t02-evaluator-v1"`;
- `context is upstream_result.context`;
- `context_digest == upstream_result.context.digest`;
- candidate/chain/token identity matches the exact context;
- P05-T06/T07/T08 provenance reachable through the context is unchanged;
- `decision_time` equals the explicit caller-supplied decision time after
  existing UTC normalization;
- canonical representation equals deterministic representation;
- the existing P06 digest recomputes exactly.

The wrapper must accept every P06-authorized analytical action that is valid
under the existing P06 owner contract. RTI-13 must not prefer, reject, upgrade,
or reinterpret `BUY`, `WATCH`, `HOLD`, `TAKE_PROFIT`, `REDUCE`,
`EXIT`, `AVOID`, or `NO_TRADE`.

## 9. Analytical-only semantics

A successful `DecisionIntent` remains analytical.

In particular:

- `BUY` is not capital authorization;
- confidence is not probability of profit;
- `EntryPosture.WAIT` is not an order;
- no `DecisionIntent` may bypass Risk/Capital Authority;
- RTI-13 cannot allocate capital;
- RTI-13 cannot create P07 input;
- RTI-13 cannot trigger execution.

The independent Risk/Capital boundary remains higher authority.

## 10. Validation semantics

The following remain raised application validation failures
(`ValueError`), not bounded RTI-13 results:

- malformed upstream type;
- canonical RTI-12 validation failure;
- upstream tampering/digest mismatch;
- RTI-12 version mismatch;
- malformed or unsupported ruleset;
- ruleset tampering/digest mismatch;
- ruleset version mismatch;
- naive/non-datetime decision time;
- decision time before context reference time;
- malformed/tampered P05-T08 context;
- P06-T02 `ValueError`.

P06-T02 `ValueError` must be re-raised as one standardized safe RTI-13
validation message. Raw owner exception text must not leak.

## 11. Bounded owner failure semantics

P06-T02 currently has no bounded result vocabulary separate from
`DecisionIntent`.

Therefore:

- unexpected non-validation exception from P06-T02 maps to
  `DECISION_UNAVAILABLE` with finite reason
  `P06_T02_UNAVAILABLE`;
- invalid return type maps to `DECISION_UNAVAILABLE` with
  `P06_T02_INVALID_RESULT`;
- a returned `DecisionIntent` that violates identity, version, canonical,
  digest, or explicit decision-time requirements maps to
  `DECISION_UNAVAILABLE` with `P06_T02_INVALID_RESULT`.

Raw exception type, text, traceback, callable identity, or internal object
address must never enter result or digest.

There is no retry.

## 12. Delegation cardinality

| Condition | P06-T02 calls |
| --- | ---: |
| canonical RTI-12 `CONTEXT_MATERIALIZED` | exactly 1 |
| canonical RTI-12 non-materialized outcome | 0 |
| validation failure before delegation | 0 |

There is no second P06 call, fallback alias, correction, repair, or
re-evaluation.

## 13. Identity and provenance continuity

RTI-13 must preserve:

- exact RTI-12 result identity and digest;
- exact RTI-12 context object;
- candidate identity;
- chain identity;
- token identity;
- reference time;
- P03 lineage;
- P04 signal/feature lineage;
- P05-T05 score;
- P05-T06 record;
- P05-T07 history;
- P05-T08 context;
- P06-T02 ruleset version/digest;
- P06-T01 DecisionIntent digest.

RTI-13 must not:

- copy/reconstruct the `OpportunityContext`;
- recalculate safety;
- recalculate eligibility;
- recalculate signals/features;
- recalculate P05 score;
- synthesize missing provenance;
- alter the P06 ruleset;
- alter the P06 decision action;
- create a second decision.

## 14. Proposed immutable RTI-13 result

A future immutable RTI-13 result should contain only bounded application
composition material required to preserve evidence:

- `contract_version`;
- `outcome`;
- finite canonical `reason_codes`;
- exact `upstream_result`;
- exact explicit `decision_ruleset` reference or canonical ruleset digest
  material;
- exact explicit `decision_time`;
- optional exact `DecisionIntent`;
- deterministic `result_digest`.

It must not add:

- capital amount;
- authorization;
- order parameters;
- transaction fields;
- wallet fields;
- execution route;
- realized outcome;
- profit/ROI labels.

## 15. Deterministic result digest

The RTI-13 `result_digest` must be lowercase SHA-256 over UTF-8 canonical JSON
using:

- sorted keys;
- compact separators;
- `ensure_ascii=True`.

It must bind exactly:

- RTI-13 contract version;
- RTI-13 outcome;
- canonical RTI-13 reason codes;
- RTI-12 contract version;
- RTI-12 outcome;
- RTI-12 result digest;
- explicit decision ruleset version;
- explicit decision ruleset digest;
- explicit canonical UTC decision time;
- P06-T01 contract version, where present;
- P06-T02 ruleset version, where present;
- P06-T02 evaluator version, where present;
- P06 `DecisionIntent.digest`, where present.

It must exclude:

- wall clock;
- environment;
- module globals unrelated to canonical versions;
- callable identity;
- exception type/text/traceback;
- object address;
- filesystem order;
- unordered iteration;
- shared mutable state.

Equivalent canonical inputs and equivalent owner results must produce the same
RTI-13 digest.

## 16. No hidden defaults

Although P06-T02 currently supports:

- a module default ruleset; and
- omitted `decision_time` that becomes `context.reference_time`;

RTI-13 must not rely on either default.

The caller owns both explicit facts.

This keeps RTI-13 deterministic and prevents application composition from
silently becoming configuration or timing authority.

## 17. No-side-effect and unreachability guarantees

RTI-13 itself performs no external I/O.

The following must be statically and behaviorally unreachable:

- RTI-12 execution;
- P04/provider/network;
- persistence/publication;
- API/WebSocket;
- concrete runtime caller;
- Risk/Capital evaluation;
- P07;
- P01-RTI-01;
- RTI paper lifecycle/persistence;
- retry/polling;
- worker/scheduler/queue;
- dashboard/Hunter Room;
- wallet/private key/signing;
- RPC/DEX routing;
- broadcast;
- economic realization/settlement;
- execution/live trading;
- G2/G3/G4/P09.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.

## 18. Future focused test matrix

A separately authorized implementation must prove:

- exact `DECISION_MATERIALIZED` success path;
- both canonical RTI-12 non-materialized outcomes;
- zero P06 calls on non-materialized upstream;
- malformed/tampered upstream validation;
- ruleset type/version/canonical/digest validation;
- explicit decision-time validation;
- exact one P06-T02 call;
- exact context object identity;
- exact ruleset and decision-time propagation;
- all valid P06 analytical actions remain owner-controlled;
- P06 `ValueError` remains standardized validation failure;
- unexpected P06 exception becomes safe bounded unavailable;
- invalid P06 type becomes safe bounded unavailable;
- wrong context/version/time/digest returned by owner is rejected;
- deterministic RTI-13 digest;
- no retry/fallback/second evaluation;
- no shared mutable state;
- forbidden-boundary static imports/calls are absent.

Relevant regression must include:

- P01-RTI-12;
- P05-T08;
- P06-T01;
- P06-T02;
- P01-RTI-01 regression unchanged;
- combined relevant RTI regression;
- full Python regression;
- compilation/static checks;
- TypeScript typecheck/build as required by CI;
- whitespace / diff check.

## 19. Expected future implementation scope

Only after separate implementation authorization, expected maximum scope is:

- `backend/application/opportunity_context_to_decision_continuation.py`;
- `tests/test_opportunity_context_to_decision_continuation.py`;
- minimal `backend/application/__init__.py` export if required;
- governance documentation.

No:

- model;
- migration;
- repository/session;
- dependency;
- route;
- API schema;
- configuration;
- secret;
- concrete runtime caller.

## 20. Open questions

No architecture blocker remains for controller review if the controller accepts
all of these locks:

1. exactly three explicit inputs: RTI-12 result, ruleset, decision time;
2. exactly three wrapper outcomes;
3. P06-T02 `ValueError` remains raised validation failure;
4. only unexpected/invalid owner output becomes bounded
   `DECISION_UNAVAILABLE`;
5. exact context object identity is mandatory;
6. module default ruleset and implicit decision-time default are forbidden;
7. terminal boundary is exactly P06-T01 `DecisionIntent`;
8. Risk/Capital and all later authorities remain unreachable.

## 21. Controller recommendation

Approve this specification as the final P01-RTI-13 contract.

Implementation should remain separately authorized and bounded to one thin
application service, one focused test module, minimal export, and governance
documentation.

No concrete runtime caller, Risk/Capital call, paper path, persistence,
publication, provider loop, API, dashboard, wallet, execution, G2, G3, G4, or
P09 should be authorized by specification approval.

The controller subsequently approved this specification and authorized limited
implementation confined to the exact scope above. No concrete runtime caller or
downstream authority was authorized.

`SPECIFICATION APPROVED / LIMITED IMPLEMENTATION AUTHORIZED`
