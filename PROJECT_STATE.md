# AI ENTRY POINT

**DO NOT SCAN THE FULL REPOSITORY.**

Read `REPLIT_RULES.md` first. Use this file as the authoritative current development state. Then read only the files listed under **Relevant files for current task**.

## Project

- **Project name:** Meme Coin Hunter AI
- **Current phase:** P08 — Outcome Learning
- **Current governed task:** P08 — G2 Realization / Settlement Endpoint Boundary
- **Governed task status:** DISCOVERY COMPLETE / BLOCKED / UNRESOLVED / NOT AUTHORIZED
- **Current integration priority:** P04-LME-03 controlled read-only diagnostic
  orchestration specification
- **Integration priority status:** SPECIFICATION DRAFT COMPLETE / REVIEW
  PENDING / IMPLEMENTATION NOT AUTHORIZED
- **Workflow baseline:** hybrid GitHub + ChatGPT/Codex + Replit workflow and CI
  merged to `main` at `71e0dea`; local verification and GitHub Actions passed
- **Last updated:** 2026-09-21

## Master progress

- P00: DONE; T01 done; T02 done
- P01: T01 done; T02 done; T03 done; T04 done; T05 done
- P02: T01 done; T02 done; T03 done; T04 done; T05 done; T06 done; T07 done; T08 done; T09 done
- P03: T01 implemented, audited, and technically complete; T02 implemented, corrective fix completed, audited / verified, and formally closed; T03 implemented, audited, verified, and formally closed; P03 overall remains not complete
- P04: T01 complete; T02 complete; T03 complete; T04 complete; T05 complete / closed; T06 complete / closed / audited PASS; T07 complete / closed / audited PASS; T08 environment/tooling stabilization complete / closed; P04 overall remains not complete
- P05: T01–T08 COMPLETE; T03–T08 CLOSED / AUDITED PASS (T04 with
  non-blocking observations)
- P06: architecture/specification gate COMPLETE / CLOSED / APPROVED; T01–T02
  COMPLETE / CLOSED / AUDITED PASS; T03 COMPLETE / CLOSED; runtime not started
- P07: architecture gate PASSED; T01–T07 COMPLETE / CLOSED / AUDITED PASS;
  phase COMPLETE / CLOSED / AUDITED PASS
- P08: T01–T07 COMPLETE / CLOSED / AUDITED PASS; G1 limited implementation and
  Authority B COMPLETE / CLOSED / AUDITED PASS; G2 discovery COMPLETE but
  BLOCKED / UNRESOLVED; G2, G3, G4, and P09 NOT AUTHORIZED
- Risk/Capital Authority limited implementation is COMPLETE / CLOSED / AUDITED PASS; G2, G3, G4, and P09 remain NOT AUTHORIZED.
- P07 Risk/Capital admission contract specification is COMPLETE / CLOSED / AUDITED PASS; a separate P07 v2 implementation authorization is required before code may be created. G2, G3, G4, and P09 remain NOT AUTHORIZED.
- P07 v2 Risk/Capital admission implementation is COMPLETE / CLOSED / AUDITED PASS; G2, G3, G4, and P09 remain NOT AUTHORIZED.
- Read-only Market Data Adapter specification is COMPLETE / CLOSED / AUDITED PASS; limited implementation is AUTHORIZED; G2, G3, G4, and P09 remain NOT AUTHORIZED.
- Read-only Market Data Adapter implementation is COMPLETE / CLOSED / AUDITED PASS; G2, G3, G4, and P09 remain NOT AUTHORIZED.

## Phase status

