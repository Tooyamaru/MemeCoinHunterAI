# P02-T02 — Provider-Neutral Ingestion Orchestration and Source Health Boundary

## 1. Task Identity

- **Project:** Meme Coin Hunter AI
- **Phase:** P02 — Solana / DEX Data Intelligence
- **Task:** P02-T02 — Provider-Neutral Ingestion Orchestration and Source Health Boundary
- **Predecessor:** P02-T01 — Data Ingestion and Normalization Contract
- **Task type:** Provider-neutral ingestion orchestration and lifecycle boundary
- **Contract role:** Defines how future adapters, validation/normalization, source
  health, recovery, and downstream publication are coordinated without selecting
  or connecting to a provider.

## 2. Current Status

**STATUS: SPECIFICATION DRAFT — NOT IMPLEMENTED**

**IMPLEMENTATION AUTHORIZED: NO**

This document proposes the next P02 task after the completed P02-T01 contract.
It defines an implementation boundary only. It does not authorize runtime code,
provider connectivity, persistence changes, or any later P02, safety, signal,
decision, risk, or execution work.

## 3. Objective

Define a deterministic, provider-neutral ingestion orchestration boundary that
can accept adapter-produced raw events, apply the P02-T01 validation and
normalization contract, publish accepted normalized observations, and expose
source lifecycle and recovery state to downstream health consumers.

The task should make the data path explicit without deciding which external
provider, transport, chain endpoint, DEX, storage system, or retry service will
be used.

## 4. Why This Is the Next P02 Predecessor

P02-T01 establishes the canonical event and normalized-state semantics, but it
does not define the application boundary that coordinates a stream or batch of
adapter observations. Before a provider can be selected or a token/market
collector can be built, the project needs a stable orchestration contract for:

- adapter input and lifecycle results;
- validation and normalization invocation;
- accepted versus rejected observation handling;
- duplicate, out-of-order, contradictory, stale, and unavailable outcomes;
- source failure and recovery transitions;
- deterministic replay and resynchronization expectations; and
- publication of observable ingestion results.

This task is therefore a predecessor to later provider-specific adapter,
universe/discovery, pool, swap, and market-state collection tasks, while
remaining independent of all of them.

## 5. Architectural Context

The approved dependency direction is:

```text
Future provider adapter
          ↓
Provider-neutral ingestion orchestration
          ↓
P02-T01 raw-event validation and normalization
          ↓
Normalized observation / source health publication
          ↓
Future market, safety, signal, opportunity, decision, and risk consumers
```

The orchestration boundary must preserve the existing P01 Python/FastAPI and
worker boundaries, but it must not require a worker, network client, database,
queue, or external service to define or test the contract.

The orchestration layer coordinates data. It does not interpret market meaning,
calculate strategy, authorize trades, or bypass the Risk Governor.

## 6. Problem Statement

P02-T01 makes individual raw events and normalized states deterministic. Without
an explicit orchestration boundary, future implementations could nevertheless
leak provider behavior into domain code, publish invalid data as current state,
lose source failures between retries, treat process restarts as recovery, or
make replay results depend on wall-clock time and hidden mutable state.

The project needs a small contract that makes these transitions auditable:

```text
adapter observation
→ ingestion result
→ P02-T01 normalization
→ accepted/rejected outcome
→ source health transition
→ published observation
```

## 7. Scope

The approved implementation, if later authorized, may include only:

1. A provider-neutral ingestion orchestration interface.
2. An adapter observation/result envelope that can represent:
   - a raw event;
   - an explicit source failure;
   - an explicit source recovery observation; and
   - a source lifecycle or cursor observation where the source provides one.
3. Deterministic coordination with the existing P02-T01 contracts.
4. Explicit accepted, rejected, duplicate, out-of-order, contradictory, stale,
   incomplete, invalid, and source-unavailable outcomes.
5. Source health transitions based on observed outcomes, not process startup.
6. Recovery rules requiring an accepted observation, consistent with P02-T01.
7. Deterministic batch and replay behavior with explicit processing/reference
   times and explicit initial state.
8. Publication contracts for normalized observations and health changes.
9. Resynchronization and cursor/checkpoint semantics as provider-neutral
   contracts only, where needed to avoid silently skipping or reordering input.
10. Deterministic local fixtures and tests using fake adapter observations.
11. Documentation of the boundary and its observability fields.

Any implementation must use the existing P02-T01 canonical types and must not
create a competing raw-event or normalized-state model.

## 8. Functional Requirements

The future implementation must:

1. Accept only provider-neutral adapter outputs at the orchestration boundary.
2. Preserve source identity, source event identity, timestamps, sequence/cursor,
   and bounded source metadata.
