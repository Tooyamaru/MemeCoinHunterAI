# AI ENTRY POINT

**DO NOT SCAN THE FULL REPOSITORY.**

Read `REPLIT_RULES.md` first. Use this file as the authoritative current development state. Then read only the files listed under **Relevant files for current task**.

## Project

- **Project name:** Meme Coin Hunter AI
- **Current phase:** P03 — Token Safety & Risk Intelligence
- **Current task:** P03-T01 — Token Safety Evidence & Eligibility Contract
- **Current task status:** IMPLEMENTED — AUDITED — PASS WITH NON-BLOCKING OBSERVATIONS — TECHNICALLY COMPLETE
- **Last updated:** 2026-08-12

## Master progress

- P00: DONE; T01 done; T02 done
- P01: T01 done; T02 done; T03 done; T04 done; T05 done
- P02: T01 done; T02 done; T03 done; T04 done; T05 done; T06 done; T07 done; T08 done; T09 done
- P03: T01 implemented, audited, and technically complete; T02 code exists but is NOT AUTHORIZED / NOT formally closed; T03 not authorized
- P04–P12: Not started

## Phase status

- **Done:** P00 governance map, architecture boundaries, continuation rules, safety and testing principles; P01-T01 technical baseline and minimal runtime; P01-T02 runtime and configuration foundation; P01-T03 persistence foundation; P01-T04 application service and worker foundation; P01-T05 application service and worker extensions; P02-T01 provider-neutral data ingestion and normalization contract; P02-T02 provider-neutral ingestion orchestration and source health boundary; P02-T03 provider-neutral source adapter contract; P02-T04 provider-neutral token universe / discovery contract; P02-T05 discovery-to-orchestration integration boundary; P02-T06 provider-neutral token-universe state / materialization boundary; P02-T07 provider-neutral token-scoped market observation evidence contract; P02-T08 provider-neutral market state materialization boundary; P02-T09 provider-neutral market intelligence boundary — FINAL; P03-T01 token safety evidence and eligibility contract — IMPLEMENTED / AUDITED / PASS WITH NON-BLOCKING OBSERVATIONS / TECHNICALLY COMPLETE
- **In progress:** None
- **Blocked:** None
- **On hold:** None
- **Not started:** P03 implementation phase; P04–P12

## Current objective

Maintain a portable, auditable data boundary with deterministic normalization,
explicit provenance and freshness, and fail-closed quality states before
implementing any safety, market, AI, wallet, trading, or production
functionality.

## Last verified checkpoint

P03-T01 technical audit completed on 2026-08-12 with a PASS WITH
NON-BLOCKING OBSERVATIONS result. The focused P03-T01 suite passed with 16
tests. No implementation boundary violations were found. P03-T02 code exists
in the repository but is NOT AUTHORIZED and NOT formally closed; it requires a
separate governance decision.

Final P02-T09 verification for the provider-neutral market intelligence
boundary, completed on 2026-08-12 at Git baseline `8958ed2` (HEAD and
origin/main). P02-T06, P02-T07, P02-T08, and P02-T09 are completed and
verified; the P02-T09 architecture gate is PASS. The P02-T09 stale-data
validation fix and explicit source-event identity/contradiction fix are
complete and committed. The authorized focused verification passed with 11
decision-ready tests and 17 market-intelligence tests, 28 combined. The
boundary preserves timestamp/provenance context, remains deterministic and
fail-closed, and produces decision-ready information only. No provider, RPC,
DEX, wallet, AI/ML, trading, execution, persistence, or production
functionality was introduced.

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
- `docs/P02-T06_SPECIFICATION.md`
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

- P02-T04 corrective patch remains complete and verified. P02-T05 and P02-T06
  are complete and verified against their controlled scopes.
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
- P02-T09 is complete and ready for the next officially gated task. Its
  architecture gate passed with the stale-data correction, explicit
  source-event identity/contradiction semantics, deterministic decision-ready
  validation, UNKNOWN-state preservation, and point-in-time provenance intact.
  No future task was started or invented.

## Next action

No automatic next implementation action is selected. P03-T01 is technically
complete and audited. P03-T02 code exists in the repository but remains NOT
AUTHORIZED / NOT formally closed and requires a separate governance decision.
P03-T03 remains NOT AUTHORIZED.

## Next task

P03 is NOT COMPLETE. P03-T01 is implemented, audited, and technically
complete. P03-T02 code exists but is NOT AUTHORIZED / NOT formally closed.
P03-T03 remains NOT AUTHORIZED. Provider connectivity, ingestion transports,
persistence changes, market-state collection, and other later capabilities
require separate specifications and approval.

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
- **P02-T06:** DONE
- **P02-T07:** DONE
- **P02-T08:** DONE
- **P02-T09:** DONE — ARCHITECTURE GATE PASS
- **P03 architecture review:** PASS
- **P03-T01:** IMPLEMENTED — AUDITED — PASS WITH NON-BLOCKING OBSERVATIONS — TECHNICALLY COMPLETE
- **P03-T02:** CODE EXISTS — NOT AUTHORIZED / NOT FORMALLY CLOSED
- **P03-T03:** NOT AUTHORIZED
- **Next implementation action:** None selected automatically; P03-T02 requires a separate governance decision and P03 remains NOT COMPLETE