- **Done:** P00 governance map, architecture boundaries, continuation rules, safety and testing principles; P01-T01 technical baseline and minimal runtime; P01-T02 runtime and configuration foundation; P01-T03 persistence foundation; P01-T04 application service and worker foundation; P01-T05 application service and worker extensions; P02-T01 provider-neutral data ingestion and normalization contract; P02-T02 provider-neutral ingestion orchestration and source health boundary; P02-T03 provider-neutral source adapter contract; P02-T04 provider-neutral token universe / discovery contract; P02-T05 discovery-to-orchestration integration boundary; P02-T06 provider-neutral token-universe state / materialization boundary; P02-T07 provider-neutral token-scoped market observation evidence contract; P02-T08 provider-neutral market state materialization boundary; P02-T09 provider-neutral market intelligence boundary — FINAL; P03-T01 token safety evidence and eligibility contract — IMPLEMENTED / AUDITED / PASS WITH NON-BLOCKING OBSERVATIONS / TECHNICALLY COMPLETE; P03-T02 safety evaluation boundary — IMPLEMENTED / CORRECTIVE FIX COMPLETED / AUDITED / VERIFIED / FORMALLY CLOSED; P03-T03 token safety eligibility derivation — IMPLEMENTED / AUDITED / VERIFIED / FORMALLY CLOSED; P04-T01 Signal Evidence Contract — COMPLETE; P04-T02 Signal Evidence Normalization — COMPLETE; P04-T03 Signal Evidence Quality — COMPLETE; P04-T04 Signal Evidence Evaluation — COMPLETE; P04-T05 Signal Evidence Aggregation — COMPLETE / CLOSED; P04-T06 Signal Evidence Snapshot Contract — COMPLETE / CLOSED / AUDITED PASS; P04-T07 Signal Evidence Snapshot History Boundary — COMPLETE / CLOSED / AUDITED PASS; P04-T08 Python Environment Stabilization — COMPLETE / CLOSED; P04-T09 Feature Calculation Snapshot Boundary — COMPLETE / CLOSED; P04-T10 Feature Snapshot History Boundary — COMPLETE / CLOSED / AUDITED PASS; P05-T01 Candidate Boundary — COMPLETE; P05-T02 Normalization / Evidence Contract — COMPLETE; P05-T03 Opportunity Hard-Risk and Disqualification Boundary — COMPLETE / CLOSED / AUDITED PASS; P05-T04 Per-Candidate Feature and Quality Evaluation — COMPLETE / CLOSED / AUDITED PASS WITH NON-BLOCKING OBSERVATIONS; P05-T05 Per-Candidate Opportunity Score (Fast Pre-Score) — COMPLETE / CLOSED / AUDITED PASS
- **In progress:** P04-LME-03 specification review; no implementation,
  scheduler, application wiring, wallet, or trading runtime is authorized
- **Blocked:** G2 realization/settlement endpoint and authoritative provider/source owner decision unresolved
- **On hold:** None
- **Not started:** P06 runtime; later P08 tasks; P09–P12

## Current objective

P07 architecture review has passed, and P07-T01 through P07-T07 are COMPLETE /
CLOSED / AUDITED PASS. P07 is now COMPLETE / CLOSED / AUDITED PASS.

P08-T01 is COMPLETE / CLOSED / AUDITED PASS as the immutable, read-only
outcome observation boundary. P08-T02 is COMPLETE / CLOSED / AUDITED PASS as
the immutable, deterministic, point-in-time dataset snapshot boundary.
P08-T03 is COMPLETE / CLOSED / AUDITED PASS as an evidence-state-only
interpretation boundary. The approved `p08-t03-v1` contract defines the exact
taxonomy, output, provenance, deterministic behavior, and missing-data
semantics. Its runtime implementation is present, verified, and formally
closed under separate implementation authorization.

P08-T04 and P08-T05 are complete, closed, and audited PASS. P08-T06 is the
implemented, immutable, deterministic, non-economic readiness boundary over one
validated P08-T05 snapshot. It emits only
`READY_FOR_NON_ECONOMIC_ANALYSIS` or
`NOT_READY_FOR_NON_ECONOMIC_ANALYSIS`, preserves T05/T02/T04 provenance, and
does not classify economic outcomes or provide authority.

P08-T07 is complete, closed, and audited PASS as the immutable, deterministic,
provider-neutral economic outcome interpretation/assembly boundary. It consumes
validated/materialized G2, G3, and G4 results, preserves their provenance and
digests, returns explicit `VALID`, `NOT_REALIZED`, or `INVALID_INPUT` results,
and does not recompute accounting or classification. No provider, external I/O,
persistence, wallet, signing, execution, or P09 behavior was introduced.

Authority A is recorded as **SPECIFICATION COMPLETE / CLOSED / AUDITED PASS;
IMPLEMENTATION NOT AUTHORIZED**. Its standalone specification audit is recorded
in `docs/P08-AUTHORITY-A-SPECIFICATION-AUDIT.md`. Authority A remains
specification-level only and owns canonical economic subject identity, lifecycle
identity, lifecycle mapping, equivalence, split, and related identity facts
within its documented boundary.

