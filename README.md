# AI AGENTS — IMPORTANT

**DO NOT SCAN THE FULL REPOSITORY.**

**FIRST READ:**

1. `REPLIT_RULES.md`
2. `PROJECT_STATE.md`

Then read only files relevant to the current task.

## Meme Coin Hunter AI

Meme Coin Hunter AI is a future selective, deterministic, explainable, risk-first, paper-first memecoin opportunity and decision platform. It is designed to discover and evaluate emerging Solana meme-coin opportunities while keeping intelligence, decisions, risk governance, execution, and learning logically separate.

## Current status

The deterministic paper-first domain pipeline is mature through P07 and the
bounded RTI-11→RTI-16 integration path. The Operator Application Facade now
provides an authenticated, explicitly controlled paper workflow: trusted
Solana/P03 upstream composition, one-shot exact-pool RTI-11 preparation,
temporary identity-preserving case review, explicit run-once OCI/OSC handoff,
explicit RTI-03 persistence, and durable lifecycle readback/catalog surfaces.

The standalone Hunter Room controlled-paper operator surface is implemented
through HR-FND-11. It reflects server case state and provides authenticated
readiness, no-I/O payload validation, explicit prepare gating, review,
two-step run/persist confirmation, server case lifetime/provenance visibility,
stale armed-action invalidation, durable readback gating, manual persisted
history/detail inspection, and explicit browser-memory session cleanup.
There is no automatic polling or retry. Active cases remain process-local and
require one stable application process from prepare through run/persist. Offline
hardening of the controlled-paper smoke path is complete for this governed
single-process scope; the remaining verification is one separately authorized
provider-backed controlled-paper smoke. The controlled-paper smoke CLI also
supports a no-provider `--preflight-only` mode
that stops after authenticated readiness and canonical payload validation, and
fails closed if the preflight contract, safety claims, or explicit identity
projection do not match the submitted case intent. Successful prepare and first
review must then preserve the exact case, candidate/token/chain/pool identity,
CIP digest, review path, simulation-only boundary, and controlled source label
before run is permitted. A provider-backed preparation STOP is accepted only
under the exact post-prepare STOP contract with simulation-only and explicit
reason codes. Run, post-run review, persistence, and durable readback then each
require their exact current contract, terminal/simulation boundaries, and
canonical digest/artifact projections before the smoke may continue.

The project remains **paper/simulation only**. There is no wallet ownership,
signing, transaction broadcast, DEX execution, autonomous hunting loop, or
real-money trading. P08 G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED;
G3/G4/P09 remain NOT AUTHORIZED. The existing TypeScript Memecoin Inspection
artifact and its `lib/api-spec/openapi.yaml` remain a separate read-only
inspection surface from the Python FastAPI Operator Facade.

## Architecture summary

The planned pipeline is:

`Token universe → ingestion → validation/normalization → safety/eligibility → signals → opportunity → phase analysis → decisions → risk governance → paper/execution → positions → learning`

The Risk Governor has authority over the Decision Engine. Any future execution must pass through an execution abstraction and the Risk Governor.

## Development workflow

GitHub `main` is the source of truth. ChatGPT is the primary controller,
architecture, implementation, review, and documentation surface; ChatGPT Work
may be used for heavier multi-step execution when available. Replit is a
fallback runtime/preview environment only when a specific interactive runtime
or environment task cannot be completed in ChatGPT. See
`docs/HYBRID_DEVELOPMENT_WORKFLOW.md` for the complete change, test, review,
and merge path.

1. Read `REPLIT_RULES.md` and `PROJECT_STATE.md`.
2. Create a scoped branch from the latest `main`.
3. Inspect only the current task's relevant files.
4. Make the smallest authorized change and add applicable tests.
5. Run targeted checks, then the applicable full checks.
6. Update documentation and `PROJECT_STATE.md`.
7. Open a pull request and require CI to pass before merge.

### Run the P01 foundation

```bash
bash scripts/replit_setup.sh
uv run uvicorn backend.api.main:app --host "${APP_HOST:-0.0.0.0}" --port "${PORT:-${APP_PORT:-8000}}"
```

The Python FastAPI surface now includes health/readiness, persisted paper lifecycle readback, and authenticated Operator Facade prepare/review/run/persist routes. See `docs/TECHNICAL_BASELINE.md` and the OAF/Hunter Room specification for the bounded contract.

### Python environment and tests

Replit's system Python is not the project source of truth. The project baseline
is pinned to Python 3.13 in `.python-version`, and uv manages the project
environment from `pyproject.toml` and `uv.lock`.

Run the read-only environment diagnostic before debugging Python or test
failures:

```bash
bash scripts/python_env_diagnostic.sh
```

Run tests through the project environment, not a globally installed pytest:

```bash
uv run pytest -q
uv run pytest -q --collect-only
```

## Repository structure

- `apps/dashboard/` — reserved production dashboard package location; the standalone Hunter Room build is currently packaged from the mockup-sandbox implementation
- `backend/api/` — future API boundary
- `backend/core/` — configuration, logging, and infrastructure boundaries
- `workers/` — future long-running workers
- `core/` — future domain modules
- `database/` — future database assets and migrations
- `tests/` — future verification
- `docs/` — governance and architecture source
- `scripts/` — portability and maintenance scripts

Existing workspace libraries and artifacts are retained. The existing TypeScript API artifact remains separate; the P01 Python baseline lives under `backend/`.

## Continuation procedure

In a blank Replit workspace, clone the GitHub repository, run `bash scripts/replit_setup.sh`, read the two AI entry-point files, and inspect only the files named by the current task. Do not depend on automatic repository-wide import analysis.

## Safety status

Real-money trading is disabled by project rule. No wallet credentials, private keys, or secret values belong in the repository. Profitability is not assumed; future live execution requires evidence of executable edge after fees, slippage, latency, failed execution, liquidity constraints, and regime changes.
