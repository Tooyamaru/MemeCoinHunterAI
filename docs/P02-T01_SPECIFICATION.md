# P02-T01 — Data Ingestion and Normalization Contract

## 1. Task Identity

- **Project:** Meme Coin Hunter AI
- **Phase:** P02 — Solana / DEX Data Intelligence
- **Task:** P02-T01 — Data Ingestion and Normalization Contract
- **Predecessor:** P01-T05 — Application Service & Worker Extensions
- **Task type:** Documentation-defined contract and boundary foundation
- **Contract role:** Defines the canonical data model and adapter boundaries for
  future P02 implementation.

## 2. Current Status

**STATUS: IMPLEMENTED — CONTRACT FOUNDATION ONLY**

**IMPLEMENTATION AUTHORIZED: YES**

This document defines the approved implementation contract. The implementation
adds deterministic local contract behavior only; it does not connect to a
provider or authorize later P02 work.

## 3. Objective

Define the canonical data contracts and boundaries required for reliable,
reproducible, provider-neutral market-data ingestion.

The contract covers:

1. Raw event representation.
2. Normalized market-state representation.
3. Source identity.
4. Event, received, and processing timestamps.
5. Freshness and data age.
6. Deterministic data-quality state.
7. Duplicate handling.
8. Sequence and ordering semantics.
9. Source failure and recovery state.
10. A provider-neutral adapter boundary.
11. Deterministic local test fixtures.

P02-T01 is a contract task, not a data-collection task.

## 4. Architectural Context

P02 is the Solana / DEX Data Intelligence phase. Its phase-level objective is
to collect reliable, normalized market data and produce reproducible normalized
market state with freshness and recovery evidence.

P02-T01 must preserve the existing dependency direction:

```text
Provider adapter boundary
          ↓
Raw event contract
          ↓
Validation and normalization boundary
          ↓
Normalized market-state contract
          ↓
Future safety, signal, opportunity, decision, and risk consumers
```

The canonical contracts must remain independent from any specific Solana,
DEX, RPC, WebSocket, REST, or data-vendor implementation.

## 5. Problem Statement

Future data sources may differ in field names, timestamp precision, delivery
mode, identifiers, ordering guarantees, duplicate behavior, and failure
semantics. Without a canonical contract, provider details can leak into domain
logic and make freshness, reproducibility, recovery, and audit behavior
ambiguous.

P02-T01 establishes the smallest shared contract needed to validate and
normalize future data without prematurely implementing a provider, strategy, or
trading system.

## 6. Scope

P02-T01 defines:

- The minimum metadata required for raw events.
- The minimum metadata required for normalized state.
- Canonical identity and source attribution.
- Timestamp and freshness semantics.
- Deterministic quality categories.
- Duplicate, ordering, and contradiction rules.
- Failure and recovery state semantics.
- Provider adapter input/output boundaries.
- Conceptual persistence requirements for a future implementation.
- Deterministic local testing requirements.
- Observability and audit requirements.

P02-T01 does not implement these contracts in application code.

## 7. Functional Requirements

The future implementation must:

1. Accept provider-neutral raw event inputs through an explicit boundary.
2. Preserve source identity and source-specific identifiers where available.
3. Validate required metadata before normalization.
4. Produce deterministic normalized representations from equivalent inputs.
5. Preserve event, received, and processing timestamps.
6. Calculate or expose data age using an explicit reference time.
7. Assign a deterministic quality state.
8. Detect duplicates without silently treating them as new information.
9. Apply explicit sequence and ordering rules where ordering information exists.
10. Represent missing ordering information without inventing ordering certainty.
11. Represent contradictory updates explicitly.
12. Represent source unavailability and recovery explicitly.
13. Avoid provider-specific types in canonical domain contracts.
14. Keep all future downstream consumers able to distinguish usable, stale,
    invalid, incomplete, duplicate, out-of-order, and unavailable data.

## 8. Data Contract Requirements

### 8.1 Raw event contract

Every raw event contract must preserve:

- `source_id`: stable identity of the originating source or adapter.
- `source_event_id`: source-provided event identifier when available.
- `payload`: source payload retained only at the adapter boundary for validation
  and normalization.
