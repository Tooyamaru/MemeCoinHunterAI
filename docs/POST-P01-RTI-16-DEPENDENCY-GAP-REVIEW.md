# Post-P01-RTI-16 Bounded Dependency / Gap Review

**Decision:** NATURAL STOPPING POINT / NO RTI-17 SELECTED

**Verified baseline:** GitHub `main` at
`00904bdf5cfd00352e6268d23b779c5649c5f843`. P01-RTI-16 is COMPLETE /
CLOSED / CI PASS; implementation PR #42 and closure PR #43 are merged. G2 is
BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3, G4, and P09 are NOT AUTHORIZED.

**Scope:** contract-level inspection of RTI-16 and the immediately relevant
RTI-02/03/04 downstream owners. No runtime, provider, live, or database
diagnostic is part of this review.

## 1. Exact terminal output and authority

`Rti15ToControlledPaperLifecycleContinuationService` accepts one canonical
`P01Rti15PaperAdmissionContinuationResult` and explicit canonical
`PaperFillInstruction` and `PaperLifecycleEvidence`. Its immutable
`P01Rti16ControlledPaperLifecycleContinuationResult` preserves the exact
upstream result and explicit inputs. Only canonical RTI-15
`ADMISSION_MATERIALIZED` creates the exact existing RTI-01-compatible
`ControlledPaperRunAdmissionResult` and invokes
`run_controlled_paper_lifecycle(...)` once. The success path preserves the
exact `ControlledPaperLifecycleResult` object, including the authoritative
RTI-02 outcome, artifacts, reasons, contract version, and digest.

The RTI-16 outcome `LIFECYCLE_MATERIALIZED` means *an exact canonical RTI-02
result exists*, not that an observation, reconciliation match, economic
outcome, or trade exists. Canonical non-admitted RTI-15 results stop before
RTI-02; unexpected or invalid owner outputs are bounded unavailable results;
malformed/tampered inputs and owner `ValueError` remain validation failures.
The RTI-16 result digest binds the RTI-15 digest and outcome, both explicit
caller-input digests, compatibility admission digest if present, and RTI-02
contract/outcome/digest if present. The hard STOP is the exact in-memory
`ControlledPaperLifecycleResult`: no RTI-03/04 invocation, database write,
publication, concrete caller, provider, or operational loop.

## 2. Downstream ownership and exact compatibility

| Existing boundary | Accepted input / responsibility | RTI-16 relationship |
| --- | --- | --- |
| RTI-02 lifecycle | Exact RTI-01 admission plus explicit fill/evidence | Already invoked once inside RTI-16; rerunning would duplicate authority |
| RTI-03 `ControlledPaperPersistenceService.persist` | Exact `ControlledPaperLifecycleResult`; validates and atomically stores the canonical lifecycle bundle | RTI-16 `lifecycle_result` is already this exact type; no compatibility adapter is missing |
| RTI-03 read and RTI-05–09 | Digest-based stored lifecycle snapshots and bounded read-only surface | Available only *after* an authorized RTI-03 write; no new reader is needed |
| RTI-04 `ControlledPaperRunService.run` | An explicit request beginning at P05-T08, then RTI-01 → RTI-02 → RTI-03 | A separate complete orchestration path; it does not accept an RTI-16 result and must not be rerun to persist one |

RTI-03 records the RTI-02 result and only the artifacts actually contained in
that result. Its documented closed artifact vocabulary does **not** include
the RTI-16 wrapper/result digest or the original `PaperFillInstruction` and
`PaperLifecycleEvidence` as replay inputs. Existing read surfaces return the
stored RTI-02 bundle, not a reconstructed RTI-16 result. This distinction
prevents a persistence call from being misrepresented as durable end-to-end
RTI-11–16 provenance or complete replayability.

## 3. Candidate / residual-gap assessment

