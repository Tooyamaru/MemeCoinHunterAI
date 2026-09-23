# P01-RTI-12 — Deterministic P05 Opportunity-Context Continuation Specification

## Status

- **Gate:** P01-RTI-12
- **Title:** Deterministic P05 Opportunity-Context Continuation
- **Specification status:** COMPLETE / APPROVED
- **Implementation status:** COMPLETE / CLOSED / CI PASS
- **Runtime status:** NO RUNTIME CALLER AUTHORIZED
- **Contract version:** `p01-rti-12-v1`

This document defines a bounded, deterministic, HTTP-independent application
continuation from one canonical `P01Rti11CompositionResult` through the
existing P05-T06, P05-T07, and P05-T08 owners. The terminal output is the
existing P05-T08 `OpportunityContext`.

The controller separately authorized limited implementation. That implementation
has now been delivered and closed without opening any runtime caller or
downstream authority boundary.

## 1. Purpose

P01-RTI-11 terminates at P05-T05 `CanonicalP04ToP05Composition`.
Existing downstream consumers P06-T02 and P01-RTI-01 require P05-T08
`OpportunityContext`.

P01-RTI-12 therefore defines the smallest deterministic continuation:

```
Canonical RTI-11 result
        ↓ only if COMPOSED
exact composition.score
        ↓ once
P05-T06 OpportunityRecord
        ↓ append once to fresh local history
P05-T07 STORED
        ↓ once
P05-T08 OpportunityContext
        ↓
STOP
```

The gate does not execute RTI-11 and does not cross into P06, paper lifecycle,
persistence, publication, provider runtime, or economic/execution authority.

## 2. Dependencies and readiness

| Dependency | Status | RTI-12 use |
| --- | --- | --- |
| RTI-11 result | Ready / closed | Sole input |
| P05-T05 score | Ready / closed | Exact `composition.score` |
| P05-T06 | Ready / closed | Materialize one record exactly once |
| P05-T07 | Ready / closed | Fresh invocation-local history; one append |
| P05-T08 | Ready / closed | Materialize one context exactly once |
| Concrete runtime caller | No owner | Not required / prohibited |
| P06 and paper path | Existing downstream owners | Out of scope |
| Persistence / publication | Not authorized | Prohibited |
| G2 / G3 / G4 / P09 | Blocked / unauthorized | Prohibited |

## 3. Exact input contract

The service accepts exactly one input:

```python
upstream_result: P01Rti11CompositionResult
```

No caller-supplied history, repository, session, persistence handle, provider,
runtime caller, clock, route, scheduler, worker, queue, or execution object is
part of the contract.

The accepted upstream contract version is exactly:

```
p01-rti-11-v1
```

Unsupported or mismatched versions fail closed as application validation
failures.

## 4. Exact output contract

The future immutable RTI-12 result uses contract version:

```
p01-rti-12-v1
```

The exact outcome vocabulary is:

- `CONTEXT_MATERIALIZED`
- `UPSTREAM_NOT_COMPOSED`
- `MATERIALIZATION_UNAVAILABLE`

No additional outcome vocabulary is authorized.

The result preserves the exact canonical upstream RTI-11 identity and, where
materialized, the exact P05-T06 record, P05-T07 history state, and P05-T08
context required by the existing owner contracts.

## 5. Non-COMPOSED upstream handling

A valid RTI-11 result whose outcome is any of:

- `TOKEN_NOT_CURRENT`
- `DIAGNOSTIC_NOT_PRODUCED`
- `COMPOSITION_UNAVAILABLE`

must return:

```
UPSTREAM_NOT_COMPOSED
```

The RTI-12 result must preserve the exact upstream result, including its:

- contract version;
- outcome;
- reason codes;
- result digest; and
- authorized upstream references/provenance.

For `UPSTREAM_NOT_COMPOSED`:

- P05-T06 is not called;
- no P05-T07 history is created or appended;
- P05-T08 is not called.

RTI-12 must not reinterpret the upstream result as trading, economic, ranking,
profitability, or execution semantics.

## 6. COMPOSED terminal flow

Only when the canonical RTI-11 outcome is exactly `COMPOSED` may RTI-12
continue.

The required flow is:

1. take the exact existing `composition.score`;
2. delegate that exact score to P05-T06 exactly once;
3. receive the exact P05-T06 `OpportunityRecord`;
4. create a new, empty, invocation-local P05-T07 history;
5. append the exact record exactly once;
6. require the P05-T07 result to be exactly valid `STORED`;
7. delegate the exact record plus exact history to P05-T08 exactly once;
8. receive the exact `OpportunityContext`;
9. stop.

No alternate branch, retry, fallback method, second append, or downstream
continuation is permitted.

## 7. P05-T07 exact success requirements

P05-T07 must produce all of the following:

