# P01-OSC-01 — Explicit-Input One-Shot Controlled Paper Caller

**Status:** SPECIFICATION COMPLETE / READY FOR CONTROLLER REVIEW / IMPLEMENTATION NOT AUTHORIZED

**Proposed contract:** `p01-osc-01-v1` (proposed; no runtime contract exists yet)

**Baseline:** GitHub `main` `ad3368ab23b6ca075ac53406ee5c884e6cea215a`, post-RTI-16 review merged in PR #44. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.

## 1. Bounded dependency and entry-point selection

The post-RTI-16 review established a natural STOP for the in-memory *composition chain*, not an operational caller. Controller direction D now asks for one explicit invocation. RTI-11 is the existing entry for caller-directed market diagnostics, but `MarketToOpportunityCompositionService.compose` delegates to a controlled OHLCV diagnostic with environment/transport seams. Calling it here would violate the no-live-provider rule. Its **already-produced canonical** `P01Rti11CompositionResult` is therefore the earliest eligible explicit input. RTI-12 owns continuation from that exact type; RTI-13–16 each own the next handoff. No domain owner is missing between them.

RTI-04 `ControlledPaperRunService.run` is a different one-request coordinator starting at P05-T08 and mandatorily invoking RTI-01, RTI-02, then RTI-03 persistence. It cannot consume the RTI-11–16 chain and would recompute closed owners. RTI-16 itself accepts RTI-15 only; it does not coordinate earlier results. Thus a distinct application-level invocation coordinator is justified, but **no new decision, risk, admission, fill, lifecycle, market, or persistence owner** is authorized. The identifier `P01-OSC-01` (one-shot caller) distinguishes this operational invocation policy from an artificial RTI-17 domain continuation.

## 2. Exact entry and caller-supplied request

Future single public HTTP-independent application entry point: `OneShotControlledPaperCaller.run(request: P01Osc01Request) -> P01Osc01Result`. It is invoked once by an explicit in-process controller with a complete immutable request; this specification does not authorize a CLI, HTTP route, startup hook, or other concrete transport. Dependency injection for focused testing conveys no caller authority.

The request has exactly the following required fields, with no implicit default:

| Field | Canonical type / meaning |
| --- | --- |
| `invocation_id` | Caller-assigned 1–128 ASCII `[A-Za-z0-9._:-]` identity; no whitespace; correlation only, never derived from clock/token/digest |
| `rti11_result` | Already-produced exact `P01Rti11CompositionResult`, including its original request, diagnostic and composition where present |
| `decision_ruleset` | Exact canonical P06 `DecisionEvaluationRuleset` |
| `decision_time` | Explicit timezone-aware `datetime`, respecting RTI-13 contextual time constraints |
| `policy_snapshot` | Exact canonical `PaperRiskCapitalPolicySnapshot` |
| `execution_observation` | Exact canonical `ExecutionObservation` |
| `simulation_configuration` | Exact canonical `SimulationConfigurationIdentity` |
| `initial_paper_state` | Exact canonical `InitialPaperStateIdentity` |
| `replay_identity` | Exact canonical `ReplayIdentity` |
| `fill_instruction` | Exact canonical RTI-02 `PaperFillInstruction` |
| `lifecycle_evidence` | Exact canonical RTI-02 `PaperLifecycleEvidence` |

The caller owns prior construction and availability of **all** market, P03, signal, P05, policy, risk, observation, quote/fill, ledger, expectation, and lifecycle facts embedded in those canonical objects. The coordinator accepts no raw market facts in place of RTI-11, no secret, provider client, environment mapping, clock, history store, database handle, or automatic token/pool selection. It cannot manufacture an RTI-11 result or treat a digest alone as replay input. A caller must obtain a canonical RTI-11 result separately under its own authority; this gate grants no provider invocation to do so.

## 3. Preflight validation, identity and provenance

Before **any** owner delegation and before examining any outcome, validate the exact request type, closed field set, `p01-osc-01-v1`, invocation ID, and each exact supported canonical owner type/version by the owners' reconstruction/digest rules. Reject missing/malformed/tampered input, noncanonical time, structural mismatch, or incompatible identities as standardized `ValueError`; no ordinary bounded outcome and no partial owner work. Validate explicit fields even when RTI-11 is non-`COMPOSED`.

Check linkable identity/time constraints among RTI-11 target, candidate/context, policy subject, execution observation, state, replay, fill, and lifecycle evidence **using existing owner invariants**; never infer identity from ticker/symbol or invent a new cross-domain identity rule. Some links require an intermediate result; validate immediately after its production and before the next delegate. Preserve exact nested object references and owner digests. `invocation_id` is application correlation and shall be bound in the outer result digest but shall not enter any P05/P06/Risk/Capital/P07/P08 or RTI-11–16 canonical digest. Reusing an ID with different inputs is caller misuse; with no storage, this gate cannot enforce global uniqueness or exactly-once delivery across separate calls.

