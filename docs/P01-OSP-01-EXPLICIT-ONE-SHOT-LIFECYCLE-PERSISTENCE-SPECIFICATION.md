# P01-OSP-01 — Explicit One-Shot Lifecycle Persistence after OSC-01

**Status:** SPECIFICATION COMPLETE / READY FOR CONTROLLER REVIEW / IMPLEMENTATION NOT AUTHORIZED

**Proposed contract:** `p01-osp-01-v1`

**Baseline and selection:** GitHub `main` `80dc8baa6cb0b669505104861865648b087052fa`; dependency findings in `POST-P01-OSC-01-PERSISTENCE-DEPENDENCY-REVIEW.md`. The identifier OSP identifies a separate optional one-shot persistence use case, rather than extending RTI numbering or moving OSC's STOP.

## 1. Authority and exact entry

One HTTP-independent application entry point, provisionally `OneShotPaperPersistenceService.persist(osc_result: P01Osc01Result) -> P01Osp01Result`, is **async** and receives an explicit existing `ControlledPaperPersistenceService` through construction/injection. There is exactly one caller-supplied argument: the already-produced exact canonical OSC-01 result; no request for token, paper fill, policy, replay, provider, OSC re-invocation, database URL, or separate lifecycle copy is accepted. The caller's **decision to invoke this separate service** is the explicit persist choice. No implicit persistence, default-on flag, or mutation of OSC-01 is authorized. The controller must separately authorize implementation before code is written.

The exact input must be a canonical `P01Osc01Result` at `p01-osc-01-v1`, preserving `invocation_id`, `result_digest`, exact ordered RTI-11–16 nested results, explicit caller-input material/digests, and exact identity links. Preflight revalidates the OSC owner result and all present nested owner results/digests according to their contracts, prior to any database transaction. Tampered, malformed, identity/structure mismatched, version-mismatched, or missing canonical input raises a standardized `ValueError`; no storage delegate and no ordinary outcome. Preflight must not fabricate a lifecycle from a paper simulation input, RTI-16 compatibility admission, owner digest, or partial OSC result.

## 2. Eligibility and exact delegation

| OSC result | RTI-16 / RTI-02 condition | RTI-03 calls | OSP disposition |
| --- | --- | ---: | --- |
| `LIFECYCLE_RETURNED` | Exact RTI-16 `LIFECYCLE_MATERIALIZED` and exact non-null `ControlledPaperLifecycleResult` | Exactly one | Submit the **same object** to `await ControlledPaperPersistenceService.persist(osc_result.rti16_result.lifecycle_result)` |
| `UPSTREAM_STOPPED` | No completed lifecycle usable for storage | Zero | `UPSTREAM_NOT_PERSISTABLE`, preserving exact OSC result, outcome, reasons and terminal stage |
| `OWNER_UNAVAILABLE` | No completed lifecycle usable for storage | Zero | `UPSTREAM_NOT_PERSISTABLE`, preserving exact OSC result, outcome, reasons and terminal stage |

All four canonical RTI-02 lifecycle outcomes in `LIFECYCLE_RETURNED` may be submitted. The gate does not filter on fill, reconciliation, observation, or economic success. It must never call RTI-11, RTI-12–16, RTI-01/02, RTI-04, P05/P06/Risk/Capital/P07/P08 owners, or `run_controlled_paper_lifecycle`. It does not perform an automatic read-after-write. The RTI-03 service alone owns validation, serialization, one atomic write attempt and any bounded concurrent-write comparison defined by its own contract. No external controller may invoke the *same* gate twice automatically; an explicitly repeated call is another attempt handled by RTI-03 idempotency.

## 3. Outer result and failure semantics

Immutable `P01Osp01Result` contains contract version, exact original `P01Osc01Result` object, exact `invocation_id` and OSC contract/outcome/result digest, one closed outer outcome, canonical bounded reason codes, optional exact `PaperLifecyclePersistenceResult` object, exact RTI-16 contract/outcome/result digest and RTI-02 contract/outcome/lifecycle digest where present, and its own deterministic digest. RTI-03 result presence is required exactly for completed delegation, except bounded unexpected delegate failure. No outer field changes canonical owner outcomes.