- outcome exactly `STORED`;
- `accepted is True`;
- empty reason codes;
- exact record identity;
- exactly one history member;
- matching history digest.

Alias methods such as `add`, `store`, or `record` must not be tried as
fallbacks. The implementation must call only the repository-established
canonical owner method.

Any owner output that violates the required P05-T07 success contract is not a
success.

## 8. Validation versus bounded owner failure

The following remain application validation failures and must raise
`ValueError` rather than become ordinary RTI-12 outcomes:

- malformed input;
- tampering;
- identity mismatch;
- structural mismatch;
- unsupported or mismatched contract version;
- P05-T06 `ValueError`;
- P05-T08 `ValueError`.

Validation messages must be standardized and safe. Raw exception text, type,
traceback, internal state, or secret material must not enter a result or digest.

P05-T07 bounded owner outcomes:

- `INVALID_INPUT`
- `DUPLICATE`

remain distinguishable bounded owner failures and map to:

```
MATERIALIZATION_UNAVAILABLE
```

using finite, stage-specific reason codes.

Unexpected owner/internal exceptions also map to
`MATERIALIZATION_UNAVAILABLE` using finite, stage-specific safe reason codes.

There is no retry.

## 9. Delegation cardinality

| Owner | Exact input | Cardinality |
| --- | --- | --- |
| P05-T06 | exact `composition.score` | exactly 1 |
| P05-T07 | exact produced record into fresh local history | exactly 1 append |
| P05-T08 | exact record + exact history | exactly 1 |

A non-`COMPOSED` upstream result has cardinality zero for all three owners.

## 10. Fresh invocation-local history

Every RTI-12 invocation must:

- create a new empty history;
- never accept history from the caller;
- never keep history on the service;
- never keep history at module/global/singleton scope;
- never reuse history across invocations;
- never preload a record;
- never perform a second append;
- never merge or repair history;
- never persist history;
- never publish history.

Equivalent invocations may create different Python object identities, but the
canonical history content and history digest must be equivalent.

Shared mutable state is forbidden.

## 11. Version binding

| Surface | Exact version |
| --- | --- |
| RTI-12 | `p01-rti-12-v1` |
| RTI-11 | `p01-rti-11-v1` |
| P05-T06 | `p05-t06-v1` |
| P05-T06 record | `p05-t06-record-v1` |
| P05-T07 | `p05-t07-v1` |
| P05-T08 | `p05-t08-v1` |
| P05-T08 context | `p05-t08-context-v1` |

There is no:

- latest-version lookup;
- version fallback;
- alias;
- silent upgrade;
- downgrade; or
- conversion.

A mismatch fails closed.

## 12. Deterministic result-digest canonicalization

The RTI-12 result digest is lowercase SHA-256 over canonical JSON with:

- sorted keys;
- compact separators;
- UTF-8;
- `ensure_ascii=True`.

The digest binds exactly:

- RTI-12 contract version;
- RTI-12 outcome;
- RTI-12 reason codes;
- RTI-11 contract version;
- RTI-11 outcome;
- RTI-11 result digest;
- P05-T06 contract and record digest, where present;
- P05-T07 contract, outcome, and history digest, where present;
- P05-T08 contract and context digest, where present.

The digest must not depend on:

- wall-clock time;
- environment;
- callable identity;
- exception text;
- exception type;
- traceback;
- object address;
- filesystem ordering;
- dictionary iteration order; or
- shared mutable state.

Equivalent canonical inputs/results must produce the same digest.

## 13. Identity and provenance continuity

The continuation must preserve exact RTI-11 and P05 lineage.

The following must remain exact through the existing owner contracts where
applicable:

- upstream RTI-11 result identity and digest;
- candidate identity;
- chain and token identity;
- reference and evaluation time;
- P03 lineage;
- P04 signal/features lineage;
- P05-T05 score;
- P05-T06 record;
- P05-T07 history;
- P05-T08 context.

RTI-12 must not:

- synthesize identity;
- clone or reconstruct the score;
- recalculate safety;
- recalculate eligibility;
- recalculate features;
- recalculate risk;
- recalculate opportunity score;
- repair, infer, or backfill missing provenance.

Existing P05 owners remain authoritative for their own identity and canonical
contracts.

## 14. Authority boundary

RTI-12 owns only:

- application-level continuation from one canonical RTI-11 result;
- bounded input/linkage/version validation;
- exact once-only delegation to existing P05-T06/T07/T08 owners;
- the immutable bounded RTI-12 result wrapper and its deterministic digest.

RTI-12 does not own:

- RTI-11 execution;
- candidate discovery;
- pool selection;
- safety or eligibility evaluation;
- signal derivation;
- feature/scoring evaluation;
- persistence;
- publication;
- runtime caller selection;
- decision authority;
- paper simulation;
- economic interpretation;
- settlement/realization;
- execution.

