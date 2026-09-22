# AI AGENTS — IMPORTANT

**DO NOT SCAN THE FULL REPOSITORY.**

**FIRST READ:**

1. `REPLIT_RULES.md`
2. `PROJECT_STATE.md`

Then read only files relevant to the current task.

## Meme Coin Hunter AI

Meme Coin Hunter AI is a future selective, deterministic, explainable, risk-first, paper-first memecoin opportunity and decision platform. It is designed to discover and evaluate emerging Solana meme-coin opportunities while keeping intelligence, decisions, risk governance, execution, and learning logically separate.

## Current status

The project is currently at P08 — Outcome Learning. P07-T01 through P07-T07
and P08-T01 through P08-T07 are complete, closed, and audited PASS. P04-LME-01
through P04-LME-03 also provide a bounded CoinGecko pool-OHLCV mapper,
single-attempt server-side read-only transport, diagnostic, and caller-directed
one-shot orchestration. Live provider verification has not run. The G2
realization/settlement endpoint boundary discovery is complete but remains
documentation-only, blocked, unresolved, and unauthorized pending an
owner-approved realization/settlement source. No continuous polling, automatic
pool selection, application runtime wiring, wallet, live trading, AI/ML, or P09
execution functionality has been implemented.

The controlled paper path now has one-shot admission (P01-RTI-01), lifecycle
(P01-RTI-02), and append-only persistence (P01-RTI-03), all merged and CI
verified. P01-RTI-04 is the next specification gate for one explicit
caller-triggered application-service invocation; implementation is not yet
authorized.

## Architecture summary

The planned pipeline is:

`Token universe → ingestion → validation/normalization → safety/eligibility → signals → opportunity → phase analysis → decisions → risk governance → paper/execution → positions → learning`

The Risk Governor has authority over the Decision Engine. Any future execution must pass through an execution abstraction and the Risk Governor.

## Development workflow

GitHub is the source of truth. Development uses short-lived branches and pull
requests; Replit is the runtime/preview environment rather than an independent
copy of the project. See `docs/HYBRID_DEVELOPMENT_WORKFLOW.md` for the complete
change, test, review, and merge path.

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

The only endpoint currently provided by the Python foundation is `GET /health`.

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

- `apps/dashboard/` — future presentation application
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
