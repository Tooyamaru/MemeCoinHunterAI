# P01-RTI-10 — Cross-Surface Governance and Upstream Readiness Reconciliation

**Status:** COMPLETE / CLOSED / CI PASS

**Gate type:** documentation and governance only

**Baseline:** `1d10df723757a46684a1ccc229606daf7fafe27c`

**Reconciled on:** 2026-09-23

## 1. Purpose and non-authority

P01-RTI-10 reconciles the current authority and readiness state between the
closed lifecycle integration surface and the bounded upstream market-evidence
surface. It resolves stale wording without changing any runtime contract.

This gate creates no production code, test behavior, dependency, model,
migration, API, provider call, application wiring, persistence behavior,
worker, scheduler, queue, dashboard, wallet, execution, live trading, G2, G3,
G4, or P09 implementation. It does not authorize the next gate.

## 2. Evidence reviewed

The controlling evidence is:

- `PROJECT_STATE.md` and `REPLIT_RULES.md`;
- `docs/HYBRID_DEVELOPMENT_WORKFLOW.md`;
- `docs/ARCHITECTURE.md`, `docs/DATA_PIPELINE.md`, and the bounded P04 status
  in `docs/MASTER_BLUEPRINT.md`;
- P04-LME-01, P04-LME-02, and P04-LME-03 specifications;
- the canonical P04-to-P05 evidence producer and P05-T08 specification only to
  establish existing ownership and handoff readiness; and
- RTI-01 through RTI-09 state/specifications only to establish dependency,
  persistence, lifecycle, and read-surface ownership.

Older selection records remain valid historical evidence of what was unknown
at their dates. They are not current blockers where a later accepted decision
within the same authority has superseded them.

## 3. Reconciled current decisions

### 3.1 Market-evidence source

**CURRENT:** CoinGecko Demo Onchain pool OHLCV is the approved bounded V1
source for exact-pool, exact-token, closed one-minute analytical price
evidence. Its authority is limited to observations returned under the locked
P04-LME-01 request, identity, temporal, content, and provenance rules.

This is not provider-runtime approval, a permanent provider-correctness claim,
automatic source fallback, pool selection, settlement evidence, or realized
economic truth.

### 3.2 Market-to-signal policy

**CURRENT:** `price-direction-v1` is the approved deterministic observational
market-to-signal policy. It produces `PRICE_DIRECTION_1M` with `RISING`,
`FALLING`, or `FLAT` from the latest two validated closed candles. It is not a
prediction, trading recommendation, P06 decision, risk authorization, or
economic classification.

### 3.3 Bounded transport and orchestration

**CURRENT / COMPLETE:**

- P04-LME-01 owns request construction, response mapping, validation, admitted
  observation production, and signal derivation.
- P04-LME-02 owns credential lookup, exactly one bounded server-side HTTP GET,
  request/receipt/evaluation timing, transport-failure mapping, and one-shot
  diagnostic composition.
- P04-LME-03 owns one caller-directed composition from one current admitted
  candidate and one exact caller-supplied pool target into P04-LME-02.

Completion of those boundaries does not authorize application/runtime
composition. P04-LME-03 deliberately stops before automatically entering the
canonical P04/P05 producer, P06, paper lifecycle, persistence, or execution.

### 3.4 Lifecycle read surface

**CURRENT / SUFFICIENTLY COMPLETE:** RTI-05 through RTI-09 provide exact
lifecycle-result lookup, deterministic digest catalog paging, their two
read-only `GET` transports, and combined API/OpenAPI conformance. Repository
evidence does not establish a present need for filtering, search,
latest/history, projections, analytics, conditional caching, retention,
mutation, authentication, or deployment extensions.

## 4. Authority matrix

