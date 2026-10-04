# Persistence Foundation

## Target and dependencies

PostgreSQL is the long-term application database. Persistence uses async SQLAlchemy 2.x with `asyncpg`; `aiosqlite` is used only by isolated tests. There is one database library and one session strategy.

Common `postgresql://` and `postgres://` URLs are normalized to the asyncpg driver. Replit's `sslmode` query setting is translated before the asyncpg connection attempt.

## Runtime behavior

`backend/core/database.py` owns lazy engine creation, the real `SELECT 1` connectivity check, session creation, state reporting, and disposal. `DATABASE_URL` behavior is:

- Empty/unset: `NOT_CONFIGURED`
- Configured but not yet checked: `CONFIGURED`
- Successful connection check: `CONNECTED`
- Failed connection check: `UNAVAILABLE`

The URL is redacted before it appears in logs. Credentials are never returned to API clients.

The API can start without a database in development. `/health` reports process liveness. `/ready` is ready when the internal runtime is ready and either the database is not configured or it is connected; a configured unavailable database produces a truthful not-ready response.

## Sessions and transactions

API and future workers use `DatabaseRuntime.session_scope()` as the unit-of-work boundary. It creates a short-lived session, commits when the operation succeeds, rolls back on exceptions, and closes the session reliably. Repositories receive a session; domain code does not open raw connections.

The current repository example is `SystemMetadataRepository`, backed only by the infrastructure-level `system_metadata` table. Trading, market, wallet, position, signal, decision, and learning tables are intentionally deferred.

P01-RTI-03 adds a narrowly bounded exception for completed paper-runtime
integration records. `paper_lifecycle_runs` stores one immutable P01-RTI-02
root identity, and `paper_lifecycle_artifacts` stores its ordered canonical
artifact snapshots. The application persistence service validates and builds
the full bundle before opening one write transaction. Exact retries are
idempotent, storage disagreements fail closed, and partial writes roll back.
The repository exposes no update or delete operation.

This storage is an audit snapshot, not a live position, wallet, settlement,
economic-result, dashboard, or complete replay-input store. Database timestamps
are operational metadata only and never become domain or learning facts.

A1-AUD-01 adds a separate explicit source-audit attachment after a successful
canonical lifecycle is already persisted. `a1_collection_audits` holds one
immutable canonical packet/raw-byte/binding snapshot and its lifecycle link in
one row. The existing RTI-03 root and 13 artifact kinds are unchanged. Exact
duplicates are idempotent; disagreements fail closed; audit rollback preserves
the independently completed lifecycle. Audit readback checks both source
integrity and the exact existing lifecycle bundle. It never reconstructs an
active case or restarts owners. There is no automatic cycle or API wiring.

## Migrations

Alembic configuration lives in `alembic.ini`, `migrations/env.py`, and
`migrations/versions/`. Migration metadata is imported from
`backend.core.models.Base.metadata`. The initial revision creates only
`system_metadata`; revision `0002_paper_lifecycle` creates only the two
controlled paper-lifecycle tables and their identity/order constraints.
Revision `0003_a1_collection_audit` creates only the separate audit/link table,
with a RESTRICT foreign key and unique run/lifecycle/audit identities. Upgrade,
downgrade and re-upgrade are tested against a populated temporary SQLite
database. No operational PostgreSQL migration is applied or qualified by this
offline work. See the A1 durable-audit linkage specification for the full
capture, idempotence, corruption and transaction contract.
Migration commands use `DATABASE_URL`; no credentials are stored in source.

## Test database

Tests use an isolated temporary SQLite database through `sqlite+aiosqlite`. This is test-only and is not used by production configuration. Tests explicitly pass `database_url=None` or a test URL, so ambient Replit `DATABASE_URL` cannot change their behavior.

## Setup and security

`bash scripts/replit_setup.sh` installs the locked dependencies but does not create, destroy, or migrate a database. Apply migrations deliberately in a configured environment; never print `DATABASE_URL`, commit `.env`, or put credentials in logs.
