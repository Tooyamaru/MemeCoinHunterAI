---
name: Python 3.13 runtime
description: Environment constraint for running this project's declared Python version on Replit.
---

The project declares Python 3.13. Replit's system Python may be 3.12 and may not include pytest, so the supported `python-base-3.13` runtime should be active before creating the uv-managed project environment. Pin the project baseline to Python 3.13 and use uv for dependency resolution and test execution.

**Why:** The preinstalled Python 3.12 does not satisfy the project requirement and has no pytest. Activating `python-base-3.13` exposes a compatible interpreter; `uv sync --locked` then creates the reproducible environment and installs the locked development tools.

**How to apply:** Check the active Python version before testing. If 3.13 is unavailable, activate the supported `python-base-3.13` runtime rather than weakening the requirement or changing dependencies. Pin an available stable 3.13 interpreter explicitly; generic uv selection may choose an incompatible 3.14 beta. Run tests through `uv run pytest`, not a global pytest executable. If greenlet cannot load, add the compiler's `libstdc++` directory to `LD_LIBRARY_PATH` for the test process only.