| Authority | Current owner | State | Owns | Explicitly does not own |
| --- | --- | --- | --- | --- |
| Candidate and admitted market identity | P02-T06/P02-T07 through P02-T09 | CURRENT / CLOSED | Canonical candidate membership, admitted observations, market-intelligence identity and state provenance | Pool selection, signal meaning, decisions, execution |
| Market evidence/source authority | P04-LME-01 | CURRENT / LIMITED IMPLEMENTATION COMPLETE | CoinGecko Demo OHLCV analytical source profile; exact source/request/identity/time/content mapping | Continuous provider runtime, failover, settlement, G2 truth |
| Transport authority | P04-LME-02 | CURRENT / LIMITED IMPLEMENTATION COMPLETE | One server-side bounded GET, credential boundary, receipt timing, transport outcomes | Retry, polling, scheduling, persistence, application publication |
| Caller-directed diagnostic orchestration | P04-LME-03 | CURRENT / LIMITED IMPLEMENTATION COMPLETE | Bind one admitted candidate and exact caller-owned pool target to one diagnostic call | Token/pool discovery or selection, automatic downstream composition |
| Analytical/signal policy authority | P04-LME-01 `price-direction-v1`; existing P04-T01–T10 owners thereafter | CURRENT / CLOSED WITHIN BOUNDED SCOPE | Observational price direction and canonical signal/feature processing | BUY/SELL meaning, P06 intent, capital authority, economic truth |
| Canonical market-to-opportunity composition | Existing canonical evidence producer and P04-to-P05 composition | CURRENT / IMPLEMENTED AS PURE BOUNDARIES | Deterministic composition of already-validated evidence through P04/P05 | Provider collection, caller/runtime ownership, retry, persistence |
| Final opportunity context | P05-T08 | CURRENT / CLOSED | Immutable evidence-first context supplied to P06 | Runtime triggering, provider collection, decision or execution |
| Application composition authority | No approved owner | READY FOR SEPARATE SPECIFICATION / NOT AUTHORIZED | Nothing yet | Invocation policy, caller contract, cross-boundary failure handling, publication/persistence |
| Paper admission and lifecycle | RTI-01 through RTI-04, using their existing P05/P06/Risk/P07 owners | CURRENT / CLOSED | Explicit controlled paper admission, lifecycle, persistence, and caller-triggered run within their contracts | Live trading, economic realization, automatic upstream runtime |
| Paper persistence authority | RTI-03 | CURRENT / CLOSED | Atomic persisted lifecycle bundle, integrity validation, immutable read snapshots and artifact ordering | Market-data persistence, G2 settlement truth |
| Lifecycle application/API read authority | RTI-05 through RTI-09 | CURRENT / CLOSED | Exact lookup, digest catalog, read-only transports, contract conformance | Mutation, execution, filtering/search authority, economics |
| Economic realization/settlement authority | No approved G2 owner/source | BLOCKED / UNRESOLVED / NOT AUTHORIZED | Nothing | P04 analytical data and paper results cannot substitute for G2 evidence |
| Economic aggregation/classification | G3/G4 | NOT AUTHORIZED | Nothing | No P04, P07, RTI, or G1 artifact grants this authority |
| Execution/live-trading authority | P09 and later execution/wallet boundaries | NOT AUTHORIZED | Nothing | No signal, opportunity, decision, risk result, or paper result permits live action |

## 5. Dependency and readiness matrix for upstream application composition

