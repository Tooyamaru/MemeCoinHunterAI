---
name: Python 3.13 runtime
description: Environment constraint for running this project's declared Python version on Replit.
---

The project declares Python 3.13. In this workspace, `uv` is configured not to download interpreters, and the shell currently exposes Python 3.12 without pytest. The available `python-base-3.13` runtime may need to be activated before running the locked test environment.

**Why:** `uv run --no-sync` cannot select the project interpreter when downloads are disabled, and the preinstalled Python 3.12 has no pytest.

**How to apply:** Check the active Python version before testing. If 3.13 is unavailable, use the supported `python-base-3.13` runtime module rather than changing the project's version requirement or dependencies.