3. Route raw events through the P02-T01 validation and normalization behavior.
4. Require explicit processing and reference times for deterministic evaluation.
5. Return a structured result for every input observation.
6. Distinguish accepted normalized state from rejected or non-usable outcomes.
7. Never publish invalid, incomplete, contradictory, or source-unavailable data
   as fresh valid state.
8. Preserve duplicate and out-of-order outcomes rather than silently dropping
   their observability.
9. Surface source failure as a health event and not as a synthetic valid event.
10. Require an accepted observation before transitioning a failed source to
    available/recovered.
11. Preserve the last known health state across observations within one explicit
    orchestration context.
12. Make initialization, shutdown, and restart semantics explicit without
    treating restart alone as recovery.
13. Support deterministic replay of an equivalent observation sequence with an
    equivalent initial context.
14. Make resynchronization or cursor invalidation explicit when ordering
    continuity cannot be trusted.
15. Keep downstream publication read-oriented and side-effect-free in the
    deterministic contract implementation.
16. Fail closed when required orchestration context is missing or ambiguous.

## 9. Data and Interface Requirements

The future boundary should define provider-neutral equivalents of the following
concepts, using existing project naming conventions where applicable:

### 9.1 Adapter observation

An adapter observation must identify:

- `source_id`;
- observation kind;
- a raw event when one is available;
- an explicit failure/recovery payload when applicable;
- observation time;
- source sequence/cursor when available;
- bounded source metadata; and
- an optional deterministic correlation or batch identity.

Provider SDK objects, HTTP response types, WebSocket message types, RPC types,
and vendor-specific errors must remain outside this boundary.

### 9.2 Ingestion context

The context must make explicit:

- duplicate and ordering state from P02-T01;
- source health state;
- initial cursor/checkpoint or resynchronization state when applicable;
- freshness policy;
- processing time;
- reference time; and
- contract/configuration version needed for reproducibility.

No context may obtain time implicitly from the wall clock during deterministic
processing.

### 9.3 Ingestion result

Every observation must produce an observable result that can distinguish:

- normalized usable state;
- normalized but non-usable quality state;
- source failure;
- source recovery;
- rejected adapter observation;
- ordering discontinuity;
- resynchronization required; and
- unsupported or malformed observation.

The result must retain the relevant source and event identities and a
machine-readable reason category. It must not include strategy, signal,
opportunity, decision, risk, execution, wallet, or trading fields.

### 9.4 Publication boundary

Publication must be represented as an explicit provider-neutral output boundary.
The contract must not require a particular message broker, database, HTTP API,
filesystem, or worker framework. A future implementation may provide an
in-memory deterministic publisher or equivalent test double only if separately
approved as part of the implementation task.

## 10. Testing Requirements

The future implementation must use deterministic local fixtures and must not
make live network calls. Tests must cover at least:

1. One valid adapter observation produces one normalized result.
2. Malformed adapter input is rejected explicitly.
3. P02-T01 quality outcomes remain distinguishable at orchestration output.
4. Duplicate input remains observable and is not republished as new valid state.
5. Out-of-order input remains observable and does not advance accepted ordering.
6. Contradictory identity input is not silently accepted.
7. Source failure produces an unavailable health outcome.
8. A failed source does not recover on restart or on a rejected observation.
9. A failed source recovers only after an accepted observation.
10. Unrelated source failure does not poison another source.
11. Missing sequence/cursor information does not create false ordering certainty.
12. Ordering discontinuity or invalid cursor state requires explicit
    resynchronization handling.
13. Equivalent observation sequences with equivalent contexts replay identically.
14. Explicit processing/reference times produce deterministic freshness results.
15. Publication output preserves provenance and quality metadata.
16. Provider-specific objects cannot cross the canonical orchestration boundary.
17. Existing P01 and P02-T01 tests remain passing.

## 11. Safety Requirements

The future implementation must preserve:

- provider-neutral canonical contracts;
- fail-closed handling of unknown, invalid, stale, incomplete, contradictory,
  and unavailable observations;
- no wallet access, private-key handling, signing, broadcasting, or trading;
- no autonomous behavior;
- no external side effects in deterministic contract tests;
- no credentials or secrets in source code or fixtures;
- no assumption that process health implies source health;
- no silent data loss during duplicate, ordering, or recovery transitions;
- explicit lifecycle behavior; and
- the authority of the Risk Governor over any future decision or execution path.

No result from this task may be interpreted as a signal, opportunity, trade
intent, authorization, or permission to execute.

## 12. Observability Requirements

The future boundary must make observable:

- source identity and observation kind;
- event identity and batch/correlation identity where applicable;
- event, observation, processing, and reference timestamps;
- data age and freshness outcome;
- quality status and reason categories;
- duplicate and ordering result;
- source health state;
- failure and recovery observation times;
- resynchronization or cursor continuity state;
- accepted versus rejected publication outcome; and
- contract/configuration version needed for replay.

Observability output must not expose credentials, private keys, raw secret
values, or unbounded provider payloads. Logging must remain compatible with the
existing standard-library logging boundary.