Authority B implementation is COMPLETE / CLOSED / AUDITED PASS as a lineage-only deterministic boundary, confirmed by the formal closure audit in `docs/P08-AUTHORITY-B-CLOSURE-AUDIT.md`. G2, G3, G4, and P09 remain NOT AUTHORIZED.

G1 limited implementation is COMPLETE / CLOSED / AUDITED PASS; G2, G3, G4, and P09 remain NOT AUTHORIZED.

G2 realization/settlement endpoint boundary discovery is COMPLETE as
documentation-only governance discovery, but G2 remains BLOCKED / UNRESOLVED /
NOT AUTHORIZED. An authoritative provider/endpoint or other realization-source
owner decision is required before a G2 specification can be written. The
discovery is recorded in
`docs/P08-G2-REALIZATION-ENDPOINT-BOUNDARY-DISCOVERY.md`. G3, G4, and P09
remain NOT AUTHORIZED.

P07-T05 is the canonical Ledger ↔ State Consistency Verification / paper
reconciliation boundary. It is deterministic, immutable, provider-neutral, and
compares only explicitly supplied immutable P07-T04 ledger entries with one
explicitly supplied expectation or replay observation. It produces an
informational reconciliation result only and does not establish external truth,
settlement, authorization, capital state, wallet state, transaction state, or
live/on-chain state.

The verification boundary preserves explicit UNKNOWN / UNAVAILABLE observation
states, fails closed on unresolved material, preserves provenance and
predecessor identity, uses canonical deterministic representations and SHA-256
digests, and has no wall-clock, provider, network, persistence, wallet,
signing, broadcast, or external-authority dependency. P07-T05 does not
calculate profit, classify WIN/LOSS, calculate ROI, evaluate strategy
performance, authorize capital, execute trades, or perform learning.

P07-T05 reconciliation feeds P07-T06, the immutable canonical finalized
non-economic `PaperSimulationResult`, and P07-T07, the deterministic local
history boundary for validated T06 results. "Finalized" here means that the
validated paper-simulation lifecycle record has been assembled; it does not
mean economic finalization or outcome interpretation. No P07-T08 exists or is
required. P08-T01 consumes one validated P06 decision intent, one validated P07
simulation input, and one linked P07 paper result retained by a P07-T07 history
snapshot. It does not interpret outcomes, aggregate, rank, decide, authorize,
execute, or modify any model or strategy. P08-T03 is closed and no longer
remains an open implementation gate.

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

The owner requested continuation after P04-LME-02 merged. P04-LME-03 is now
defined as a proposed controlled one-shot composition from one current P02-T06
candidate and one exact caller-directed pool target into the existing
P04-LME-02 diagnostic. The draft explicitly preserves caller-owned target
provenance, validates current candidate membership before secret lookup or
network access, and performs no token/pool selection, polling, retry,
persistence, application wiring, paper automation, wallet, or execution.
Implementation remains held for explicit owner acceptance of the specification.

The owner authorized the recommended P04-LME-02 transport and diagnostic step
on 2026-09-21. The approved scope is one server-side read-only request,
environment-secret handling, a one-shot diagnostic composition, mocked/offline
tests, and the timing separation required by a real request. Continuous polling,
application wiring, persistence, wallet, execution, G2, and P09 remain outside
this authorization. Live provider verification has not run because no provider
credential or exact real diagnostic target has been supplied to this task.

The bounded one-attempt transport, environment-secret diagnostic boundary, and
post-receipt evaluation-time correction are implemented. The implementation
uses no new dependency, disables redirects, streams within the caller's size
limit, discards HTTP error bodies, closes responses, and maps expected failures
into existing P04-LME-01 outcomes. Thirty-two new focused tests passed; 133
combined LME tests and 223 targeted/regression tests passed on the available
Python 3.12.14 runtime. Module compilation and `git diff --check` passed. The
locked Python 3.13 full suite, whitespace gate, and TypeScript checks/builds
passed in GitHub Actions run #14. Live provider verification is `NOT RUN`; no
credential value or real target was available.

The owner explicitly approved P04-LME-01 and its limited implementation on
2026-09-21. Authorization covers the two modules, offline fixture, focused
tests, and minimal documentation in section 13. Live provider verification,
application wiring, wallet, execution, G2, and P09 remain unauthorized.