## 4. Delegation and stopping semantics

Within one invocation, the coordinator calls **only** the following owners, in order, each at most once, passing the exact preceding result and explicit fields unchanged:

1. `P05OpportunityContextContinuationService.continue_to_context(rti11_result)` (RTI-12) only when RTI-11 is canonical `COMPOSED`; otherwise return `UPSTREAM_STOPPED`, preserving RTI-11.
2. `OpportunityContextToDecisionContinuationService.continue_to_decision(rti12, decision_ruleset, decision_time)` only for `CONTEXT_MATERIALIZED`.
3. `DecisionToRiskCapitalContinuationService.continue_to_risk_capital(rti13, policy_snapshot)` only for `DECISION_MATERIALIZED`.
4. `RiskCapitalToPaperAdmissionContinuationService.continue_to_paper_admission(rti14, execution_observation, simulation_configuration, initial_paper_state, replay_identity)` only for `AUTHORIZATION_MATERIALIZED` with the existing canonical approved paper-only authority. A materialized `REJECTED` is a valid authority result and stops here; do not ask RTI-15 to represent a new rejection.
5. `Rti15ToControlledPaperLifecycleContinuationService.continue_to_controlled_paper_lifecycle(rti15, fill_instruction, lifecycle_evidence)` only for `ADMISSION_MATERIALIZED`.

At each stage a canonical non-progress or unavailable outcome stops with `UPSTREAM_STOPPED`, retaining the exact last produced result, its reasons, and preceding result chain. Neither the coordinator nor RTI-04 invokes RTI-01, P05/P06/Risk/Capital/P07/RTI-02 directly; those domain delegations occur only inside the relevant canonical owner. RTI-16 alone constructs its RTI-01-compatible envelope and calls RTI-02 once. No owner previously executed in this invocation is rerun. No automatic retry, alternate branch, fallback, or compensating invocation is allowed.

## 5. Result, failure and deterministic contract

An immutable outer `P01Osc01Result` shall contain contract version, exact `invocation_id`, one closed outcome (`LIFECYCLE_RETURNED`, `UPSTREAM_STOPPED`, `OWNER_UNAVAILABLE`), canonical bounded reason codes, exact `rti11_result`, optional exact stage results `rti12_result` through `rti16_result` in prefix order, `terminal_stage`, and deterministic `result_digest`. `LIFECYCLE_RETURNED` requires RTI-16 `LIFECYCLE_MATERIALIZED` and exposes the exact nested `ControlledPaperLifecycleResult`, its own authoritative RTI-02 outcome and digest, unchanged. The outer outcome does not claim fill success, reconciliation match, persistence, realized value, or trading.

Canonical stage unavailable outcomes are `UPSTREAM_STOPPED` with exact owner reason codes; unexpected non-`ValueError` delegate exceptions or invalid owner outputs yield `OWNER_UNAVAILABLE` with a finite stage-specific reason, no fabricated later result, no raw exception. Owner `ValueError` (including RTI-16 validation) remains a standardized validation failure and is **never** converted into an ordinary result. Cancellation propagates and never retries. Results may include only stages actually reached; no synthetic upstream result is permitted.

The outer digest uses a versioned canonical representation binding invocation ID, outcome/reasons, terminal stage, and, for every present RTI-11–16 result, its exact contract version, outcome and digest, plus canonical digests of each explicit caller input. It excludes wall time, process state, provider/environment, logger, mutable state, and exception text. Identical canonical inputs with equivalent canonical owner results yield identical outer results and digest; `invocation_id` differences yield different outer digests. This in-memory guarantee is not durable idempotency. All objects retain the nested provenance, including RTI-16 compatibility admission, fill/evidence and exact RTI-02 result; no reconstructed market or economic provenance is claimed.

## 6. Hard STOP and governance

The exact terminal boundary is the in-memory canonical RTI-16 result and, on success, its exact nested `ControlledPaperLifecycleResult`. No RTI-03 write or RTI-04 run occurs. Lifecycle-only persistence B and full lineage/replay persistence C require separate controller gates. There is no API/dashboard/publication, discovery/provider polling or loop, hidden input construction, scheduler, worker/queue, recurring invocation, wallet/signing, RPC/DEX, execution, economic realization, or live trading. G2 stays BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 stay NOT AUTHORIZED.

Specification checkpoint changes documentation/governance only. Future implementation needs explicit controller authorization and focused evidence for preflight failure before delegation, exact once per stage, all canonical stops, rejected Risk/Capital behavior, tampering, digest continuity, and no RTI-04/RTI-03 or provider access.