## 13. Acceptance Criteria

The future implementation may be accepted only if:

1. A provider-neutral orchestration boundary is defined and implemented.
2. The boundary consumes or emits no provider SDK types.
3. P02-T01 remains the sole canonical raw-event and normalized-state contract.
4. Every observation has an explicit, inspectable result.
5. Usable normalized state is distinguishable from every non-usable quality
   outcome required by P02-T01.
6. Failure, recovery, and current source health are explicit.
7. Recovery cannot be inferred from process restart or a rejected observation.
8. Duplicate, ordering, contradiction, and missing-ordering semantics remain
   observable.
9. Replay with equivalent input and context is deterministic.
10. Resynchronization requirements are explicit when continuity is uncertain.
11. No live network, provider, database, migration, or external side effect is
    required by the deterministic implementation and tests.
12. Existing P01 and P02-T01 behavior remains intact.
13. Tests cover the listed failure, recovery, ordering, and replay cases.
14. Observability preserves provenance without exposing secrets.
15. No strategy, signal, opportunity, decision, risk, wallet, trading, or
    execution capability is introduced.
16. Documentation and project state identify the implementation boundary and
    its approval status accurately.

## 14. Explicitly Out of Scope

This task must not include:

- Solana RPC, WebSocket, REST, or DEX provider integration;
- selecting or authorizing a provider or vendor;
- token universe or token discovery;
- emerging-token detection;
- pool, liquidity, swap, transaction-flow, price, or volume collection;
- provider-specific retry, reconnect, rate-limit, or failover implementation;
- database schema, migration, persistence, retention, or query API;
- queue, broker, Redis, or microservice infrastructure;
- dashboard or production deployment work;
- safety/eligibility or hard-risk rules;
- signals, features, opportunity scoring, or phase analysis;
- decision engine or AI/ML/LLM functionality;
- paper trading, execution, wallets, signing, or broadcasting;
- autonomous behavior or multi-agent architecture;
- strategy generation or profitability claims;
- changes to P01 architecture or completed P02-T01 behavior;
- arbitrary production freshness thresholds;
- credentials, secrets, or external service setup.

Provider-specific adapters and actual ingestion transports require separate
specifications and approvals after this boundary is reviewed.

## 15. Dependencies

### Required predecessors

- P00 governance and architecture foundation;
- P01-T01 through P01-T05 application foundation;
- P02-T01 canonical data ingestion and normalization contract;
- existing P02-T01 deterministic tests remain passing.

### Future dependents

This boundary is intended to precede separately specified work for:

- provider-neutral source adapter implementations;
- token universe/discovery ingestion;
- DEX pool and liquidity ingestion;
- swap and transaction-flow ingestion; and
- normalized market-state collection.

Those tasks are not authorized by this draft.

### Approval dependencies

Implementation requires:

- explicit review and approval of this specification;
- a concrete implementation task opened in project governance;
- separate approval for any provider, network, persistence, credentials, or
  operational retry/reconnect behavior; and
- confirmation that the implementation does not expand into later P02 phases.

## 16. Implementation Constraints

If approved, implementation must:

1. Make the smallest change consistent with this specification.
2. Preserve P01 boundaries and P02-T01 canonical types.
3. Prefer existing dependencies and standard-library primitives.
4. Keep orchestration deterministic under explicit context and time inputs.
5. Keep provider-specific parsing and errors at the adapter boundary.
6. Represent rejected and non-usable observations explicitly.
7. Avoid silent drops, implicit recovery, and hidden ordering assumptions.
8. Avoid speculative market or strategy fields.
9. Avoid introducing a queue, database, network client, or provider by default.
10. Add no dependency without separate justification and approval.
11. Add no live external I/O without a separate approved task.
12. Run targeted tests, the full regression suite, and `git diff --check`.
13. Update project state only after implementation and verification are complete.

## 17. Governance / Approval Gate

**STATUS: SPECIFICATION DRAFT — NOT IMPLEMENTED**

**IMPLEMENTATION AUTHORIZED: NO**

This draft proposes P02-T02 as the next architectural candidate. The existence
of this document does not authorize implementation. No provider, adapter,
ingestion worker, migration, external integration, or later P02 capability may
be added until this specification is reviewed, explicitly approved, and opened
as a concrete implementation task.

## 18. Expected Deliverables

After explicit approval, the implementation task may deliver only:

- provider-neutral ingestion observation and result contracts;
- deterministic orchestration over the P02-T01 contracts;
- explicit source lifecycle, failure, recovery, and resynchronization behavior;
- provider-neutral publication interfaces;
- deterministic local fixtures and tests;
- observability documentation for ingestion outcomes; and
- project-state updates reflecting only verified work.

This draft itself produces no runtime, provider, network, database, migration,
trading, or execution capability.