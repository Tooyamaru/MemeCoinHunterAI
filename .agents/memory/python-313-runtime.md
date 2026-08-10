---
name: Python 3.13 runtime
description: Environment constraint for running this project's declared Python version on Replit.
---

The project declares Python 3.13. In this workspace, `uv` is configured not to download interpreters, and the general Python tools module may not provide 3.13. The available `python-base-3.13` runtime is sufficient for running the locked environment and tests.

**Why:** Running tests with the preinstalled Python 3.12 fails before collection because the project requires Python 3.13.

**How to apply:** Check the active Python version before testing. If 3.13 is unavailable, use the supported `python-base-3.13` runtime module rather than changing the project's version requirement or dependencies.