Closed outer outcomes: `UPSTREAM_NOT_PERSISTABLE`, `STORED`, `ALREADY_STORED`, `CONFLICT`, `INVALID_INPUT`, `STORAGE_UNAVAILABLE`, and `PERSISTENCE_UNAVAILABLE`. The middle five correspond **exactly** to the RTI-03 result outcomes and preserve the owner's reason codes and exact result object. `UPSTREAM_NOT_PERSISTABLE` has no RTI-03 result. `PERSISTENCE_UNAVAILABLE` is reserved for an unexpected non-validation exception or invalid/mismatched RTI-03 owner result, with finite non-leaking reason, no fabricated persistence object, and no automatic retry. It cannot claim a write was rolled back or did not commit if the error happened after the delegate began; an explicit later caller read by the RTI-02 digest can resolve the observed storage state.

RTI-03 `INVALID_INPUT` remains a canonical storage-owner outcome **only if** RTI-03 itself returns a valid canonical result; caller/OSC tampering and owner `ValueError` are validation failures, not this bounded outcome. Verify any owner-supplied lifecycle digest equals the exact submitted RTI-02 digest; for `STORED`, `ALREADY_STORED`, `CONFLICT`, and `STORAGE_UNAVAILABLE` the digest is required, while RTI-03 `INVALID_INPUT` may omit it under the existing owner contract. A mismatch or malformed RTI-03 result is `PERSISTENCE_UNAVAILABLE`, not proof of a write. Cancellation propagates unchanged and must not launch another write. Safe errors never expose SQL, credentials, payload bytes, exception text, or database URLs.

## 4. Identity, provenance, determinism and readback

The outer result digest binds OSP contract/outcome/reasons, exact OSC invocation identity/contract/outcome/digest, RTI-16 contract/outcome/digest, the submitted RTI-02 contract/outcome/digest where present, and RTI-03 contract/outcome/result digest where present. On no-write/unknown owner branches, absent fields remain explicitly absent. The RTI-03 write and read keys remain the **RTI-02 lifecycle digest**; OSC ID and OSC/RTI-16 digests are in-memory correlation only, never inserted into RTI-03 rows or substituted as lookup keys. Owner digests do not acquire invocation ID, wall-clock, storage timestamps, or provider/environment material.

With equal canonical input **and equal canonical RTI-03 result**, the outer result/digest is deterministic. It is *not* input-only deterministic across database states: `STORED`, `ALREADY_STORED`, `CONFLICT`, `INVALID_INPUT`, and `STORAGE_UNAVAILABLE` retain RTI-03's state-dependent meanings. An exact explicit repeat can yield `ALREADY_STORED`; RTI-03 compares the full existing bundle, not just the digest, and preserves conflicting data unchanged. A failed or cancelled response never authorizes an implicit retry.

RTI-05 existing read service and RTI-03 `read(lifecycle_result_digest)` accept only the RTI-02 digest and return read-only stored snapshots with `FOUND`, `NOT_FOUND`, `CORRUPT`, `STORAGE_UNAVAILABLE`; they cannot reconstruct executable RTI-02 objects, OSC/RTI-16 wrappers or original replay inputs. Readback is caller-directed under existing contracts and outside the OSP-01 STOP. Persistence records only the canonical RTI-02 bundle and artifacts actually present. The fill instruction, lifecycle evidence, OSC wrapper and full earlier replay material remain **outside durable retention**.

## 5. Hard STOP, exclusions and future verification

STOP at the exact canonical `PaperLifecyclePersistenceResult` returned by RTI-03, wrapped without changing its meaning. For upstream stops, STOP at the exact OSC result with no write; for unexpected owner failure, STOP at the bounded OSP result with no invented RTI-03 result. No RTI-04 reuse, second persistence owner, schema/model/migration, new read API, publication, full provenance/replay archive, provider loop, autonomous selection, scheduler/worker/queue, automatic retry, wallet/signing/RPC/DEX, economic realization, execution, or live trading is authorized. G2 stays BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 stay NOT AUTHORIZED.

Future implementation requires separate controller approval and focused tests for canonical OSC validation before any write; exact object/digest linkage; zero calls for both OSC nonterminal outcomes; one RTI-03 call for all four canonical RTI-02 outcomes; owner `STORED`/`ALREADY_STORED`/`CONFLICT`/`INVALID_INPUT`/`STORAGE_UNAVAILABLE` propagation; malformed owner result and exception behavior; cancellation; no repeat delegation; and existing RTI-03/05 readback by lifecycle digest. This checkpoint changes only specification and governance documentation.