- `event_time`: timestamp asserted by the source when available.
- `received_time`: timestamp when the application receives the event.
- `sequence`: source sequence or cursor when available.
- `source_metadata`: bounded metadata needed to interpret the event, without
  embedding provider-specific types into the canonical domain contract.

If a source does not provide an event identifier, the adapter must provide the
metadata needed to derive a deterministic identity from the event content and
source context. The contract must not invent a globally unique identifier from
an unstable value.

### 8.2 Normalized market-state contract

Every normalized state record must preserve:

- `source_id`.
- `source_event_id` when available.
- `event_time`.
- `received_time`.
- `processing_time`.
- A deterministic identity/key.
- `data_age` or equivalent freshness information.
- `quality_status`.
- `sequence` or explicit ordering information when applicable.
- The minimal normalized state payload required by the approved future
  implementation.

The normalized payload must not define strategy, signal, opportunity, decision,
risk, execution, wallet, or trading fields in this task.

### 8.3 Determinism

Equivalent input events with equivalent reference context must produce the same
identity, normalized representation, quality status, and ordering outcome.

Normalization must not depend on process-local randomness, wall-clock time
without an explicit reference, or provider-specific side effects.

## 9. Timestamp and Freshness Requirements

The future implementation must distinguish:

- **Event time:** when the source says the event occurred.
- **Received time:** when the application received the event.
- **Processing time:** when validation or normalization processed the event.
- **Data age:** the elapsed duration between a defined reference time and the
  event time, with the reference time explicitly supplied or defined by the
  processing context.

Requirements:

1. Timestamp values must preserve timezone and precision sufficient for the
   source contract.
2. Missing or malformed timestamps must produce an explicit quality outcome.
3. Event time must not be silently replaced with received or processing time.
4. Freshness calculations must be deterministic when reference time is fixed.
5. Production stale-data thresholds must be configurable.
6. No arbitrary production freshness threshold may be hard-coded in this task.
7. A stale determination must be observable and must not be silently treated as
   valid current data.
8. Clock skew or contradictory timestamp relationships must be represented as
   a quality or observability condition rather than silently hidden.

## 10. Data Quality Requirements

Quality state must be explicit, deterministic, and observable. At minimum, the
contract must support these categories:

- `VALID`: required fields and quality checks pass.
- `STALE`: the event is older than the configured freshness policy.
- `INVALID`: the event cannot be trusted or fails validation.
- `INCOMPLETE`: required information is missing.
- `DUPLICATE`: the event identity has already been observed.
- `OUT_OF_ORDER`: ordering information shows the event is not in the expected
  sequence.
- `SOURCE_UNAVAILABLE`: the source cannot currently provide usable data.

An implementation may use a different representation only if it preserves the
same distinctions and documents the mapping. Quality state must never be
silently inferred as `VALID` when required information is unknown.

## 11. Duplicate and Ordering Requirements

The future implementation must define deterministic behavior for:

1. **Duplicate detection:** Prefer source identity plus source context; when no
   source identifier exists, use a documented deterministic identity derived
   from canonical event content.
2. **Repeated source messages:** Mark repeated events as `DUPLICATE`; do not
   count them as new state without an explicit future policy.
3. **Sequence numbers:** Preserve source sequence or cursor values where
   available and validate monotonicity according to the source contract.
4. **Out-of-order events:** Mark events as `OUT_OF_ORDER` when ordering
   evidence proves they violate the applicable ordering rule.
5. **Missing sequence information:** Preserve the absence of sequence data and
   do not claim ordering guarantees that the source did not provide.
6. **Conflicting updates:** Do not silently overwrite contradictory state.
   Preserve the conflict as an explicit quality/observability outcome and
   require an approved resolution policy before accepting a replacement.
7. **Identity collisions:** Treat a collision that maps different payloads to
   the same deterministic identity as a contradiction or invalid condition,
   never as an ordinary duplicate.

## 12. Failure and Recovery Requirements

The contract must represent at least:

- Source availability.
- Source failure.
- Last known source health state.
- Failure observation time.
- Recovery observation time when recovery is detected.
- Whether data is currently usable, stale, or unavailable.

Requirements:

1. A source failure must be visible to downstream health and observability
   consumers.