| Dependency/link | Current evidence | Readiness | Residual requirement before composition |
| --- | --- | --- | --- |
| Current candidate identity | P02-T06 and P04-LME-03 admission check | CLOSED | Preserve exact candidate/predecessor identity; do not rediscover |
| Exact pool target | Caller-owned `ExactPoolDiagnosticTarget` in P04-LME-03 | PARTIAL / EXPLICIT INPUT | Specify the authorized application caller and provenance source; no automatic selection |
| Historical source contract | P04-LME-01 CoinGecko Demo OHLCV | CLOSED FOR BOUNDED ANALYTICAL USE | Bind exact contract/version; do not broaden into runtime or G2 authority |
| Transport | P04-LME-02 single bounded GET | CLOSED FOR ONE SHOT | Decide whether a future application boundary may invoke it; retries remain absent unless separately specified |
| Controlled diagnostic | P04-LME-03 | CLOSED FOR ONE SHOT | Define how nested outcomes propagate without reinterpretation |
| Source-to-signal policy | `price-direction-v1` | CLOSED FOR V1 | Bind exact policy version; no ambient/latest policy substitution |
| Observation and cutoff semantics | Closed-minute request cutoff plus explicit request, receipt, observation, and evaluation times | CLOSED AT SOURCE BOUNDARY | Preserve all times and freshness policy across composition |
| Provenance propagation | Source-response digest, admitted P02 identities/digests, signal references, target reference | SUBSTANTIALLY READY | Specify end-to-end preservation and rejection of missing/mismatched lineage |
| Safety eligibility | Existing P03 derived eligibility is required by canonical producer | DEPENDENCY EXISTS; APPLICATION SUPPLY NOT OWNED | Specify which already-authoritative application input supplies it; never accept browser-asserted eligibility |
| Canonical P04/P05 production | Canonical evidence producer and composition exist | CLOSED AS PURE BOUNDARIES | Authorize only delegation; do not create a second evaluator |
| P05-T08 context materialization | Existing P05-T06–T08 chain | CLOSED AS PURE BOUNDARY | Specify whether the prospective gate stops at composition or materializes T08; preserve owner semantics |
| Caller/application owner | None approved for this cross-surface invocation | BLOCKED FOR IMPLEMENTATION | Lock one explicit caller, input contract, invocation cardinality, and returned result |
| Failure/retry semantics | Fail-closed outcome vocabularies exist; LME-02/03 perform no retry | PARTIAL | Define deterministic cross-boundary outcome mapping; keep retry/polling outside the first gate |
| Persistence/publication | No upstream application-composition persistence owner | NOT AUTHORIZED | First gate should remain non-persistent unless a later independent specification proves need |
| Worker/scheduler/continuous runtime | Explicitly absent | NOT AUTHORIZED | Must remain absent |
| G2/economic truth | No authoritative source/owner | BLOCKED | Not a dependency for analytical composition and must never be inferred from it |

## 6. Historical versus current reconciliation

| Prior wording or decision | Classification | Current reconciliation |
| --- | --- | --- |
| Pre-LME selection records said authenticated historical evidence, source-time linkage, and market-to-signal ownership were unresolved. | HISTORICAL / SUPERSEDED for the bounded P04 analytical scope | P04-LME-01 later selected the source, time semantics, provenance, and `price-direction-v1`; P04-LME-02/03 completed one-shot transport/orchestration. The old records remain accurate snapshots of their dates. |
| `PROJECT_STATE.md` said the repository had no approved market-to-signal policy or source-authentication mapping. | SUPERSEDED current-state wording | Replaced with the accepted LME state and residual application-composition blockers. |
| `HYBRID_DEVELOPMENT_WORKFLOW.md` said live application integration awaited approval of a source and deterministic policy. | SUPERSEDED current-boundary wording | Source and policy are now approved for bounded analytical use; application composition still awaits its own caller and orchestration specification. |
| P04-LME-01 notes that its initially authorized implementation did not include HTTP transport. | HISTORICAL / STILL TRUE FOR LME-01 ITSELF | P04-LME-02 later owns transport; ownership is additive, not retroactively moved into LME-01. |
| P04-LME-01 states the live application path remains blocked. | CURRENT | Source/policy completion did not authorize application wiring. |
| P04-LME-02 says retry remains orchestration-owned. | CURRENT AS A FUTURE OWNERSHIP PLACEHOLDER | P04-LME-03 intentionally performs no retry; no current retry owner is authorized. |
| P04-LME-03 caller owns exact pool selection and provenance. | CURRENT | No application owner for that caller decision has yet been approved. |
| G2 realization/settlement provider/source owner is unresolved. | CURRENT / BLOCKED | This is economic authority and is not repaired or weakened by P04 source selection. |
| RTI-05–RTI-09 are closed read-only lifecycle surfaces. | CURRENT | No extension is presently justified by repository evidence. |

