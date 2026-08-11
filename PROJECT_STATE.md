# AI ENTRY POINT

**DO NOT SCAN THE FULL REPOSITORY.**

Read `REPLIT_RULES.md` first. Use this file as the authoritative current development state. Then read only the files listed under **Relevant files for current task**.

## Project

- **Project name:** Meme Coin Hunter AI
- **Current phase:** P02 — Solana / DEX Data Intelligence
- **Current task:** P02-T05 — Discovery-to-Orchestration Integration Boundary
- **Current task status:** IMPLEMENTED / VERIFIED
- **Last updated:** 2026-08-11

## Master progress

- P00: DONE; T01 done; T02 done
- P01: T01 done; T02 done; T03 done; T04 done; T05 done
- P02: T01 done; T02 done; T03 done; T04 done; T05 done
- P03–P12: Not started

## Phase status

- **Done:** P00 governance map, architecture boundaries, continuation rules, safety and testing principles; P01-T01 technical baseline and minimal runtime; P01-T02 runtime and configuration foundation; P01-T03 persistence foundation; P01-T04 application service and worker foundation; P01-T05 application service and worker extensions; P02-T01 provider-neutral data ingestion and normalization contract; P02-T02 provider-neutral ingestion orchestration and source health boundary; P02-T03 provider-neutral source adapter contract; P02-T04 provider-neutral token universe / discovery contract; P02-T05 discovery-to-orchestration integration boundary
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

P02-T05 discovery-to-orchestration integration boundary
verified on 2026-08-11. Focused P02-T05 tests, all P02 tests, the full
regression suite, Python compilation, and diff checks passed. The boundary
validates accepted P02-T04 discovery output, preserves point-in-time
provenance and classification, converts deterministically to the existing
P02-T02 orchestration input, and delegates publication through the existing
publisher protocol. No provider, network, RPC, DEX, wallet, AI/model,
trading, execution, database, persistence, migration, or dependency
integration was added.

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

- P02-T04 corrective patch remains complete and verified. P02-T05 is complete
  and verified against its controlled scope.
- P02-T04 adds only provider-neutral token discovery observation and record
  contracts, deterministic duplicate/contradiction/stale/out-of-order handling,
  cursor resynchronization semantics, bounded provenance, local publication,
  and P02-T03 adapter observation consumption; no provider, external I/O,
  migration, trading capability, or dependency was added.
- P02-T03 adds only provider-neutral adapter identity, capability, lifecycle,
  health observation, deterministic fake-adapter behavior, P02-T02 observation
  production, and local integration tests; no provider, external I/O,
  migration, trading capability, or dependency was added.
- P02-T02 adds only provider-neutral observation envelopes, deterministic
  orchestration, explicit accepted/rejected outcomes, source health/recovery,
  resynchronization, publication, and local tests; no provider, external I/O,
  migration, trading capability, commit, or push was added.

## Next action

Await review of the completed P02-T05 implementation. Do not start P02-T06 or
any later task without separate authorization.

## Next task

P02-T06 — NOT STARTED / NOT AUTHORIZED. P03 and all later tasks are also not
started or authorized. Provider connectivity, ingestion transports, persistence
changes, and other later P02 capabilities require separate specifications and
approval.

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
- **P02-T02:** DONE
- **P02-T03:** DONE
- **P02-T04:** DONE
- **P02-T05:** DONE
- **Next implementation action:** Await review; P02-T06 and P03 remain NOT STARTED / NOT AUTHORIZED