2. Source failure must not be represented as fresh valid data.
3. Recovery must be explicit and observable.
4. A source must not be considered healthy merely because a process restarted.
5. Recovery must require an accepted, valid source observation according to the
   future source policy.
6. Repeated failure and recovery events must have deterministic identities or
   sequence semantics where applicable.
7. Retry and reconnection policy are future implementation concerns and are not
   defined or implemented by P02-T01.

## 13. Provider Adapter Boundary

The canonical domain contract must not directly depend on:

- A specific DEX SDK.
- A specific RPC provider.
- A specific WebSocket provider.
- Jupiter.
- Jito.
- Birdeye.
- DexScreener.
- Helius.
- Any other vendor or provider SDK.

A future provider adapter may translate external data into the canonical raw
event contract. That adapter must:

1. Own provider-specific parsing and error translation.
2. Preserve source identity and source-specific identifiers.
3. Preserve source timestamps and sequence information where available.
4. Avoid exposing provider-specific objects to canonical domain consumers.
5. Be replaceable without changing normalized domain contracts.
6. Be testable with deterministic local fixtures.

No provider adapter is implemented in P02-T01.

## 14. Persistence Boundary

P02-T01 may define conceptual future persistence requirements only.

Future persistence must be able to retain, as appropriate:

- Canonical identity.
- Source identity and source event identifier.
- Raw-event provenance or a durable reference to it.
- Normalized state.
- Event, received, and processing timestamps.
- Freshness/data age.
- Quality state.
- Sequence/order information.
- Failure and recovery observations.
- Configuration or contract version needed for reproducibility.

The following are explicitly not part of P02-T01:

- Database implementation.
- Production schema.
- Migration.
- Historical storage system.
- Retention job.
- Query API.
- Trading, position, signal, decision, risk, or execution tables.

Any future schema must be separately specified, reviewed, and migrated through
the existing database boundary.

## 15. Testing Requirements

The future implementation must use deterministic local fixtures and tests for
at least:

1. Valid event.
2. Malformed event.
3. Incomplete event.
4. Stale event.
5. Duplicate event.
6. Out-of-order event.
7. Contradictory event.
8. Unavailable source.
9. Recovery.
10. Deterministic normalization.
11. Freshness calculation with a fixed reference time.
12. Missing sequence information.
13. Identity collision.
14. Provider adapter boundary isolation.
15. Preservation of source and timestamp metadata.

No live network calls are required for P02-T01. Existing P01 tests must remain
passing during any later implementation.

## 16. Safety Requirements

The future implementation must preserve:

- Fail-closed behavior when required data is invalid, stale, incomplete,
  contradictory, or unavailable.
- No autonomous trading.
- No wallet access.
- No private-key handling.
- No signing.
- No transaction execution or broadcasting.
- No external side effects in deterministic contract tests.
- No secrets in source code.
- Explicit lifecycle control.
- Deterministic behavior.
- Auditable state and provenance.

No path may be created from P02-T01 directly to live trading. Any later
execution capability must pass through the documented Decision Intent, Risk /
Capital Authorization, Execution Request, isolated signing, broadcast,
reconciliation, and journal boundaries.

## 17. Observability Requirements

The future implementation must make observable:

- Source identity.
- Event identity.
- Event, received, and processing timestamps.
- Data age and freshness decision.
- Quality status.
- Duplicate and ordering result.
- Source failure and recovery state.
- Normalization or validation failure category.
- Contract or configuration version where needed for reproducibility.

Observability output must not expose credentials, private keys, or raw secret
values. Logging must remain compatible with the existing standard-library
logging boundary.

## 18. Acceptance Criteria

1. A canonical raw-event contract is defined.
2. A canonical normalized-state contract is defined.
3. Source identity is preserved.
4. Source-specific event identity is preserved where available.
5. Event, received, and processing timestamps are defined and distinct.
6. Freshness and data-age semantics are defined.
7. Stale-data semantics are configurable rather than based on an arbitrary
   production constant.
8. Explicit quality states support `VALID`, `STALE`, `INVALID`, `INCOMPLETE`,
   `DUPLICATE`, `OUT_OF_ORDER`, and `SOURCE_UNAVAILABLE`.