## 15. No-side-effect and unreachability requirements

The specification requires proof that RTI-12 cannot reach:

- RTI-11 execution;
- provider/network calls;
- a concrete runtime caller;
- persistence/publication;
- API/WebSocket;
- P06;
- Risk/Capital;
- P07;
- paper lifecycle;
- retry/polling;
- worker/scheduler/queue;
- dashboard/Hunter Room;
- wallet/signing/RPC/DEX;
- economic realization;
- execution/live trading;
- G2;
- G3;
- G4;
- P09.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.
G3, G4, and P09 remain unauthorized.

## 16. Focused implementation test matrix

A later separately delivered limited implementation must prove:

1. exact success path;
2. all valid non-`COMPOSED` RTI-11 outcomes;
3. validation failures;
4. exact once-only P05-T06 delegation;
5. exact one-append P05-T07 behavior;
6. exact once-only P05-T08 delegation;
7. fresh history isolation;
8. no history reuse across invocations;
9. P05-T07 bounded failures;
10. unexpected owner failures;
11. invalid owner outputs;
12. exact version binding;
13. identity/provenance continuity;
14. deterministic result digest;
15. no side effects;
16. no shared mutable state;
17. all forbidden-boundary unreachability.

Relevant regression must include:

- RTI-11;
- P05-T05;
- P05-T06;
- P05-T07;
- P05-T08;
- canonical P04/P05 composition;
- combined RTI regression where applicable;
- full Python regression;
- Python compilation/static checks;
- TypeScript typecheck/build as required by repository CI;
- whitespace / `git diff --check`.

## 17. Expected limited implementation scope

When separately delivered under the already-approved limited implementation
authorization, the expected maximum implementation scope is:

- `backend/application/p05_opportunity_context_continuation.py`;
- `tests/test_p05_opportunity_context_continuation.py`;
- minimal `backend/application/__init__.py` export if required by repository convention;
- governance documentation/state/changelog.

No database model, migration, repository, session, dependency, API route,
configuration, secret boundary, or concrete runtime caller is authorized.

## 18. Forbidden implementation scope

Forbidden are:

- changes that execute RTI-11;
- provider/network integration;
- concrete runtime caller creation;
- persistence/publication;
- API/WebSocket route creation;
- P06 composition;
- Risk/Capital or P07 integration;
- paper lifecycle integration;
- retry/polling;
- worker/scheduler/queue;
- dashboard/Hunter Room;
- wallet/signing/RPC/DEX;
- economic realization/settlement;
- execution/live trading;
- G2/G3/G4/P09;
- model/migration/repository/session changes;
- dependency/config/secret additions.

## 19. Acceptance criteria

The limited implementation may be considered complete only if:

- the exact input/output contracts are implemented;
- the three-outcome vocabulary is exact;
- non-`COMPOSED` upstream results call no P05 continuation owner;
- P05-T06/T07/T08 delegation cardinality is exact;
- history is fresh and invocation-local;
- validation and bounded-owner-failure semantics match this specification;
- version binding is exact and fail-closed;
- identity/provenance continuity is preserved;
- deterministic digest rules are satisfied;
- forbidden surfaces remain unreachable;
- focused and required regression/CI checks pass;
- no scope expansion occurs.

## 20. Controller decision

The controller approved this formal specification and separately authorized a
future **limited implementation** confined to the scope above.

This documentation-only checkpoint publishes the authoritative specification
and governance state. It does not implement RTI-12 and does not start any
runtime behavior.

No gate after P01-RTI-12 is authorized or started by this document.


## 21. Closure record

P01-RTI-12 limited implementation is complete and closed.

- Application module:
  `backend/application/p05_opportunity_context_continuation.py`
- Focused tests:
  `tests/test_p05_opportunity_context_continuation.py`
- Minimal export:
  `backend/application/__init__.py`
- Implementation PR: #31
- Implementation merge commit:
  `1287316872fe95d21f321ce6b2a501a0808792a9`
- GitHub Actions run: #90
- Python 3.13 tests / whitespace: PASS
- TypeScript typecheck / build: PASS

The implementation preserves the exact three-outcome RTI-12 vocabulary,
once-only P05-T06/P05-T07/P05-T08 delegation, fresh invocation-local history,
safe validation/failure semantics, exact version binding, provenance continuity,
and deterministic canonical result digest.

No concrete runtime caller, provider/network runtime, persistence/publication,
API/WebSocket, P06, Risk/Capital, P07/paper lifecycle, retry/polling,
worker/scheduler/queue, dashboard/Hunter Room, wallet/signing/RPC/DEX,
economic realization, execution/live trading, G2, G3, G4, or P09 boundary was
opened.

No post-P01-RTI-12 gate is authorized by this closure.
