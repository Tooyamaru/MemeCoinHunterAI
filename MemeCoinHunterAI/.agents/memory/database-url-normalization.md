---
name: Database URL normalization
description: Replit's injected PostgreSQL URL may use sslmode, which must be normalized before asyncpg connects.
---

The persistence boundary normalizes common PostgreSQL URL schemes to asyncpg and translates supported `sslmode` values before creating an async SQLAlchemy engine.

**Why:** Replit can inject a PostgreSQL URL containing `sslmode`, while asyncpg does not accept that keyword directly. Without normalization, API startup can fail before the application can report `UNAVAILABLE`.

**How to apply:** Keep URL normalization inside the database runtime boundary; do not expose or log raw credentials, and preserve truthful readiness when the configured database cannot connect.