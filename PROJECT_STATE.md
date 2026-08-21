# AI ENTRY POINT

**DO NOT SCAN THE FULL REPOSITORY.**

Read `REPLIT_RULES.md` first. Use this file as the authoritative current development state. Then read only the files listed under **Relevant files for current task**.

## Project

- **Project name:** Meme Coin Hunter AI
- **Current phase:** P07 — Paper Trading Engine
- **Current task:** P07 specification
- **Current task status:** SPECIFICATION READY FOR ARCHITECTURE REVIEW — IMPLEMENTATION NOT AUTHORIZED
- **Last updated:** 2026-08-21

## Master progress

- P00: DONE; T01 done; T02 done
- P01: T01 done; T02 done; T03 done; T04 done; T05 done
- P02: T01 done; T02 done; T03 done; T04 done; T05 done; T06 done; T07 done; T08 done; T09 done
- P03: T01 implemented, audited, and technically complete; T02 implemented, corrective fix completed, audited / verified, and formally closed; T03 implemented, audited, verified, and formally closed; P03 overall remains not complete
- P04: T01 complete; T02 complete; T03 complete; T04 complete; T05 complete / closed; T06 complete / closed / audited PASS; T07 complete / closed / audited PASS; T08 environment/tooling stabilization complete / closed; P04 overall remains not complete
- P05: T01 COMPLETE; T02 COMPLETE; T03 COMPLETE / CLOSED / AUDITED PASS; T04 COMPLETE / CLOSED / AUDITED PASS WITH NON-BLOCKING OBSERVATIONS; T05 COMPLETE / CLOSED / AUDITED PASS; T06 COMPLETE / CLOSED / AUDITED PASS; T07 COMPLETE / CLOSED / AUDITED PASS; T08 COMPLETE / CLOSED / AUDITED PASS; P06 ARCHITECTURE / SPECIFICATION GATE COMPLETE / CLOSED / APPROVED; P06-T01 COMPLETE / CLOSED / AUDITED PASS; P06-T02 COMPLETE / CLOSED / AUDITED PASS; P06-T03 COMPLETE / CLOSED; P07 SPECIFICATION PREPARED — IMPLEMENTATION NOT AUTHORIZED; P06 runtime and P07–P12 not started

## Phase status

- **Done:** P00 governance map, architecture boundaries, continuation rules, safety and testing principles; P01-T01 technical baseline and minimal runtime; P01-T02 runtime and configuration foundation; P01-T03 persistence foundation; P01-T04 application service and worker foundation; P01-T05 application service and worker extensions; P02-T01 provider-neutral data ingestion and normalization contract; P02-T02 provider-neutral ingestion orchestration and source health boundary; P02-T03 provider-neutral source adapter contract; P02-T04 provider-neutral token universe / discovery contract; P02-T05 discovery-to-orchestration integration boundary; P02-T06 provider-neutral token-universe state / materialization boundary; P02-T07 provider-neutral token-scoped market observation evidence contract; P02-T08 provider-neutral market state materialization boundary; P02-T09 provider-neutral market intelligence boundary — FINAL; P03-T01 token safety evidence and eligibility contract — IMPLEMENTED / AUDITED / PASS WITH NON-BLOCKING OBSERVATIONS / TECHNICALLY COMPLETE; P03-T02 safety evaluation boundary — IMPLEMENTED / CORRECTIVE FIX COMPLETED / AUDITED / VERIFIED / FORMALLY CLOSED; P03-T03 token safety eligibility derivation — IMPLEMENTED / AUDITED / VERIFIED / FORMALLY CLOSED; P04-T01 Signal Evidence Contract — COMPLETE; P04-T02 Signal Evidence Normalization — COMPLETE; P04-T03 Signal Evidence Quality — COMPLETE; P04-T04 Signal Evidence Evaluation — COMPLETE; P04-T05 Signal Evidence Aggregation — COMPLETE / CLOSED; P04-T06 Signal Evidence Snapshot Contract — COMPLETE / CLOSED / AUDITED PASS; P04-T07 Signal Evidence Snapshot History Boundary — COMPLETE / CLOSED / AUDITED PASS; P04-T08 Python Environment Stabilization — COMPLETE / CLOSED; P04-T09 Feature Calculation Snapshot Boundary — COMPLETE / CLOSED; P04-T10 Feature Snapshot History Boundary — COMPLETE / CLOSED / AUDITED PASS; P05-T01 Candidate Boundary — COMPLETE; P05-T02 Normalization / Evidence Contract — COMPLETE; P05-T03 Opportunity Hard-Risk and Disqualification Boundary — COMPLETE / CLOSED / AUDITED PASS; P05-T04 Per-Candidate Feature and Quality Evaluation — COMPLETE / CLOSED / AUDITED PASS WITH NON-BLOCKING OBSERVATIONS; P05-T05 Per-Candidate Opportunity Score (Fast Pre-Score) — COMPLETE / CLOSED / AUDITED PASS
- **In progress:** None
- **Blocked:** None
- **On hold:** None
- **Not started:** P06 runtime; P07 implementation; P08–P12