| Candidate | Dependency finding | Disposition |
| --- | --- | --- |
| RTI-16 → RTI-03 thin write wrapper | Exact nested lifecycle type already matches `persist`; RTI-04 already owns one-shot persistence coordination for its own path. A new wrapper would mainly add a second gate and state-dependent storage outcome, without retaining the RTI-16 wrapper provenance in RTI-03. | **Not selected**: no demonstrated contract incompatibility or governed requirement for this write |
| Feed RTI-16 to RTI-04 | RTI-04 accepts its own P05-T08-starting request, not RTI-16, and would rerun P06/Risk/Capital/P07 and lifecycle. | Rejected: duplicates closed owners and discards exact upstream path |
| Persist full RTI-16 lineage / explicit replay facts | Current RTI-03 schema and artifact contract cannot retain them. Needs an explicit retention/identity/readback policy and separately governed persistence contract/schema capability. | Deferred: not a thin composition |
| Route, dashboard, automatic caller, provider polling, worker/scheduler/queue | No authorized invocation, cadence, publication, exposure, or provider-operational policy for this chain. | Ineligible in this review |
| G2/G3/G4/P09, economic realization, wallet/signing/RPC/DEX, execution/live trading | Authority blocked or absent. | Prohibited |

The missing *operational* choices are not a type-level integration gap. In
particular, no controller-approved requirement says the RTI-16 result must be
persisted now, which lifecycle outcomes to submit to storage, who supplies the
explicit inputs and database runtime, or whether RTI-16 lineage must survive
restart. Merely numbering a wrapper RTI-17 would not answer those questions.

## 4. Contract semantics if a future use case is authorized

These are **decision constraints**, not a successor specification or authority
grant:

- **Input/STOP:** An optional existing RTI-03 call can take the exact nested
  `ControlledPaperLifecycleResult` only when RTI-16 is
  `LIFECYCLE_MATERIALIZED`. `UPSTREAM_NOT_ADMITTED` and
  `LIFECYCLE_UNAVAILABLE` have no lifecycle object and cannot be fabricated
  into an RTI-03 input. Any such call is outside the RTI-16 STOP boundary.
- **Cardinality:** An authorized caller or separately specified coordinator
  would invoke the existing RTI-03 owner at most once per attempt, without
  rerunning RTI-01–16 or using RTI-04 as a shortcut. No automatic retry,
  polling, queue, or worker follows from the present chain.
- **Failures:** RTI-03 owns `STORED`, `ALREADY_STORED`, `CONFLICT`,
  `INVALID_INPUT`, and `STORAGE_UNAVAILABLE`. They are storage outcomes, not
  lifecycle or economic outcomes. Malformed/tampered RTI-16 input must not be
  silently converted to an ordinary upstream stop; exact validation and
  cancellation behavior would need to be specified separately.
- **Identity/provenance:** The RTI-03 result refers to the RTI-02 lifecycle
  digest, not the RTI-16 wrapper digest. A requirement to bind and later read
  RTI-16/RTI-15 lineage or original fill/evidence requires an explicit new
  durable contract rather than invented rows or reconstructed facts.
- **Determinism:** RTI-16 is deterministic over canonical explicit inputs and
  equivalent owner results. RTI-03 storage outcomes may change from `STORED`
  to `ALREADY_STORED` on an explicit repeat or vary with database state. A
  future wrapper cannot promise the same outcome solely from identical RTI-16
  input, nor introduce wall-clock time or database metadata into owner digests.

## 5. Selection and next controller decision

The bounded caller-supplied **in-memory paper lifecycle chain** is complete
for its authorized purpose at RTI-16. No RTI-17 or formal successor
specification is justified by the current repository dependency graph. This
does **not** mean that a live system, durable full-chain provenance, automated
paper runner, economic realization, or execution path is complete.

If a concrete need arises, the controller must choose and separately authorize
its goal before a new gate is specified: use existing RTI-03 persistence of
only its canonical RTI-02 bundle, define new durable RTI-16 lineage/replay
ownership, or define a concrete caller/operational policy. None is selected
here. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3, G4, P09,
provider loops, scheduler/worker/queue, wallet/signing/RPC/DEX, economic
realization, and live trading remain NOT AUTHORIZED.
