# P01-OSC-02 — Prevalidated Risk/Capital Suffix One-Shot Paper Caller Specification

**Status:** SPECIFICATION COMPLETE / READY FOR CONTROLLER REVIEW

**Implementation:** AUTHORIZED / IMPLEMENTED ON FEATURE BRANCH / CLOSURE PENDING CI

**Contract:** `p01-osc-02-v1`

## 1. Purpose

P01-OSC-02 is a staged, in-memory, one-shot paper suffix caller.

It consumes one already-produced canonical
`P01Rti14RiskCapitalContinuationResult` and explicit paper simulation inputs,
then delegates only to RTI-15 and RTI-16.

It exists to preserve an already validated RTI-12→RTI-13→RTI-14 prefix without
rerunning those owners.

```
exact canonical RTI-14 result
        +
explicit ExecutionObservation
explicit SimulationConfigurationIdentity
explicit InitialPaperStateIdentity
explicit ReplayIdentity
explicit PaperFillInstruction
explicit PaperLifecycleEvidence
        ↓
RTI-15 exactly once when eligible
        ↓
RTI-16 exactly once when admitted
        ↓
STOP at exact RTI-16 result
```

## 2. Non-goals

OSC-02 does not:

- produce RTI-11;
- run RTI-12;
- run RTI-13;
- run RTI-14;
- construct or repair a Risk/Capital policy;
- rerun OSC-01;
- persist anything;
- publish anything;
- fetch provider data;
- execute a trade.

## 3. Exact request inputs

A future immutable `P01Osc02Request` accepts exactly:

- `invocation_id: str`;
- `rti14_result: P01Rti14RiskCapitalContinuationResult`;
- `execution_observation: ExecutionObservation`;
- `simulation_configuration: SimulationConfigurationIdentity`;
- `initial_paper_state: InitialPaperStateIdentity`;
- `replay_identity: ReplayIdentity`;
- `fill_instruction: PaperFillInstruction`;
- `lifecycle_evidence: PaperLifecycleEvidence`.

No RTI-11 result, decision ruleset, decision time, or policy snapshot is accepted
separately because those facts are already canonically bound inside RTI-14.

## 4. Canonical prefix requirement

The request must prove that the supplied RTI-14 result is canonical and that its
nested predecessor chain is exact:

`RTI-14 → RTI-13 → RTI-12 → RTI-11`.

For a materialized authorization, the exact nested links must preserve:

- RTI-11 result identity and digest;
- RTI-12 context result and digest;
- RTI-13 DecisionIntent and digest;
- RTI-14 policy snapshot and digest;
- RTI-14 authorization result and digest;
- candidate/chain/token identity;
- context digest;
- decision digest;
- policy provenance;
- authorization scope and effect.

No clone, recomputation, repair, fallback alias, or fabricated provenance is
permitted.

## 5. Eligibility to enter RTI-15

RTI-15 may be called only when the supplied RTI-14 result is exactly:

- outcome `AUTHORIZATION_MATERIALIZED`;
- contains one canonical authorization result;
- authorization status `APPROVED`;
- authorization effect
  `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`.

Any canonical RTI-14 result that is non-materialized or contains a canonical
Risk/Capital rejection stops before RTI-15.

## 6. Exact suffix delegation

When eligible:

1. pass the exact supplied RTI-14 result to
   `RiskCapitalToPaperAdmissionContinuationService.continue_to_paper_admission`;
2. pass the exact explicit execution/configuration/initial-state/replay inputs;
3. invoke RTI-15 exactly once;
4. validate the returned canonical RTI-15 result and exact predecessor identity;
5. continue only when RTI-15 outcome is exactly `ADMISSION_MATERIALIZED`;
6. pass that exact RTI-15 result plus the exact explicit fill/evidence inputs to
   `Rti15ToControlledPaperLifecycleContinuationService.continue_to_controlled_paper_lifecycle`;
7. invoke RTI-16 exactly once;
8. preserve the exact RTI-16 result without semantic rewriting;
9. stop.

## 7. Proposed OSC-02 outcomes

Exact wrapper outcomes:

- `LIFECYCLE_RETURNED`;
- `UPSTREAM_STOPPED`;
- `OWNER_UNAVAILABLE`.

These are coordinator outcomes only.

They do not replace RTI-14, RTI-15, RTI-16, Risk/Capital, or lifecycle domain
outcomes.

## 8. Stop behavior

### 8.1 RTI-14 not approved/materialized

Return `UPSTREAM_STOPPED`.

RTI-15 calls: 0.
RTI-16 calls: 0.

Preserve the exact RTI-14 reason/authorization reasons as appropriate.

### 8.2 RTI-15 does not materialize admission

Return `UPSTREAM_STOPPED`.

RTI-15 calls: 1.
RTI-16 calls: 0.

Preserve exact RTI-15 reason codes.

### 8.3 RTI-16 returns a canonical non-materialized lifecycle outcome

Return `UPSTREAM_STOPPED`.

RTI-15 calls: 1.
RTI-16 calls: 1.

Preserve exact RTI-16 reason codes and result.