The limited mapper, deterministic price-direction policy, synthetic fixture,
and 101 new offline tests are implemented. Combined targeted/regression checks
passed: 191 tests on the available Python 3.12.14 runtime. The full locked
Python 3.13 suite, workspace TypeScript checks/builds, and repository hygiene
passed in GitHub Actions run #7 for implementation PR #3. `git diff --check`
also passed locally. No live request, new dependency, runtime wiring, wallet,
execution, or G2/P09 functionality was introduced. PR #2 specification was
approved by the owner and merged at `891d2a0`. Implementation PR #3 passed its
final GitHub Actions run and was squash-merged to `main` at `155b50a`.

P04-LME-01 specification completed on 2026-09-21. It selects the CoinGecko
Demo Onchain pool-OHLCV endpoint as the V1 analytical source owner, defines
exact-pool/exact-token closed-candle mapping into P02-T09, and defines the
non-predictive `PRICE_DIRECTION_1M` signal policy. The specification adds no
provider call, dependency, secret, runtime, wallet, execution, G2, or P09
behavior. Its original implementation hold was superseded by the explicit
limited authorization recorded above; live integration remains blocked.

Hybrid workflow hardening was locally verified on 2026-09-21. The full Python
3.13 suite passed with 1,191 tests and one non-blocking dependency warning.
The pnpm 10.28.0 frozen installation, workspace TypeScript typechecks, package
builds with the required non-secret build environment, and `git diff --check`
passed. GitHub Actions passed and PR #1 was squash-merged to `main` at
`71e0dea`.

Limited G1 implementation and real P06 → P07 → P08 fixture-chain verification
were completed on 2026-09-09 against main commit `546ef24`.

Formal Authority B closure audit completed on 2026-09-09. The focused
Authority B suite passed with 21 tests, and all closure criteria passed.

P08-T07 focused tests: 35 passed.
G1 focused tests: 229 passed after verification hardening.
G1 module compile check: passed.
Full project test suite: 769 passed with 1 non-blocking dependency warning.
Python version: 3.13.12.
`git diff --check`: PASS.
G1 implementation closure re-audit completed on 2026-09-10. Former
canonicalization, digest, provenance, duplicate, contradiction, cutoff, replay,
and reason-precedence evidence gaps are closed. The formal re-audit is recorded
in `docs/P08-G1-IMPLEMENTATION-CLOSURE-REAUDIT.md`.
G1 validation preserves predecessor-owned digest contracts, accepts the real
P07-T05 `MATCH` reconciliation status, and preserves the P08-T02 cutoff as a
timezone-aware datetime. No remaining G1 contract mismatch was identified.
No commit or push was performed. `.replit` remains a pre-existing local
workspace change and is excluded from project changes.

P08-T01 through P08-T06 are COMPLETE / CLOSED / AUDITED PASS. P08-T07 is
COMPLETE / CLOSED / AUDITED PASS. G1 limited implementation is COMPLETE /
CLOSED / AUDITED PASS. G2, G3, G4, and P09 remain NOT AUTHORIZED. No later
behavior was introduced.

P08-T01 implementation is present in:
`core/learning/outcome_observation.py`
and
`tests/test_outcome_learning.py`.

P08-T02 implementation is present in:
`core/learning/outcome_dataset.py`
and
`tests/test_outcome_learning_dataset.py`.

P08-T03 governance/discovery is documented in:
`docs/P08-T03-BOUNDARY-DISCOVERY.md`.

P08-T03 specification is documented in:
`docs/P08-T03-SPECIFICATION.md`.

The P07-T07 specification is:
`docs/P07-T07-SPECIFICATION.md`.

The P08-T01 specification is:
`docs/P08-T01-SPECIFICATION.md`.

The implementation remains deterministic, immutable, provider-neutral,
simulation-only, provenance-preserving, and fail-closed. No live execution,
wallet, signing, broadcast, RPC, DEX, provider, network, persistence,
external-authority reconciliation, economic metric, model, or P09
functionality was introduced. P08-T03 remains evidence-state-only.

The candidate-listing integration checkpoint is verified on 2026-09-18. The
read-only inspection artifact now supports an explicit, bounded provider-list
request, preserves provider order plus duplicate, invalid, and missing-identity
entries, and keeps canonical discovery admission `NOT_ADMITTED`. Selecting a
candidate only fills the inspection form; inspection remains explicit. Latest
token profiles are not comprehensive discovery, a newly-created-token feed, or
approved opportunities. Verification uses mocked provider responses and does
not establish live provider correctness; source freshness remains `UNKNOWN` and
P08 acceptance remains `NOT_ATTEMPTED`. No live market requests, analytics,
watchlist, or downstream admission behavior was added.

