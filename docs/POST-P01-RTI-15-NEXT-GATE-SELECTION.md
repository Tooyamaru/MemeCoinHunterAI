# Post-P01-RTI-15 Next-Gate Selection

**Status:** COMPLETE / READY FOR CONTROLLER REVIEW

**Verified base:** `main` / `origin/main` at
`0828d0acac7af751953eba3c6b80770fdb4eb7c8`

**Review scope:** bounded dependency and integration-gap review only

## 1. Verified state

- P01-RTI-14 is COMPLETE / CLOSED / CI PASS.
- P01-RTI-15 is COMPLETE / CLOSED / CI PASS.
- P01-RTI-15 terminates at an exact canonical `PaperSimulationInput` inside
  `P01Rti15PaperAdmissionContinuationResult`.
- P01-RTI-02 remains the existing controlled lifecycle owner for P07-T02
  through P07-T07 and P08-T01.
- G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED.
- G3, G4, and P09 remain NOT AUTHORIZED.

## 2. Exact dependency gap

P01-RTI-15 and P01-RTI-02 are individually complete, but their application
contracts are not directly composable:

- RTI-15 emits a `P01Rti15PaperAdmissionContinuationResult` containing the
  exact admitted `PaperSimulationInput` and its decision and Risk/Capital
  lineage.
- RTI-02 accepts a `ControlledPaperRunAdmissionResult`, not an RTI-15 result or
  a bare `PaperSimulationInput`.

The missing integration boundary is therefore a compatibility composition. It
must construct the exact existing RTI-01-compatible admission envelope from
already-authoritative RTI-15 artifacts, without invoking RTI-01 or recomputing
P05, P06, Risk/Capital, or P07-T01, and then delegate exactly once to RTI-02.

## 3. Candidate assessment

| Candidate | Dependency readiness | Ownership/blast radius | Decision |
| --- | --- | --- | --- |
| RTI-15 → compatible admission envelope → RTI-02 | High; all exact source artifacts and the lifecycle owner exist | Thin application composition; closed owners unchanged | **Selected** |
| Adapter only, stopping before RTI-02 | High | Low, but creates an unnecessary extra terminal gate | Not selected |
| Change RTI-02 to accept RTI-15 directly | Medium | Changes a closed owner contract and regression surface | Rejected |
| Reimplement P07-T02–T07 outside RTI-02 | Technically possible | Duplicates lifecycle authority | Rejected |
| Persist or publish RTI-15 directly | Not ready | Skips the canonical lifecycle result | Deferred |
| Concrete runtime caller/provider loop | Caller/cadence authority unresolved | Opens operational runtime | Ineligible |
| G2/G3/G4/P09, wallet, or execution | Blocked/not authorized | Prohibited authority expansion | Ineligible |

## 4. Selected bounded gate

**P01-RTI-16 — Deterministic RTI-15-to-Controlled Paper Lifecycle
Continuation**

The selection is dependency-driven. The numbering follows the established RTI
sequence but does not itself grant implementation authority.

Canonical flow:

1. accept one canonical RTI-15 result plus explicit `PaperFillInstruction` and
   explicit `PaperLifecycleEvidence`;
2. stop before compatibility materialization and RTI-02 for every valid RTI-15
   outcome other than `ADMISSION_MATERIALIZED`;
3. for `ADMISSION_MATERIALIZED`, construct one exact
   `READY_FOR_PAPER_SIMULATION` `ControlledPaperRunAdmissionResult` from the
   already-carried exact decision, authorization, and paper input;
4. call `run_controlled_paper_lifecycle` exactly once with that envelope and
   the two exact caller inputs;
5. preserve the returned `ControlledPaperLifecycleResult` without rewriting
   its nested outcome, reasons, artifacts, or digest; and
6. stop before persistence or publication.

This boundary creates no new decision, Risk/Capital, fill, state, ledger,
reconciliation, paper-result, history, observation, persistence, or economic
authority.

## 5. Residual risks resolved by the formal specification

- canonical validation occurs before outcome branching, so malformed explicit
  inputs are never silently accepted on an upstream stop path;
- compatibility construction uses only the existing RTI-01 result contract;
- RTI-02 owner outcomes remain nested and authoritative;
- owner `ValueError` remains a validation failure, while unexpected failures
  are represented by finite safe wrapper reasons;
- the wrapper digest binds both explicit caller inputs and every predecessor
  digest without clocks, environment, iteration order, retry, or shared state;
  and
- the gate is unreachable from RTI-03/04, persistence, provider/runtime,
  wallet/execution, economic realization, G2/G3/G4, and P09.

## 6. Recommendation

The formal RTI-16 specification should be reviewed by the controller. This
checkpoint authorizes documentation only. Limited implementation requires a
separate explicit approval.