### 8.4 RTI-16 materializes lifecycle

Return `LIFECYCLE_RETURNED` and preserve the exact RTI-16 result.

## 9. Validation failures

Malformed, tampered, structurally inconsistent, identity-mismatched, or
unsupported-version request material remains `ValueError`, not an ordinary
bounded outcome.

This includes:

- noncanonical RTI-14 or nested RTI-13/12/11;
- broken predecessor object identity;
- invalid authorization linkage;
- noncanonical explicit paper inputs;
- subject/replay/state/time contradictions;
- RTI-15 or RTI-16 owner `ValueError`.

Owner validation errors must be standardized and must not leak raw exception
details.

## 10. Unexpected owner failure

Unexpected RTI-15 or RTI-16 exceptions map to `OWNER_UNAVAILABLE` with one
finite stage reason:

- `RTI-15_UNAVAILABLE`;
- `RTI-16_UNAVAILABLE`.

No retry is permitted.

Invalid owner return objects are treated identically as bounded unavailable
stage results.

## 11. Determinism

The OSC-02 result digest must bind only canonical explicit material:

- OSC-02 contract version;
- invocation ID;
- wrapper outcome and reasons;
- exact RTI-14 contract/outcome/result digest;
- exact authorization status/result digest where present;
- execution observation digest;
- simulation configuration digest;
- initial paper state digest;
- replay identity canonical digest;
- fill instruction digest;
- lifecycle evidence digest;
- RTI-15 contract/outcome/result digest where present;
- RTI-16 contract/outcome/result digest where present.

Exclude:

- wall clock;
- environment;
- provider state;
- callable identity;
- exception text/type;
- object address;
- unordered iteration;
- filesystem state;
- shared mutable state.

## 12. Owner cardinality

| Owner | Maximum calls per OSC-02 invocation |
| --- | ---: |
| RTI-11 | 0 |
| RTI-12 | 0 |
| RTI-13 | 0 |
| RTI-14 | 0 |
| RTI-15 | 1 |
| RTI-16 | 1 |
| OSC-01 | 0 |
| OSP / RTI-03 | 0 |

This cardinality is a core contract requirement.

## 13. PFS relationship

P07-PFS-01 remains a separate simulation-only input owner.

OSC-02 may receive exact `PaperFillInstruction`,
`PaperLifecycleEvidence`, and matching `InitialPaperStateIdentity` produced
by PFS, but it does not invoke PFS itself.

A future controlled-input preparer may compose PFS with this staged architecture
under a separate gate.

## 14. Result shape

A future immutable `P01Osc02Result` should contain only:

- exact request;
- wrapper outcome;
- finite reason codes;
- terminal stage;
- optional exact RTI-15 result;
- optional exact RTI-16 result;
- deterministic result digest.

The exact upstream RTI-14 result remains reachable from the request and must not
be copied into a divergent wrapper.

## 15. Hard STOP boundary

Stop at exact RTI-16 result.

Forbidden:

- persistence/publication;
- P01-OSP-01;
- RTI-03/04;
- provider/network/polling;
- autonomous candidate/pool selection;
- worker/scheduler/queue;
- API/WebSocket/dashboard;
- wallet/private key/signing;
- RPC/DEX routing;
- broadcast;
- execution/live trading;
- economic realization;
- G2/G3/G4/P09.

## 16. Future focused test matrix

A separately authorized implementation must prove:

1. approved exact RTI-14 prefix reaches RTI-15 exactly once;
2. exact RTI-15 admission reaches RTI-16 exactly once;
3. exact lifecycle result is preserved;
4. rejected/non-materialized RTI-14 stops before RTI-15;
5. non-materialized RTI-15 stops before RTI-16;
6. malformed/tampered RTI-14 or nested prefix fails validation;
7. exact predecessor object identity is preserved;
8. explicit inputs are passed by exact identity;
9. owner `ValueError` becomes standardized validation failure;
10. unexpected RTI-15/16 exception becomes bounded unavailable;
11. invalid owner return becomes bounded unavailable;
12. deterministic replay produces the same wrapper digest;
13. RTI-11/12/13/14 and OSC-01 call count is zero;
14. no PFS, persistence, provider, API, scheduler, wallet, execution, G2/G3/G4/P09 import/call is reachable.

Regression must include RTI-14, RTI-15, RTI-16, OSC-01, PFS, and relevant
Risk/Capital/P07 tests.

## 17. Expected implementation scope

Only after separate explicit authorization:

- `backend/application/prevalidated_risk_capital_suffix_caller.py`;
- `tests/test_prevalidated_risk_capital_suffix_caller.py`;
- minimal `backend/application/__init__.py` export;
- minimal governance documentation.

No model, migration, repository, persistence owner, dependency, route, config,
secret, frontend, provider adapter, worker, scheduler, wallet, or execution code
is authorized.

## 18. Exit criterion

This specification is ready for controller review.

Controller authorization received. Limited implementation is present on the feature branch and remains pending GitHub CI, merge, and separate governance closure.

`SPECIFICATION READY FOR CONTROLLER REVIEW`