## Current objective

P07 specification is prepared and ready for architecture review. It defines
provider-neutral, reproducible paper simulation after P06 and independent Risk
/ Capital Authorization, with no live execution, wallet, signing, broadcast,
RPC, DEX, provider, persistence, or P08/P09 implementation authority.

P06-T02 is COMPLETE / CLOSED / AUDITED PASS as the deterministic evaluation
boundary, and P06-T03 is COMPLETE / CLOSED as an optional non-authoritative
bounded analysis record. T02 consumes exactly one validated P05-T08
OpportunityContext, applies an immutable versioned ruleset, and produces one
P06-T01 DecisionIntent with fail-closed thresholds and preserved provenance. It adds no ranking,
authorization, execution, wallet, RPC, DEX, signing, broadcast, or LLM
behavior. P06-T01 is COMPLETE / CLOSED / AUDITED PASS as the immutable,
deterministic, provider-neutral Decision Intent contract. P05-T05 is COMPLETE /
CLOSED / AUDITED PASS as the deterministic,
provider-neutral, pure per-candidate opportunity pre-score boundary. It consumes
one validated P05-T04 evaluation and the authorized versioned ruleset, preserves
feature and provenance context, and performs no ranking, decision, authorization,
execution, AI, or external I/O. P05-T06 is COMPLETE / CLOSED / AUDITED PASS as
the evidence-first opportunity-record boundary. P05-T07 and P05-T08 preserve
that context without adding decisions. The P06 architecture/specification gate
is closed and no subsequent P06 task is authorized yet; any next boundary
requires its own specification and explicit approval.

## Last verified checkpoint

P06-T02 final boundary verification completed on 2026-08-21.
P06-T01 and P06-T02 are COMPLETE / CLOSED / AUDITED PASS. P06-T03 is COMPLETE /
CLOSED and does not alter T02 authority. P05-T06, P05-T07,
and P05-T08 remain COMPLETE / CLOSED / AUDITED PASS after the evidence-first
revisions.
P05-T04 remains COMPLETE / CLOSED / AUDITED PASS WITH NON-BLOCKING OBSERVATIONS.

No provider, network, persistence, AI, wallet, trading, execution, or production
functionality was introduced. P04-T08 changed only Python environment/tooling
control; it did not define or start a new P04 signal boundary. Any next P04
signal task requires a separate specification and approval.
P03-T01 remains implemented, audited, and technically complete. P03-T02
remains implemented, audited / verified, and formally closed. P03-T03 is
implemented, audited, verified, and formally closed. P03 overall remains not
complete.

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
- `core/risk/safety_evidence.py`
- `core/risk/safety_evaluation.py`
- `core/risk/safety_eligibility.py`
- `tests/test_token_safety.py`
- `tests/test_safety_evaluation.py`
- `tests/test_safety_eligibility.py`
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

P07 specification is prepared and requires architecture review before any
implementation. The review must confirm the paper-simulation boundary,
Risk/Capital Authorization dependency boundary, paper-state and ledger
identity semantics, deterministic friction/fill/failure rules, persistence
boundary, and verification plan. No P07 runtime implementation is authorized
until that review passes.

## Next task

P07 architecture review is the next authorized governance action. No P07
runtime implementation, database change, provider integration, wallet,
signing, broadcast, live execution, P08 learning, or P09 execution work is
authorized until the P07 specification is approved and the first P07
implementation boundary receives its own explicit authorization.
P04 overall remains NOT COMPLETE; any future P04 signal task requires a
separate specification and approval. Provider connectivity, ingestion
transports, persistence changes, market-state collection, and later phases
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
- **P03-T02:** IMPLEMENTED — CORRECTIVE FIX COMPLETED — AUDITED / VERIFIED — FORMALLY CLOSED
- **P03-T03:** IMPLEMENTED — AUDITED — VERIFIED — FORMALLY CLOSED
- **P04-T01:** COMPLETE — Signal Evidence Contract
- **P04-T02:** COMPLETE — Signal Evidence Normalization
- **P04-T03:** COMPLETE — Signal Evidence Quality
- **P04-T04:** COMPLETE — Signal Evidence Evaluation
- **P04-T05:** COMPLETE / CLOSED — Signal Evidence Aggregation
- **P04-T06:** COMPLETE / CLOSED / AUDITED PASS — Signal Evidence Snapshot Contract
- **P04-T07:** COMPLETE / CLOSED / AUDITED PASS — Signal Evidence Snapshot History Boundary
- **P04-T08:** COMPLETE / CLOSED — Python Environment Stabilization; no P04 signal boundary was added
- **Next implementation action:** No later P04 signal task is defined in the current architecture; any next P04 signal task requires separate specification and approval