The token-safety integration checkpoint is verified on 2026-09-19 on branch
`wip/token-safety-integration`. The inspection UI now exposes an explicit
“Check token safety” action only after a successful inspection. The bounded
server-side GoPlus adapter supports the configured EVM chain set, validates and
binds the exact chain/token identity, applies response-size and timeout limits,
and composes documented returned fields through the existing P03 evaluation and
eligibility contracts. The generated API clients and validators are synchronized
with the OpenAPI contract. Risk flags fail closed; favorable, missing,
unsupported, and undocumented evidence remains `UNKNOWN`/unavailable rather
than becoming positive evidence. Undocumented `is_freezable` is ignored, and
the UI states that freeze-authority evidence remains incomplete. Stale UI
responses are rejected after input identity changes. Focused verification
passes 57 Python safety/contract tests, 38 API tests, and the Chromium-backed
mocked frontend interaction test, plus API/frontend typechecks and builds with
the required workflow environment. Verification uses mocked provider responses;
no live GoPlus request, wallet, trading, ranking, analytics, commit, push, or
merge was performed.

The opportunity-evaluation integration checkpoint is verified on 2026-09-19 on
branch `wip/opportunity-evaluation-integration`. The inspection UI now exposes
an explicit per-pair admission-diagnostic action only after both held reports
are available; it does not evaluate automatically, request another provider
report, rank pairs, create a score, admit a token, or authorize trading. The
API preserves exact chain/token/pair/market-subject identity, rejects a pair
whose token is not represented on either side, preserves receipt versus source
observation timestamps, and reports explicit missing P04/P05 canonical-input
blockers. Its bounded safety diagnostic bridge invokes the existing Python
P03 evaluation and eligibility functions; the qualifying fixture path reaches
those evaluators in focused tests and in the built API verification. The
default bridge was exercised through the running `POST
/api/opportunity-evaluations` endpoint with a generated-schema-valid offline
fixture, using the repository root as the Python working directory. It
returned HTTP 200 with a structured `BLOCKED` admission diagnostic,
`P03_ELIGIBILITY_UNKNOWN`, unavailable P04/P05 blockers, and zero provider
requests. The live API remains intentionally blocked as an admission
diagnostic because its request contract does not carry the canonical P04
signal and feature snapshots required by P05. The generated API clients are
synchronized with OpenAPI. Verification passes 43 API tests, the
Chromium-backed mocked frontend interaction test, API/frontend typechecks and
builds with the required workflow environment, and 130 focused Python safety
and opportunity tests. The frontend build retains only the existing
`tooltip.tsx` sourcemap warning. No live provider request, wallet, trading,
ranking, analytics, commit, push, or merge was performed.

The canonical P04-to-P05 composition checkpoint is implemented as a
provider-neutral, deterministic assembly boundary. It constructs P04-T06
signal and P04-T10 feature snapshots from already-validated upstream results,
then invokes the existing P05-T01 candidate, P05-T02 normalization, P05-T03
hard-risk, P05-T04 feature-evaluation, and P05-T05 score functions. The
qualifying test-only fixture reaches `ELIGIBLE` and produces the existing
P05-T05 score `80.55555555555555555555555556` while preserving candidate
identity, upstream representation digests, snapshot provenance, and the
reference timestamp. Missing evidence, UNKNOWN/INELIGIBLE safety, identity
mismatch, invalid time ordering, malformed numbers, and altered digests fail
closed through the existing contracts.

The application endpoint remains diagnostic-only and does not accept
browser-supplied eligibility, self-computed digests, or test fixtures. It
continues to report blocked P04/P05 canonical-input blockers when those
inputs are absent. Remaining live-data blockers are unchanged: the backend
does not yet receive trusted canonical P04 signal/feature inputs from an
authorized upstream producer, and G2 realization/settlement remains blocked
pending the authoritative provider/source owner decision.

The canonical evidence producer is implemented on `main` at commit `2d32397`.
It consumes already-admitted P02-T09
market-intelligence observations and P04-T01 signal evidence, invokes the
existing P04-T02 normalization, P04-T03 quality, P04-T04 evaluation,
P04-T05 aggregation, and P04-T09 price-feature functions, then passes their
outputs into the existing P04-T06/P04-T10 and P05-T01 through P05-T05 chain.
The qualifying offline path uses three explicitly historical price
observations, preserves observation versus receipt timestamps and P02 state
digests, and reaches the existing score of
`80.55555555555555555555555556`.

