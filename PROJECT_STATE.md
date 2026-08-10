# AI ENTRY POINT

**DO NOT SCAN THE FULL REPOSITORY.**

Read `REPLIT_RULES.md` first. Use this file as the authoritative current development state. Then read only the files listed under **Relevant files for current task**.

## Project

- **Project name:** Meme Coin Hunter AI
- **Current phase:** P02 — Solana / DEX Data Intelligence
- **Current task:** P02-T01 — Data Ingestion and Normalization Contract
- **Current task status:** DONE
- **Last updated:** 2026-08-10

## Master progress

- P00: DONE; T01 done; T02 done
- P01: T01 done; T02 done; T03 done; T04 done; T05 done
- P02: T01 done
- P03–P12: Not started

## Phase status

- **Done:** P00 governance map, architecture boundaries, continuation rules, safety and testing principles; P01-T01 technical baseline and minimal runtime; P01-T02 runtime and configuration foundation; P01-T03 persistence foundation; P01-T04 application service and worker foundation; P01-T05 application service and worker extensions; P02-T01 provider-neutral data ingestion and normalization contract
- **In progress:** None
- **Blocked:** None
- **On hold:** None
- **Not started:** P03–P12

## Current objective

Maintain a portable, auditable data boundary with deterministic normalization,
explicit provenance and freshness, and fail-closed quality states before
implementing any safety, market, AI, wallet, trading, or production
functionality.

## Last verified checkpoint

P02-T01 data ingestion and normalization contract verified on 2026-08-10.
No provider integration, external I/O, migration, market strategy, AI, wallet,
trading, or execution functionality was added.

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
- `docs/P01-T05_SPECIFICATION.md`
- `docs/P02-T01_SPECIFICATION.md`
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
- Later implementation phases must not begin without explicit approval and review of the applicable architecture baseline.
- Do not implement Solana, DEX, wallet, AI/ML, signals, paper trading, execution, Railway, Redis, or a full dashboard before their planned phases.

## Known issues

- No known P02-T01 issues.
- P02-T01 adds only provider-neutral contracts, deterministic validation and
  normalization, explicit quality/freshness/order state, and source
  failure/recovery tracking; no provider, external I/O, migration, trading
  capability, commit, or push was added.

## Next action

Review the proposed P02-T02 specification. Do not implement it until explicit
approval is recorded and a concrete implementation task is opened.

## Next task

The next candidate is documented for review only:

- **P02-T02 — Provider-Neutral Ingestion Orchestration and Source Health Boundary**
- **Status:** SPECIFICATION DRAFT — NOT IMPLEMENTED
- **Implementation authorized:** NO
- **Specification:** `docs/P02-T02_SPECIFICATION.md`

P02-T01 remains complete and is the required predecessor. The draft does not
authorize provider connectivity, ingestion workers, persistence changes, or
later P02 capabilities.

## Required secret names

No secret values are stored here. Future integrations must use environment
secrets; names will be added only when a later task requires them.

## V1.1 architecture revision

- **Status:** DONE as a documentation/governance revision
- **Baseline:** V1.1
- **Implementation authorized by this revision:** P01-T04 and P01-T05; P02-T01 was separately approved against its specification
- **P01-T04:** DONE
- **P01-T05:** DONE
- **P02-T01:** DONE
- **P02-T02:** SPECIFICATION DRAFT ONLY; NOT AUTHORIZED
- **Next implementation action:** Await review and explicit approval; do not implement