## 7. Residual-gap statement

The source, signal policy, one-shot transport, controlled diagnostic, and pure
P04/P05 composition components exist. The remaining blocker is not their
absence; it is the absence of one approved application-level composition
contract joining them.

Before direct upstream application composition can be implemented, a separate
specification must lock:

1. the sole application caller and why it may initiate one composition;
2. the exact immutable inputs, including current candidate, caller-owned pool
   target, P03 eligibility, freshness policy, and all reference times;
3. invocation cardinality and proof that there is no loop, polling, retry,
   scheduler, worker, or queue;
4. exact binding to `price-direction-v1` and the existing LME/P02/P04/P05
   contract versions;
5. nested result and failure propagation without semantic rewriting;
6. candidate, pool-target, source-response, P02 state, signal, feature, safety,
   and opportunity provenance propagation;
7. observation-time, receipt-time, evaluation-time, reference-time, and
   closed-minute cutoff preservation;
8. whether the bounded output stops at canonical P04-to-P05 composition or may
   materialize the existing P05-T08 context;
9. an explicit no-persistence/no-publication default; and
10. isolation from RTI invocation, paper lifecycle mutation, P06 decisions,
    economic interpretation, G2/G3/G4/P09, wallet, and execution.

Provider runtime correctness remains unproven by offline CI. That fact does not
invalidate the approved bounded source contract, but it prohibits claims of
continuous operational readiness.

## 8. Current governance summary

- CoinGecko Demo OHLCV is **CURRENT** as the bounded V1 analytical source.
- `price-direction-v1` is **CURRENT** as the deterministic observational
  market-to-signal policy.
- P04-LME-01 through P04-LME-03 are **COMPLETE** in their limited scopes.
- Direct application/runtime composition is **NOT AUTHORIZED**.
- RTI-05 through RTI-09 require **NO EXTENSION NOW**.
- P04 analytical evidence is not G2 realization/settlement evidence.
- Paper/runtime evidence is not realized economic truth.
- G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.
- G3, G4, and P09 remain **NOT AUTHORIZED**.
- Provider runtime, automatic pool selection, retry loops, workers, schedulers,
  queues, dashboards, wallets, execution, and live trading remain unopened.

## 9. Recommended next gate

### P01-RTI-11 — Bounded Caller-Directed Market-to-Opportunity Application Composition Specification

The next gate should be specification-only. It should define one explicit,
caller-directed, single-invocation application boundary that delegates through
P04-LME-03 and then, only for a successful produced diagnostic, into the
existing canonical P04/P05 owners. It should default to no persistence and
stop no later than an existing P05-T08 `OpportunityContext`.

RTI-11 must not add HTTP, dashboard publication, automatic token/pool
selection, provider polling, retry, worker, scheduler, queue, persistence,
P06 invocation, paper-run invocation, G2/G3/G4/P09, wallet, execution, or live
trading. Controller review and separate authorization are required before the
specification is written or any implementation is considered.

## 10. Validation and closure criteria

P01-RTI-10 is complete when:

1. current governance wording reflects the accepted P04-LME decisions;
2. historical records remain intact and are classified rather than erased;
3. authority, readiness, residual gaps, and forbidden boundaries are explicit;
4. only documentation/governance files changed;
5. `git diff --check` passes; and
6. the documentation PR passes required CI and merges before closure is
   recorded.

All closure criteria are satisfied. GitHub Actions run #75 passed the Python
3.13 regression/whitespace job and the TypeScript typecheck/build job. PR #26
was squash-merged to `main` at `b8e24c8`. No subsequent gate is authorized or
started by this closure.
