# AI AGENTS — IMPORTANT

**DO NOT SCAN THE FULL REPOSITORY.**

**FIRST READ:**

1. `REPLIT_RULES.md`
2. `PROJECT_STATE.md`

Then read only files relevant to the current task.

## Meme Coin Hunter AI

Meme Coin Hunter AI is a future AI-driven crypto intelligence and trading system. It is designed to discover and evaluate emerging Solana meme-coin opportunities while keeping intelligence, decisions, risk governance, execution, and learning logically separate.

## Current status

The project is in P02 — Solana / DEX Data Intelligence. P02-T01 — Data Ingestion and Normalization Contract is complete. It provides deterministic, provider-neutral raw-event and normalized-state contracts without provider connectivity. No Solana, DEX, wallet, trading, AI/ML, paper-trading, or Railway functionality has been implemented.

## Architecture summary

The planned pipeline is:

`Token universe → ingestion → validation/normalization → safety/eligibility → signals → opportunity → phase analysis → decisions → risk governance → paper/execution → positions → learning`

The Risk Governor has authority over the Decision Engine. Any future execution must pass through an execution abstraction and the Risk Governor.

## Development workflow

1. Read `REPLIT_RULES.md` and `PROJECT_STATE.md`.
2. Inspect only the current task's relevant files.
3. Make the smallest scoped change.
4. Run targeted verification.
5. Update documentation and `PROJECT_STATE.md`.
6. Commit/push through the single GitHub repository when ready.

### Run the P01 foundation

```bash
bash scripts/replit_setup.sh
uv run uvicorn backend.api.main:app --host "${APP_HOST:-0.0.0.0}" --port "${PORT:-${APP_PORT:-8000}}"
```

The only endpoint currently provided by the Python foundation is `GET /health`.

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
