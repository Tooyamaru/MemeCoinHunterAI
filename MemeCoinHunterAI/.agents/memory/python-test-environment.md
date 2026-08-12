---
name: Python test environment
description: Replit may inject database configuration into Python test processes even when dotenv loading is disabled.
---

Tests that assert development configuration defaults should explicitly pass `database_url=None` (or another intended value) rather than relying only on `_env_file=None`.

**Why:** Replit can expose a workspace-level `DATABASE_URL` to the process environment, which otherwise makes tests depend on the current workspace.

**How to apply:** Keep runtime configuration environment-based, but construct deterministic test settings explicitly whenever a test needs to exercise an unset optional service.