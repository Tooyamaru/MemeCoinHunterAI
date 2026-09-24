# Post-P01-OSC-01 Bounded Persistence Dependency Review

**Decision:** select P01-OSP-01 as a separately authorized, optional persistence composition specification; implementation NOT AUTHORIZED.

**Verified baseline:** GitHub `main` `80dc8baa6cb0b669505104861865648b087052fa`; OSC-01 COMPLETE / CLOSED / CI PASS, PRs #46–48 merged. G2 BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 NOT AUTHORIZED.

## Dependency and exact handoff

OSC-01 `P01Osc01Result` terminates in memory. Its `LIFECYCLE_RETURNED` branch contains the exact RTI-16 `P01Rti16ControlledPaperLifecycleContinuationResult` with `LIFECYCLE_MATERIALIZED`, whose `lifecycle_result` property is the same exact `ControlledPaperLifecycleResult` object returned by the RTI-02 owner. RTI-03 `ControlledPaperPersistenceService.persist(lifecycle_result: ControlledPaperLifecycleResult)` already accepts that exact type and canonical RTI-02 version. No compatibility model, conversion, re-evaluation, or new domain owner is required. RTI-03 accepts all four *canonical* RTI-02 outcomes, including `ADMISSION_NOT_READY`, `RECONCILIATION_NOT_MATCHED`, and canonical `INVALID_INPUT`; an OSC success means existence of an RTI-02 result, not a profitable fill.

OSC `UPSTREAM_STOPPED` and `OWNER_UNAVAILABLE` lack a valid returned lifecycle and cannot be sent to RTI-03. A malformed/tampered OSC wrapper, nested RTI-16 result, mismatch between nested lifecycle and OSC, or unsupported version is validation failure before a write; a digest alone is insufficient. No RTI-04 call is appropriate: RTI-04 starts from P05-T08, reruns upstream owners, and persists its own lifecycle. RTI-05 delegates read-only lookup to RTI-03 by **RTI-02 lifecycle digest**, never OSC digest.

## Controller selection and consequences

The controller has requested a bounded review of persistence following OSC-01. The proper operational choice is explicit: first invoke OSC once with canonical caller inputs; then, *if the caller chooses to store its already-produced result*, separately invoke the proposed P01-OSP-01 gate on that exact OSC result. The gate must not invoke OSC, RTI-11–16, or RTI-04. Selecting this gate therefore adds optional durable **RTI-02 lifecycle bundle** retention, without modifying OSC's hard STOP or making persistence the default. RTI-03 already owns validation, atomic write, idempotent comparison, conflict, and readback. OSP-01 owns only preflight linkage, one-delegate application coordination, and its outer result.

Storage is state-dependent: first write may return `STORED`; a later identical explicit write may return `ALREADY_STORED`; a different bundle under the same lifecycle digest returns `CONFLICT`; unavailable storage returns `STORAGE_UNAVAILABLE`. The gate cannot promise input-only deterministic storage outcomes, exactly-once delivery across requests, or no extra *attempts* if the caller deliberately invokes it again. RTI-03 enforces one canonical stored bundle. There is no automatic retry, read-after-write, or repair. Readback is an independent RTI-03/05 operation that can return `FOUND`, `NOT_FOUND`, `CORRUPT`, or `STORAGE_UNAVAILABLE` and cannot reconstruct an OSC or RTI-16 wrapper.

The RTI-03 schema does not store OSC invocation ID/digest, RTI-16/15 wrapper, original `PaperFillInstruction`, `PaperLifecycleEvidence`, or complete earlier replay inputs. A present in-memory OSP result can bind OSC and persistence digests, but persisted RTI-03 rows alone do not provide durable end-to-end lineage or full replay. These require a separately authorized contract and ownership decision. No provider loop, token selection, scheduler/worker, wallet, execution, economic authority, G2/G3/G4/P09, or live trading follows from this selection.
