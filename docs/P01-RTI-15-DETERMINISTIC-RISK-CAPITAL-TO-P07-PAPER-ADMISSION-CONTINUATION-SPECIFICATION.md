# P01-RTI-15 — Deterministic Risk/Capital-to-P07 Paper Admission Continuation

**Status:** COMPLETE / CLOSED / CI PASS

**Contract:** `p01-rti-15-v1`

## Purpose

Consume exactly one canonical `P01Rti14RiskCapitalContinuationResult` plus
explicit caller-owned `ExecutionObservation`, `SimulationConfigurationIdentity`,
`InitialPaperStateIdentity`, and `ReplayIdentity`. Continue only an exact
materialized `APPROVED` paper-only authorization through the existing
authorization-observation adapter and P07-T01 v2 constructor, then stop at the
exact `PaperSimulationInput`.

## Authority and dependency boundary

| Concern | Owner | RTI-15 permission |
| --- | --- | --- |
| Decision and Risk/Capital result | RTI-13/14 and existing authority | Validate/pass only |
| Authorization observation | `AuthorizationObservation.from_risk_capital_result` | Delegate once |
| P07 admission | `PaperSimulationInput` (`p07-t01-v2`) | Construct once with exact facts |
| Fill/state/ledger/lifecycle | P07-T02 onward / RTI-02 | Prohibited |
| Economic truth/execution | G2/G3/G4/P09 | Blocked/prohibited |

## Exact flow

Only `AUTHORIZATION_MATERIALIZED` with exact `status == APPROVED` and effect
`PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY` continues:

1. exact authority result → `AuthorizationObservation.from_risk_capital_result`
   exactly once;
2. require exact PASS observation and canonical authorization reference;
3. exact RTI-13 `DecisionIntent`, observation, caller facts, and authority
   `simulation_reference_time` → `PaperSimulationInput` exactly once with
   contract `p07-t01-v2`;
4. require exact object identity, version, provenance, and digest linkage;
5. return exact input and stop.

No alias fallback or retry is permitted.

## Outcomes and failures

| Condition | Outcome/behavior |
| --- | --- |
| Approved authorization and valid P07 input | `ADMISSION_MATERIALIZED` |
| RTI-14 non-materialized or canonical REJECTED authority | `UPSTREAM_NOT_AUTHORIZED`; no adapter/P07 call |
| Unexpected adapter/P07 exception or invalid return | `ADMISSION_UNAVAILABLE` with finite stage code |
| Malformed/tampered/version/identity input, adapter `ValueError`, P07 `ValueError` | Safe standardized `ValueError`; not a semantic outcome |

Finite unavailable reasons are
`AUTHORIZATION_OBSERVATION_UNAVAILABLE`,
`AUTHORIZATION_OBSERVATION_INVALID_RESULT`, `P07_ADMISSION_UNAVAILABLE`, and
`P07_ADMISSION_INVALID_RESULT`. Raw exception content is excluded.

## Determinism and canonical digest

The lowercase SHA-256 wrapper digest binds only canonical JSON fields:

- RTI-15 contract/outcome/reasons;
- RTI-14 contract/outcome/result digest;
- authority status/result digest;
- execution observation, simulation configuration, initial state, and replay
  identity digests;
- authorization observation digest; and
- P07 contract/input digest.

Sorted keys, compact separators, `ensure_ascii=True`, and UTF-8 are required.
No clock, environment, callable identity, exception detail, object address,
filesystem/dictionary order, or shared mutable state participates.

## Identity and provenance

Preserve exact DecisionIntent, authorization id/digest/effect/scope, policy
lineage, authorization reference, execution observation, configuration,
initial state, replay identity, timestamps, and P07 input digest. Do not infer,
repair, clone, recalculate, upgrade, downgrade, or synthesize them.

## STOP and forbidden boundary

Stop at `PaperSimulationInput`. No provider/network, runtime caller, API,
worker/scheduler/queue, fill evaluation, position mutation, ledger,
reconciliation, paper lifecycle, persistence/publication, P08 learning/economic
path, G2/G3/G4, P09, dashboard, wallet, signing, RPC/DEX, execution, or live
trading is authorized.

## Focused verification

Tests must prove approved success, rejected/non-materialized stop behavior,
safe validation, unexpected and invalid owner results, exact once-only calls,
version/identity/provenance continuity, deterministic digest, no retry, no
shared state, and forbidden-import/call unreachability. Relevant RTI-13/14,
Risk/Capital, P07-T01, RTI combined, full Python, compilation, TypeScript, and
whitespace checks must pass.

## Expected files

- `backend/application/risk_capital_to_paper_admission_continuation.py`
- `tests/test_risk_capital_to_paper_admission_continuation.py`
- minimal application export
- this specification, gap review, `PROJECT_STATE.md`, and `docs/CHANGELOG.md`

No model, migration, repository/session, dependency, route, config, secret, or
runtime caller may be added.

## Local implementation checkpoint

The authorized module, focused tests, and minimal export are implemented.
Focused tests pass 17/17; relevant RTI-13/14, Risk/Capital, and P07 tests pass
95/95; combined RTI regression passes 217/217; full Python regression passes
1601 tests with one existing dependency warning. Compilation, TypeScript
typecheck/build, and whitespace checks pass. GitHub PR/CI and closure remain
pending.