The producer does not derive signal types or statuses from market data because
the repository has no approved market-to-signal policy or source-authentication
mapping for that decision. Its live application connection therefore remains
blocked: DexScreener inspection is source-shaped/read-only and GoPlus safety
is not market evidence; neither supplies the complete authenticated historical
price, signal-policy, and source-time linkage required for P04. The next
concrete requirement is an authoritative producer that supplies those fields
and an approved mapping from them to P04-T01 signal evidence.

P07-T01 through P07-T07 are recorded as COMPLETE / CLOSED / AUDITED PASS.
P07 is COMPLETE / CLOSED / AUDITED PASS. No P07-T08 specification or task
exists.
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
- `.github/workflows/ci.yml`
- `docs/HYBRID_DEVELOPMENT_WORKFLOW.md`
- `docs/P04-LME-01-LIVE-MARKET-EVIDENCE-SPECIFICATION.md`
- `docs/P04-LME-02-TRANSPORT-DIAGNOSTIC-SPECIFICATION.md`
- `docs/P04-LME-03-CONTROLLED-ORCHESTRATION-SPECIFICATION.md`
- `core/data/coingecko_onchain_ohlcv.py`
- `core/data/coingecko_onchain_transport.py`
- `core/data/coingecko_onchain_diagnostic.py`
- `core/signals/price_direction_policy.py`
- `core/data/market_observations.py`
- `core/data/market_state.py`
- `core/data/market_intelligence.py`
- `core/opportunity/canonical_evidence_producer.py`
- `tests/test_coingecko_onchain_ohlcv.py`
- `tests/test_price_direction_policy.py`
- `tests/test_coingecko_onchain_transport.py`
- `tests/test_coingecko_onchain_diagnostic.py`
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
- `docs/P07-T05-SPECIFICATION.md`
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

Review and explicitly accept or revise the P04-LME-03 field-level contract.
Runtime code must not begin before that approval. Keep live provider
verification recorded as `NOT RUN`.

## Next task

After approval, the next limited implementation may add only the controlled
one-shot orchestration module, its mocked/offline tests, minimal exports, and
documentation synchronization. Continuous polling, application wiring, and
paper automation require later specifications and authorization. G2 remains
blocked; P09 remains unauthorized.

 Only the implementation
files explicitly approved by the P07-T01 specification were created:
`core/execution/paper_simulation_input.py`,
`core/execution/__init__.py`, and
`tests/test_paper_simulation_input.py`.

P07-T02 specification and implementation are COMPLETE / CLOSED / AUDITED PASS.

The P07-T02 implementation was limited to the explicitly authorized files:
`core/execution/paper_fill_outcome.py`
and `tests/test_paper_fill_outcome.py`.

The implementation was verified as deterministic, provider-neutral,
simulation-only, fail-closed, immutable, provenance-preserving, and independent
from position mutation, ledger, reconciliation, Risk/Capital Authorization,
and live execution.

Focused P07-T02 tests: 19 passed.
Full project test suite: 574 passed with 1 non-blocking dependency warning.
Direct negative-latency contract probes: all passed.
`git diff --check`: passed.

P07-T03 specification, implementation, and final governance audit are
COMPLETE / CLOSED / AUDITED PASS. P07-T03 focused tests: 18 passed; P07-T02
regression: 19 passed; full project test suite: 592 passed with one
non-blocking dependency warning; `git diff --check`: passed. FIX #4 and FIX #5
are resolved. P07-T02 remains untouched, no forbidden scope was added, and
P07-T04 implementation and final audit are COMPLETE / CLOSED / AUDITED PASS.

No position, exposure, ledger, reconciliation, provider, network, wallet,
signing, broadcast, live execution, or P09 work is authorized. No later P08
task is authorized.

P04 overall remains NOT COMPLETE; any future P04 signal task requires a
separate specification and approval. Provider connectivity, ingestion
transports, persistence changes, market-state collection, and later phases
require separate specifications and approval.

## Required secret names

No secret values are stored here. Future integrations must use environment
secrets; names will be added only when a later task requires them.
The token-safety adapter optionally reads `GOPLUS_ACCESS_TOKEN` server-side when
the provider requires authentication; no value is present in this workspace.

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
