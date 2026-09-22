# P01-RTI-01 — Controlled Paper Run Admission Composition

**Status:** LIMITED IMPLEMENTATION COMPLETE / REVIEWED / CI PASS

**Phase:** P01 runtime integration over existing P05, P06, Risk/Capital, and P07 owners

**Scope:** one explicit, deterministic, paper-only admission attempt

**Authorized:** 2026-09-22

## 1. Purpose and authorization

The owner authorized documentation correction and continued implementation on
2026-09-22 after reviewing the full-project progress audit. P01-RTI-01 is the
first bounded step toward a usable paper-first runtime. It must prove that the
existing analytical and risk boundaries can be composed without transferring
their authority into an application service.

This task composes exactly one already-materialized P05-T08
`OpportunityContext` through:

1. the existing P06-T02 deterministic decision evaluator;
2. the existing independent paper Risk/Capital Authority; and
3. the existing P07-T01 paper-simulation input admission contract.

It stops before fill evaluation, position mutation, ledger creation,
reconciliation, outcome learning, persistence, scheduling, or presentation.

## 2. Existing owners remain authoritative

- P05-T08 owns the evidence-first opportunity context.
- P06-T02 owns deterministic analytical intent evaluation.
- Risk/Capital Authority owns paper lifecycle entry authorization and remains
  independent from and above P06.
- P07-T01 owns the canonical paper simulation input and admission validation.
- The caller owns the explicitly supplied execution observation, paper
  configuration, initial paper state, replay identity, and policy snapshot.

P01-RTI-01 may call these owners in order. It must not duplicate their rules,
repair their inputs, synthesize favorable state, or reinterpret a rejection as
approval.

## 3. Input boundary

One invocation receives explicitly:

- one validated `OpportunityContext`;
- one `DecisionEvaluationRuleset`;
- one `PaperRiskCapitalPolicySnapshot` already linked to the deterministic
  decision the caller expects for this context;
- one `ExecutionObservation`;
- one `SimulationConfigurationIdentity`;
- one `InitialPaperStateIdentity`;
- one `ReplayIdentity`; and
- an optional explicit timezone-aware `decision_time`.

No value may be fetched from a provider, database, environment secret, wallet,
clock, queue, or UI by this composition. The existing contracts remain
responsible for canonical identity, digest, time, freshness, and scope checks.

## 4. Ordered composition

The implementation must:

1. require exact supported input types;
2. call P06-T02 exactly once;
3. call Risk/Capital Authority exactly once with that exact decision;
4. stop with `AUTHORIZATION_REJECTED` when authority rejects;
5. convert an approved authority result through its canonical P07 observation
   adapter; and
6. construct P07-T01 exactly once from the original caller inputs.

The composition must not independently test whether an action is BUY, copy the
Risk/Capital policy, or create a legacy P07 admission. P06 and Risk/Capital
remain responsible for those decisions.

## 5. Result boundary

The immutable result has exactly these outcomes:

- `READY_FOR_PAPER_SIMULATION`: P06 intent, approved Risk/Capital result, and a
  validated P07-T01 input exist;
- `AUTHORIZATION_REJECTED`: a valid P06 intent and canonical rejection exist,
  and no P07-T01 input was created; or
- `INVALID_INPUT`: composition could not validate or link the supplied inputs,
  and no P07-T01 input was created.

Every result preserves the produced P06 intent when available, the canonical
Risk/Capital result when available, explicit reason codes, and a deterministic
result digest. `READY_FOR_PAPER_SIMULATION` means only that P07-T01 admission is
ready; it does not mean a fill occurred, a position exists, profit was made, or
execution was authorized.

## 6. Failure and side-effect boundary

All contract, identity, digest, scope, time, freshness, and policy-link failures
fail closed as `INVALID_INPUT`. Risk/Capital rejection is preserved separately
as `AUTHORIZATION_REJECTED`.

One invocation has no loop, sleep, retry, network call, secret lookup,
persistence, cache, database write, scheduler, worker, API route, WebSocket,
dashboard publication, wallet, signing, broadcast, or live execution.

## 7. Authorized implementation files

The limited implementation may add or update only:

- `core/runtime/__init__.py`;
- `core/runtime/controlled_paper_run_admission.py`;
- `tests/test_controlled_paper_run_admission.py`;
- this specification and minimal current-state documentation.

No dependency, migration, configuration value, endpoint, worker, frontend, or
provider adapter is authorized.

## 8. Verification gate

Offline tests must prove:

1. a qualifying context and matching approved policy produce one canonical
   P07-T01 input;
2. P06 WATCH/NO_TRADE or any other authority rejection produces no P07 input;
3. altered policy identity, digest, scope, or time fails closed;
4. invalid execution, configuration, initial state, or replay input fails
   closed;
5. the exact P06 and Risk/Capital outputs are preserved;
6. repeat execution over identical explicit facts is deterministic;
7. no legacy authorization path is used; and
8. no fill, position, ledger, reconciliation, P08, provider, persistence,
   wallet, execution, G2, G3, G4, or P09 behavior is reachable.

Focused tests, relevant P05/P06/Risk/P07 regressions, module compilation,
`git diff --check`, and the standard GitHub CI gates must pass.

## 9. Exit and following gate

The authorized composition and focused tests are implemented. Eight focused
tests, 87 relevant P05/P06/Risk/P07 tests, and the full 1,377-test Python 3.13
suite pass locally. Module compilation and `git diff --check` pass. GitHub CI
verification passed in GitHub Actions run #24. Workspace TypeScript typechecks
and builds also pass locally and in CI with the known non-blocking frontend
sourcemap warning.

Completion of P01-RTI-01 authorizes neither a complete paper cycle nor an API
runtime. A later P01-RTI-02 specification may compose an explicitly supplied
P07 fill through paper state, ledger, reconciliation, result, history, and
non-economic P08 observation. It must remain offline/paper-only until separately
reviewed. Automatic token/pool selection, live polling, persistence, dashboard
publication, wallet access, live execution, G2, G3, G4, and P09 remain separate
future gates.
