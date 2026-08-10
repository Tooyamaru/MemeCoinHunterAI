# P01-T05 — Application Service & Worker Extensions

**Status:** DONE
**Approval state:** Explicitly approved and implemented according to this contract
**Phase:** P01 — Application Foundation  
**Predecessor:** P01-T04 — Application Service & Worker Foundation

## Objective

Extend the existing P01-T04 application and worker foundation into a
deterministic, reusable, testable service/worker lifecycle coordination layer.

## Approved scope

P01-T05 may implement only:

1. Explicit worker registration and unregistration.
2. Deterministic worker enumeration and inspection.
3. Coordinated worker start.
4. Coordinated worker stop.
5. Aggregated worker status.
6. Deterministic shutdown.
7. Cancellation-safe coordination.
8. Fail-closed safety propagation.
9. Failure visibility.
10. Preservation of import safety and existing lifecycle behavior.

The following invariants apply:

- Workers must never start automatically merely because a module is imported.
- Worker execution remains explicitly controlled.
- Safety defaults remain fail-closed.
- Existing P01-T04 behavior must be preserved.

## Explicitly out of scope

P01-T05 must not include:

- Scheduling or cron.
- Automatic retry.
- Automatic restart.
- Domain-specific workers.
- External I/O.
- Solana.
- DEX.
- Market-data ingestion.
- Token discovery.
- Signals.
- Opportunity analysis.
- AI, ML, or LLM functionality.
- Decision-engine functionality.
- Risk-engine functionality.
- Paper trading.
- Live trading.
- Wallets.
- Signing.
- Transaction execution.
- Redis.
- Railway.
- Microservices.
- Multi-agent architecture.
- Generic plugin architecture.
- Database schema changes.
- Database migrations.
- Full dashboard features.
- Autonomous behavior.

## Architectural boundary

P01-T05 must preserve the existing foundation boundary:

```text
API / future workers
          ↓
Application Service / Worker Coordination
          ↓
Runtime + Safety + Config + Logging
          ↓
Infrastructure boundaries
```

The implementation must not bypass existing runtime or safety boundaries.

## Acceptance criteria

1. Existing P01-T04 tests continue to pass.
2. A worker can be explicitly registered.
3. Duplicate worker identity is rejected deterministically.
4. Registered workers can be inspected without starting them.
5. Multiple workers can be started deterministically.
6. Multiple workers can be stopped deterministically.
7. Coordinated shutdown remains safe when a worker is cancelled.
8. Coordinated shutdown remains safe when a worker fails.
9. Unsafe safety state prevents worker execution.
10. Worker lifecycle coordination creates no background task during import.
11. No external I/O is introduced.
12. New behavior has deterministic unit tests.
13. Existing `/health` and `/ready` behavior remains intact.
14. No database schema changes are introduced.
15. No domain, trading, or AI logic is introduced.
16. No new dependency is introduced unless explicitly justified; existing
    dependencies and standard-library async primitives are preferred.

## Implementation guidance

Potential existing locations include:

- `backend/application/service.py`
- `backend/workers/runtime.py`
- `backend/core/runtime.py`
- `backend/core/safety.py`
- `backend/api/main.py`
- `tests/test_service_worker.py`

These locations are not mandatory. The implementation must inspect the current
repository and use the smallest change consistent with the architecture. No
speculative files or abstractions should be created.

## Governance

P01-T05 implementation is complete and was performed only after this
specification was explicitly approved as the implementation contract.

**P01-T05 implementation must follow this specification and must not expand
beyond its approved scope without explicit architectural approval.**
