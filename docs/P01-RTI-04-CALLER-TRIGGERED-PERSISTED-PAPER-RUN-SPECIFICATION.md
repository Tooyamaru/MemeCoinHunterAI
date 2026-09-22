# P01-RTI-04 — Caller-Triggered Persisted Paper Run

**Status:** IMPLEMENTED / LOCAL VERIFICATION PASS / CI PENDING

**Phase:** P01 runtime integration over completed P01-RTI-01, P01-RTI-02, and
P01-RTI-03 boundaries

**Scope:** coordinate exactly one explicitly supplied paper run through
admission, lifecycle, and persistence from an HTTP-independent application
service

**Proposed:** 2026-09-22

## 1. Purpose

P01-RTI-01 produces one canonical paper-run admission, P01-RTI-02 advances that
admission through one paper lifecycle, and P01-RTI-03 atomically retains the
canonical lifecycle result. P01-RTI-04 proposes the first application-service
boundary that invokes those three completed owners in order for one explicit
caller request.

The service is a coordinator, not a new domain owner. It must not copy,
reinterpret, repair, or replace decision, Risk/Capital, simulation,
reconciliation, observation, or persistence rules.

The owner explicitly authorized the limited implementation on 2026-09-22.

## 2. Existing owners remain authoritative

- P06-T02 owns deterministic decision evaluation.
- Risk/Capital Authority owns paper capital authorization and rejection.
- P01-RTI-01 owns P05-T08 through P07-T01 admission composition.
- P01-RTI-02 owns P07-T02 through P08-T01 lifecycle composition.
- P01-RTI-03 owns canonical append-only lifecycle persistence and readback.
- P01-T03 owns database runtime, sessions, and transaction handling.
- P01-T04 owns HTTP-independent application-service layering and request
  correlation context.
- P01-RTI-04 owns only ordered one-request coordination and its outer result.

Nested owner outcomes and reason codes are preserved. The coordinator must not
translate an admission rejection into an invalid input, treat a non-matching
reconciliation as a successful observation, or treat persistence as proof of
economic or on-chain activity.

## 3. Accepted request

One immutable request contains exactly the explicit inputs already required by
the completed owners:

- one validated P05-T08 `OpportunityContext`;
- one P06 `DecisionEvaluationRuleset`;
- one `PaperRiskCapitalPolicySnapshot`;
- one P07 `ExecutionObservation`;
- one `SimulationConfigurationIdentity`;
- one `InitialPaperStateIdentity`;
- one `ReplayIdentity`;
- an optional explicit decision time;
- one P01-RTI-02 `PaperFillInstruction`; and
- one P01-RTI-02 `PaperLifecycleEvidence`.

The request also carries a caller-supplied `invocation_id`: 1 through 128 ASCII
letters, digits, `.`, `_`, `:`, or `-`, without surrounding whitespace. An
optional `ServiceRequestContext` provides operational correlation. The request
ID is not copied into `invocation_id`. Correlation metadata is operational only
and must not enter the invocation result digest or any P06, Risk/Capital, P07,
P08, or persistence-owner digest.

P01-RTI-04 does not fetch or manufacture any input. In particular, it cannot
select a token or pool, obtain a quote, construct reconciliation expectations
from its own ledger, read provider secrets, or use wall-clock time when an
owner requires an explicit time.

## 4. Ordered composition

One invocation performs these bounded steps:

1. validate the exact request type, supported contract version, canonical
   invocation identity, and closed input shape;
2. call `prepare_controlled_paper_run(...)` exactly once;
3. pass the exact admission result to
   `run_controlled_paper_lifecycle(...)` exactly once;
4. pass the exact lifecycle result to
   `ControlledPaperPersistenceService.persist(...)` exactly once; and
5. return one immutable outer orchestration result preserving all nested
   results and their digests.

The coordinator may stop before a later step only when it cannot construct a
canonical owner input or when an unexpected boundary failure prevents a
canonical nested result. Canonical admission rejection and canonical
reconciliation mismatch are data outcomes, not exceptions: they continue
through P01-RTI-02 and P01-RTI-03 so the append-only audit record is retained.

No step may be retried automatically. An explicit caller retry replays the same
immutable request and relies on P01-RTI-03 idempotency.

## 5. Outer result contract

The immutable P01-RTI-04 result contains:

- the P01-RTI-04 contract version;
- canonical invocation identity;
- one closed outer outcome;
- canonical reason codes;
- optional exact P01-RTI-01 admission result;
- optional exact P01-RTI-02 lifecycle result;
- optional exact P01-RTI-03 persistence result;
- the available nested result digests; and
- one deterministic outer result digest.

It has exactly these outcomes:

- `PERSISTED`: P01-RTI-03 returned `STORED`;
- `ALREADY_PERSISTED`: P01-RTI-03 returned `ALREADY_STORED` for an exact retry;
- `PERSISTENCE_CONFLICT`: P01-RTI-03 returned `CONFLICT`;
- `STORAGE_UNAVAILABLE`: P01-RTI-03 returned `STORAGE_UNAVAILABLE`; and
- `INVALID_INPUT`: the coordinator could not validate the outer request or a
  returned nested result, or P01-RTI-03 rejected the lifecycle as invalid.

`PERSISTED` and `ALREADY_PERSISTED` describe storage only. The nested lifecycle
may still canonically record `ADMISSION_NOT_READY` or
`RECONCILIATION_NOT_MATCHED`; neither outer outcome means a fill succeeded,
profit occurred, or a trade was executed.