9. Duplicate handling is deterministic.
10. Repeated source messages have defined behavior.
11. Sequence and ordering behavior is defined where applicable.
12. Missing sequence information does not create false ordering guarantees.
13. Contradictory data is visible and is not silently overwritten.
14. Source failure and recovery states are defined.
15. The provider adapter boundary is provider-neutral.
16. Provider-specific details cannot leak into canonical domain contracts.
17. The persistence boundary is clearly separated from this documentation-only
    task.
18. Deterministic local testing requirements are defined.
19. No external I/O is required by this task.
20. No trading or execution capability is introduced.
21. Existing P01 architecture remains intact.
22. Existing P01 tests must remain passing during future implementation.
23. No new dependency is required merely to define or implement the contract.
24. No secrets are introduced.
25. The specification is internally consistent and implementation-testable.

## 19. Explicitly Out of Scope

P02-T01 must not include:

- Solana RPC integration.
- DEX integration.
- Token discovery.
- Emerging-token detection.
- Liquidity scanning.
- Swap ingestion.
- Transaction-flow ingestion.
- External price feeds.
- External volume feeds.
- WebSocket connections.
- REST/API integrations.
- Jupiter.
- Jito.
- Birdeye, DexScreener, Helius, or other provider integrations.
- Wallets.
- Private keys.
- Signing.
- Broadcasting.
- Trading.
- Paper trading.
- Signals.
- Opportunity scoring.
- Decision engine.
- Risk engine.
- AI, ML, or LLM functionality.
- Strategy generation.
- Autonomous behavior.
- Multi-agent architecture.
- Redis.
- Railway.
- Microservices.
- Generic plugin architecture.
- Dashboard expansion.
- Production deployment.
- Database implementation.
- Database schema or migrations.
- Automatic retry or restart policy.

P02-T01 is a contract task, not a data-collection task.

## 20. Dependencies

### Required predecessor

- P01-T01 through P01-T05 must remain complete and auditable.
- The existing Python/FastAPI runtime, configuration, logging, safety,
  persistence, application-service, and worker boundaries must be preserved.

### Phase dependency

- P02 depends on P01.
- P02 entry criteria require a foundation capable of securely running and
  persisting validated data.

### Approval dependency

- This specification requires explicit architectural approval before
  implementation.
- Provider selection, external connectivity, persistence changes, and any
  credentials require separate review if they are later proposed.

## 21. Implementation Constraints

Future implementation must:

1. Make the smallest change consistent with this contract.
2. Preserve the existing P01 architecture and dependency direction.
3. Prefer existing dependencies and standard-library primitives.
4. Keep canonical contracts provider-neutral.
5. Keep validation and normalization deterministic.
6. Use explicit reference times for freshness tests.
7. Fail closed on unknown, stale, invalid, incomplete, or contradictory data
   where downstream safety requires reliable information.
8. Avoid speculative domain fields.
9. Avoid provider-specific abstractions in canonical domain modules.
10. Introduce no live network behavior without separate approval.
11. Introduce no trading, wallet, signing, execution, or autonomous behavior.
12. Add no dependency unless separately justified and approved.

## 22. Governance / Approval Gate

**STATUS: SPECIFICATION DRAFT — NOT IMPLEMENTED**

**IMPLEMENTATION AUTHORIZED: NO**

P02-T01 implementation requires explicit architectural approval after review of
this specification.

The existence of this specification does not authorize P02 implementation.
P02 remains NOT STARTED. No provider, adapter, ingestion process, migration,
worker with real work, or external integration may be added until approval is
recorded and a concrete implementation task is opened.

## 23. Expected Deliverables

After explicit approval, the future implementation task may deliver only the
approved contract realization, including:

- Canonical raw-event and normalized-state types or equivalent contracts.
- Deterministic validation and normalization behavior.
- Freshness and quality evaluation behavior.
- Duplicate, ordering, contradiction, failure, and recovery handling.
- A provider-neutral adapter interface without a provider implementation.
- Deterministic local fixtures and tests.
- Documentation of any approved persistence implications.
- Updated project state only after implementation and verification are actually
  complete.

No code or runtime deliverable is produced by this specification-only task.