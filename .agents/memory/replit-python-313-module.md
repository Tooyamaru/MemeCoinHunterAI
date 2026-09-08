---
name: Replit Python 3.13 module
description: Replit's available Python 3.13 module and dependency-management behavior for this project
---

Use `python-base-3.13` when configuring this project in Replit. The older `python-3.13` identifier is not present in the available module inventory.

**Why:** The base module provides the required Python 3.13 runtime and the `python`/`python3` commands, while this project intentionally manages its locked dependencies with `uv` rather than system pip.

**How to apply:** Keep the Python requirement at 3.13, use the repository's `scripts/replit_setup.sh` / `uv.lock` flow to restore dependencies, and verify with the project's Python test command.