A canonical P01-RTI-01 `INVALID_INPUT` owner result is not rewritten as an
outer orchestration failure. P01-RTI-02 represents it as
`ADMISSION_NOT_READY`, and P01-RTI-03 may persist that exact audit chain. The
outer result then describes only whether that canonical chain was stored.

## 6. Validation and linkage

Before returning, the service must verify that:

- every supplied object has its exact supported owner type and version;
- each completed owner result is canonical and its digest is valid;
- the lifecycle retains the exact admission digest produced in this invocation;
- the persistence result refers to the exact lifecycle digest produced in this
  invocation whenever that digest is available;
- result presence matches the reached stage; and
- reason codes and nested outcomes are not silently rewritten.

Invalid or tampered inputs fail closed. The service must not expose exception
messages, SQL, database URLs, secrets, payload contents, or mutable objects in
its outer result.

## 7. Side effects and failure behavior

The only authorized side effect is the existing P01-RTI-03 atomic database
write. Decision, admission, and lifecycle work remains in-memory and
deterministic.

- Owner validation failures return bounded canonical outcomes.
- Unexpected orchestration type/linkage failures return `INVALID_INPUT` without
  a fabricated later-stage result.
- Database failures return `STORAGE_UNAVAILABLE` through P01-RTI-03.
- Persistence conflict returns `PERSISTENCE_CONFLICT` and changes no stored
  record.
- Cancellation or failure before persistence creates no database record.
- There is no automatic retry, compensation workflow, queue, outbox, or
  background recovery process.

## 8. Request correlation and observability

The service may use the existing `ServiceRequestContext` and structured logger
to record stage names and bounded outcomes. Logs may contain the request ID,
contract versions, invocation identity, owner result digests, and outcome
names. They must not contain full canonical payloads, credentials, secrets,
database URLs, wallet material, or raw exception text.

Logging is not part of deterministic result construction. A logging failure
must not alter an owner result or authorize a retry.

## 9. Explicit exclusions

P01-RTI-04 adds no:

- FastAPI route, WebSocket, or external application protocol;
- scheduler, worker registration, loop, polling, sleep, queue, or retry;
- automatic token, candidate, pool, ruleset, policy, quote, or fill selection;
- provider, RPC, DEX, chain, or secret access;
- dashboard or Hunter Room publication;
- wallet, signing, broadcast, live order, or settlement behavior;
- economic WIN/LOSS, ROI, expectancy, or profit interpretation;
- strategy/model update, multi-agent runtime, or P09 behavior; or
- G2, G3, or G4 implementation.

## 10. Authorized implementation surface

Implementation is limited to:

- `backend/application/controlled_paper_run_service.py` for the immutable
  request/result and coordinator;
- `backend/application/__init__.py` for minimal exports;
- `tests/test_controlled_paper_run_service.py` for focused offline tests; and
- minimal updates to this specification, `PROJECT_STATE.md`, and
  `docs/CHANGELOG.md`.

No dependency, model, repository, migration, API, worker, frontend, provider,
configuration, wallet, execution, or learning-owner file is included.

## 11. Verification gate

Offline tests must prove:

1. one approved complete request invokes admission, lifecycle, and persistence
   once and returns `PERSISTED`;
2. the exact same request returns `ALREADY_PERSISTED` without duplicate rows;
3. Risk/Capital rejection is preserved as a nested admission-not-ready
   lifecycle and is persisted without producing a fill;
4. reconciliation mismatch is preserved and persisted without producing a
   P07-T06 result, history result, or P08-T01 observation;
5. an unsupported outer request shape and any tampered returned owner result,
   digest, identity, time, or linkage fail closed, while a canonical owner-level
   invalid admission is preserved and persisted as admission-not-ready;
6. storage unavailability and same-digest conflict remain distinct;
7. no owner function is invoked more than once per request;
8. request correlation metadata does not enter domain or persistence digests;
9. replay of identical explicit facts is deterministic; and
10. no network, provider, API, worker, scheduler, dashboard, wallet, execution,
    G2, G3, G4, or P09 behavior is reachable.

Focused RTI-04 tests, relevant P01-RTI-01 through RTI-03 regressions, the full
Python suite, module compilation, TypeScript checks/builds, `git diff --check`,
and standard GitHub CI must pass before implementation merge.

## 12. Exit and following gate

P01-RTI-04 now provides one locally verified, manually invoked, persisted paper
application-service call. It does not make the system continuously operational
and does not create a public API or dashboard feed.

The authorized service, immutable request/result contracts, exports, and ten
focused tests are implemented. The focused suite passes 10 tests, the combined
P01-RTI-01 through P01-RTI-04 regression suite passes 38 tests, and the full
Python 3.13 suite passes 1,409 tests with one pre-existing Starlette warning.
Module compilation, whitespace checks, TypeScript typechecks, and all workspace
builds pass; the known frontend `tooltip.tsx` sourcemap warning remains
non-blocking. GitHub CI and merge are pending.

Any later API/manual trigger, read-only result query, dashboard/Hunter Room
publication, upstream market-to-opportunity runtime composition, scheduler, or
continuous paper loop requires its own specification and explicit approval.
Wallet access, live execution, G2, G3, G4, and P09 remain future gates.
