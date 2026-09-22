# P01-RTI-02 — Controlled Paper Lifecycle Composition

**Status:** COMPLETE / CLOSED / CI PASS

**Phase:** P01 runtime integration over existing P07 and P08 owners

**Scope:** one explicit, deterministic, paper-only lifecycle from an approved P07-T01 input through one P08-T01 observation

**Authorized:** 2026-09-22

## 1. Purpose and authorization

The owner authorized continued construction on 2026-09-22 after P01-RTI-01
merged through PR #7. P01-RTI-02 is the next bounded step toward an operational
paper-first system. It composes existing P07-T02 through P07-T07 and P08-T01
owners without moving their rules or authority into the runtime layer.

One invocation begins with a completed P01-RTI-01 result whose outcome is
`READY_FOR_PAPER_SIMULATION`. It may produce:

1. one P07-T02 hypothetical fill;
2. one P07-T03 paper position/exposure transition;
3. one P07-T04 logical ledger entry;
4. one P07-T05 reconciliation against an independently supplied expectation;
5. one P07-T06 non-economic simulation result;
6. one P07-T07 local history insertion; and
7. one P08-T01 immutable outcome-learning observation.

This task does not evaluate profit, classify WIN/LOSS, modify a strategy, or
create settlement/accounting authority.

## 2. Existing owners remain authoritative

- P01-RTI-01 owns controlled P05 → P06 → Risk/Capital → P07-T01 admission.
- P07-T02 owns fill status, quantity conservation, friction, and fill identity.
- P07-T03 owns position, exposure, valuation, and accounting state transition.
- P07-T04 owns logical ledger identity and linkage.
- P07-T05 owns reconciliation against a caller-supplied expectation.
- P07-T06 owns the finalized non-economic paper result.
- P07-T07 owns deterministic local result history.
- P08-T01 owns read-only decision-to-paper-result observation.

The runtime composition must call these owners in order. It must not duplicate
their rules, manufacture a favorable fill, infer missing valuation/accounting
facts, or reinterpret a reconciliation discrepancy as a match.

## 3. Explicit inputs

The composition receives exactly one completed P01-RTI-01 admission plus two
immutable runtime input records.

### 3.1 Fill instruction

The fill instruction supplies:

- side;
- requested quantity and units;
- executable liquidity;
- reference quote price;
- quote observation and fill times;
- explicit `FrictionComponents`;
- optional available inventory for SELL; and
- explicit quote currency.

The authoritative asset identity remains the P07-T01 execution observation.
The runtime must not override it.

### 3.2 Lifecycle evidence

The lifecycle evidence supplies:

- one prior `PaperPositionExposureState`;
- exact target asset identity;
- one `ValuationContext`;
- one `AccountingContext`;
- one explicit transition/ledger reference time;
- ledger stream identity, sequence number, and predecessor digest; and
- one independent `PaperReconciliationExpectation`.

The expectation must be caller-supplied. The runtime must not derive an
expectation from the ledger entry it is about to verify, because that would make
reconciliation tautological.

No input may be fetched from a provider, database, wall clock, queue, wallet,
environment secret, or UI.

## 4. Ordered composition

The implementation must:

1. require a canonical `READY_FOR_PAPER_SIMULATION` P01-RTI-01 result;
2. call P07-T02 exactly once with the admitted P07-T01 input;
3. call P07-T03 exactly once with the produced fill and supplied state facts;
4. create one P07-T04 ledger entry;
5. call P07-T05 exactly once with that entry and the independent expectation;
6. stop before P07-T06 when reconciliation is not `MATCH`;
7. create P07-T06 through `PaperSimulationResult.from_predecessors` only;
8. insert the result into a new local P07-T07 history exactly once; and
9. create one P08-T01 observation from the exact P06/P07 chain.

Failed, rejected, unavailable, or invalid fill outcomes may still become
non-economic paper observations when their P07-T03/T04/T05 chain is canonical
and reconciliation is `MATCH`. They must never be rewritten as successful
fills.

## 5. Corrective compatibility fix

P07-T02 uses `PARTIALLY_FILLED`, while the closed P07-T06 result vocabulary uses
`PARTIAL`. The current `from_predecessors` implementation copies the T02 value
verbatim and therefore rejects an otherwise canonical partial-fill chain.

P01-RTI-02 authorizes one narrow corrective mapping:

`PARTIALLY_FILLED` → `PARTIAL`

The original P07-T02 fill status remains unchanged in the fill artifact and
ledger. No other status, contract field, or authority is changed.

## 6. Result boundary

The immutable runtime result has exactly these outcomes:

- `OBSERVATION_PRODUCED`: the complete P07-T02–T07 and P08-T01 chain exists;
- `ADMISSION_NOT_READY`: P01-RTI-01 did not provide an approved P07-T01 input;
- `RECONCILIATION_NOT_MATCHED`: P07-T05 returned a canonical status other than
  `MATCH`, so no P07-T06/T07 or P08-T01 artifact was created; or
- `INVALID_INPUT`: a contract, type, identity, digest, time, state, history, or
  linkage check failed closed.

The result preserves every successfully produced predecessor artifact and a
deterministic digest. `OBSERVATION_PRODUCED` is non-economic: it does not mean a
profit, a realized outcome, a WIN, settlement, or authorization to trade.

## 7. Side-effect and safety boundary

One invocation has no network request, loop, retry, polling, sleep, persistence,
database write, API route, worker, scheduler, WebSocket, dashboard publication,
wallet, signing, broadcast, transaction, G2, G3, G4, or P09 behavior.

The Risk Governor remains above the Decision Engine. Only the exact approved
P07-T01 input from P01-RTI-01 may enter this lifecycle.

## 8. Authorized implementation files

The limited implementation may add or update only:

- `core/runtime/controlled_paper_lifecycle.py`;
- `core/runtime/__init__.py`;
- `core/execution/paper_simulation_result.py` for the exact partial-status map;
- `tests/test_controlled_paper_lifecycle.py`;
- `tests/test_paper_simulation_result.py` for the corrective regression; and
- this specification plus minimal project-state/changelog updates.

No dependency, migration, configuration, API, worker, frontend, provider, or
persistence file is authorized.

## 9. Verification gate

Offline tests must prove:

1. one canonical full-fill lifecycle reaches P08-T01;
2. one canonical partial fill is preserved as P07-T02 `PARTIALLY_FILLED` and
   represented as P07-T06 `PARTIAL`;
3. failed or unavailable fills are never rewritten as success;
4. an admission rejection creates no fill or later artifact;
5. a non-matching reconciliation creates no P07-T06/T07 or P08-T01 artifact;
6. altered state, identity, digest, expectation, time, or history facts fail
   closed;
7. exact predecessor digests survive across P07-T02 through P08-T01;
8. replay with identical explicit facts is deterministic; and
9. no external I/O, persistence, wallet, execution, G2, G3, G4, or P09 behavior
   is reachable.

Focused RTI-02 and P07-T06 tests, relevant P07/P08 regressions, full Python
tests, module compilation, workspace TypeScript checks/builds, and
`git diff --check` must pass before merge.

## 10. Exit and following gate

Completion of P01-RTI-02 authorizes neither persistence nor an API runtime. The
next proposed gate is P01-RTI-03 controlled persistence for run, decision,
paper state, ledger, reconciliation, result, history, and observation records.
It requires a separate specification and review. Scheduler, dashboard runtime,
automatic pool selection, wallet access, live execution, G2, G3, G4, and P09
remain future gates.
