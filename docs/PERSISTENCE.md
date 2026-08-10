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

## Migrations

Alembic configuration lives in `alembic.ini`, `migrations/env.py`, and `migrations/versions/`. Migration metadata is imported from `backend.core.models.Base.metadata`. The initial revision creates only `system_metadata`. Migration commands use `DATABASE_URL`; no credentials are stored in source.

## Test database

Tests use an isolated temporary SQLite database through `sqlite+aiosqlite`. This is test-only and is not used by production configuration. Tests explicitly pass `database_url=None` or a test URL, so ambient Replit `DATABASE_URL` cannot change their behavior.

## Setup and security

`bash scripts/replit_setup.sh` installs the locked dependencies but does not create, destroy, or migrate a database. Apply migrations deliberately in a configured environment; never print `DATABASE_URL`, commit `.env`, or put credentials in logs.
