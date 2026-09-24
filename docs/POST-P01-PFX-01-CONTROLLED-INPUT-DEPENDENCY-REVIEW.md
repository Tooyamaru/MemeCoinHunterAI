# Post-P01-PFX-01 bounded controlled-input dependency review

**Status:** DEPENDENCY REVIEW COMPLETE / DOCUMENTATION ONLY

**Baseline:** P01-PFX-01 COMPLETE / CLOSED / CI PASS; P01-OSC-02 and P07-PFS-01 COMPLETE / CLOSED / CI PASS.

## Question and exact terminals

Can one already-materialized PFX-01 result plus one already-materialized PFS-01 result and explicit RTI-15 paper inputs form exactly one OSC-02-ready request without executing any owner again?

- PFX-01 `PREFIX_MATERIALIZED` preserves an **exact** RTI-14 result (APPROVED or REJECTED), with nested exact RTI-13 → RTI-12 → RTI-11. It has no RTI-15/16, PFS, or OSC calls.
- PFS-01 `FACTS_MATERIALIZED` preserves exact `PaperFillInstruction`, `PaperLifecycleEvidence`, `InitialPaperStateIdentity`, selected historical source and simulation-policy provenance. Its exact request retains `ExecutionObservation`, `SimulationConfigurationIdentity`, `ReplayIdentity`, reference/evaluation times, selected RTI-11 result, and explicit policy. It has no downstream calls.
- OSC-02 requires `invocation_id`, exact RTI-14, those four RTI-15 inputs (execution, configuration, initial state, replay), and exact fill/lifecycle evidence. OSC-02 itself owns one RTI-15 and one RTI-16 delegation and stops at RTI-16.

## Dependency finding

The missing boundary is **thin, deterministic application composition of already-produced outputs**, not a new source of market/fill facts or another decision/risk owner. There is no requirement to rerun RTI-11/12/13/14, PFS, or OSC-02 to prepare the request. An exact, approved PFX prefix and exact PFS products suffice when all cross-lineage/time/scope checks pass. They do **not** guarantee RTI-15 admission or RTI-16 lifecycle materialization: canonical owners retain those decisions.

The controller must still explicitly supply or obtain the canonical RTI-11 result; select the candidate and exact pool; supply the PFX policy seed, ruleset and decision time; specify PFS historical observation and full simulation policy; supply canonical execution/configuration/replay inputs and initial-state declaration where applicable; and choose an OSC invocation ID. No adapter may synthesize these facts.

## Required cross-checks before an OSC-02 request

1. Revalidate both exact result digests/outcomes and predecessor object identities. PFS.request.rti11_result must be the **same exact object** as PFX.request.rti11_result and nested RTI-14 → RTI-13 → RTI-12 → RTI-11 predecessor. Candidate/chain/token/exact pool and source observation must remain those of this one RTI-11 result.
2. PFX must have `PREFIX_MATERIALIZED`, exact RTI-14 `AUTHORIZATION_MATERIALIZED`, authorization `APPROVED` with paper-only effect. A canonical REJECTED prefix is valid PFX output, but cannot form an experiment case for OSC-02. PFS must have `FACTS_MATERIALIZED` with all three exact products; refusal/unavailable cannot be repaired or defaulted.
3. Bind PFX policy snapshot/authorization `simulation_reference_time` to PFS request's explicit simulation reference; check source close/receipt and simulated fill/evaluation times against canonical admission and lifecycle timing. Preserve PFS USD historical close solely as a simulation price proxy.
4. Pass exact PFS.request.execution_observation, simulation_configuration and replay_identity, exact PFS.result.initial_state_identity, fill_instruction and lifecycle_evidence. Check execution subject, replay/ledger stream, portfolio/state scope and policy references against PFX decision/authorization and PFS products. Do not reconstruct either paper fact.
5. Validate the complete `P01Osc02Request` using its existing constructor once. Do not construct a P07 `PaperSimulationInput`, pre-run RTI-15/16, invoke OSC-02, or infer owner outcomes.

Identity/time/version/digest mismatch or tampering is validation failure, not an ordinary non-admission. Explicit PFX stop/rejection and PFS refusal can be represented as finite non-ready outcomes; no later owner is invoked. Unexpected construction failure must be bounded without a retry or substitute. Same exact inputs yield the same deterministic request/case digest; an in-memory digest does not constitute persistent replay archive or idempotent durable execution.

## Architecture and STOP

A separately approved input-preparation gate may accept both already-produced canonical results and one explicit invocation ID, check compatibility, and return the **exact canonical `P01Osc02Request` in memory**. Its owner delegation cardinality is zero for PFX, PFS, RTI-11–16, OSC-01/02 and RTI-03/04. OSC-02 runs only on a later explicit invocation; persistence is separate.

This review authorizes no runtime implementation, provider polling, autonomous selection, retry/loop, worker/scheduler/queue, API/dashboard, wallet/signing/RPC/DEX, economic realization, execution/live trading, G2, G3, G4 or P09. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.
