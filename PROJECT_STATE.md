# AI ENTRY POINT

**DO NOT SCAN THE FULL REPOSITORY.**

Read `REPLIT_RULES.md` first. Use this file as the authoritative current development state. Then read only the files listed under **Relevant files for current task**.

## Project

- **Project name:** Meme Coin Hunter AI
- **Current phase:** P01 — Application Foundation
- **Current task:** P01-T04 — Application Service & Worker Foundation
- **Current task status:** DONE
- **Last updated:** 2026-08-10

## Master progress

- P00: DONE; T01 done; T02 done
- P01: T01 done; T02 done; T03 done; T04 done; T05 not started
- P02–P12: Not started

## Phase status

- **Done:** P00 governance map, architecture boundaries, continuation rules, safety and testing principles; P01-T01 technical baseline and minimal runtime; P01-T02 runtime and configuration foundation; P01-T03 persistence foundation
- **In progress:** None
- **Blocked:** None
- **On hold:** None
- **Not started:** P01-T05 application service and worker extensions and all later implementation phases

## Current objective

Maintain a portable, auditable application foundation with explicit service,
worker lifecycle, and fail-closed safety boundaries before implementing any
market, AI, wallet, trading, or production functionality.

## Last verified checkpoint

P01-T04 application service and worker foundation verified on 2026-08-10.
No market, AI, wallet, trading, or execution functionality was added.

## Relevant files for current task

- `REPLIT_RULES.md`
- `PROJECT_STATE.md`
- `README.md`
- `docs/MASTER_BLUEPRINT.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_PIPELINE.md`
- `docs/DECISION_ENGINE.md`
- `docs/RISK_ENGINE.md`
- `docs/EXECUTION_ENGINE.md`
- `docs/LEARNING_ENGINE.md`
- `docs/SECURITY.md`
- `docs/TESTING_STRATEGY.md`
- `docs/CHANGELOG.md`
- `docs/TESTING_STRATEGY.md`
- `scripts/replit_setup.sh`
- `docs/TECHNICAL_BASELINE.md`
- `pyproject.toml`
- `uv.lock`
- `backend/api/main.py`
- `backend/core/config.py`
- `backend/core/logging.py`
- `backend/core/database.py`
- `backend/core/runtime.py`
- `backend/core/request_id.py`
- `backend/core/models.py`
- `backend/core/repositories.py`
- `docs/PERSISTENCE.md`
- `alembic.ini`
- `migrations/env.py`
- `migrations/versions/0001_create_system_metadata.py`
- `tests/test_foundation.py`
- `.env.example`

## Optional files

- `replit.md`
- `lib/`
- `artifacts/`

## Do not read / out of scope

- Do not scan the full repository.
- Do not start P01-T05 without explicit user approval and review of the V1.1 architecture baseline.
- Do not implement Solana, DEX, wallet, AI/ML, signals, paper trading, execution, Railway, Redis, or a full dashboard before their planned phases.

## Known issues

- No known P01-T03 issues.
- P01-T04 adds only service/worker lifecycle and safety boundaries; no external
  integrations, database migrations, trading capabilities, commit, or push were
  added.

## Next action

Wait for user review and explicit approval before beginning P01-T05.

## Next task

P01-T05 — Application Service & Worker Extensions (NOT STARTED)

## Required secret names

No secret values are stored here. Future integrations must use environment
secrets; names will be added only when a later task requires them.

## V1.1 architecture revision

- **Status:** DONE as a documentation/governance revision
- **Baseline:** V1.1
- **Implementation authorized by this revision:** P01-T04 only
- **P01-T04:** DONE
- **Next implementation action:** P01-T05 is gated pending user review and explicit approval
