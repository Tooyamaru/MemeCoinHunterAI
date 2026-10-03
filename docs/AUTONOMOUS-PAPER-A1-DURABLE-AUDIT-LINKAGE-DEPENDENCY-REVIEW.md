# A1/P03/RTI-11 durable audit linkage — bounded dependency review

**Status:** REVIEW COMPLETE / IMPLEMENTATION PATH STOPPED / STORAGE CONTRACT BLOCKED.

**Proposed task:** A1-AUD-01 — offline durable collection audit linkage.

This is a dependency review, not a formal implementation contract or a completed
durable audit capability. The controller's 2026-10-03 PIPELINE FAST MODE batch
authorizes review/specification/implementation together, but explicitly requires
STOP if the capability needs an unsupported schema migration or major
persistence redesign. That stop condition applies here.

## Verified baseline

- GitHub main: `981f16c4fc34b41bf7f19b4075c52a03caabfe1a`.
- PR #142 MERGED / CLOSED; CI trigger optimization is landed.
- Main CI #566 / run `37116227151`: IN PROGRESS at this checkpoint; Python 3.13
  is running `Run Python tests`, TypeScript checks/builds PASS. No idle CI loop.
- A1/P03/RTI-11 offline implementation is already landed through PR #141; the
  collection/replay owners and independent mandatory Risk authority are retained.

## Finding

The frozen common collection packet and immutable discovery/safety/pool/request
and replay-lineage records contain the source evidence needed for an audit.
They remain outside the canonical lifecycle bundle accepted by RTI-03. Existing
paper persistence proves the lifecycle/result artifacts, but does not durably
retain the raw collection packet or its complete exact upstream replay binding.
The missing capability is durable evidence linkage, not another provider call,
new scoring calculation or repeated safety/diagnostic evaluation.

| Existing owner | Verified constraint | Consequence |
| --- | --- | --- |
| `core/data/a1_rti11_collection.py` | Frozen packet plus original-object binding and replay-lineage records; no durable writer. | Source audit material exists process-locally. |
| `core/runtime/controlled_paper_lifecycle.py` | `ControlledPaperLifecycleResult` has no collection/audit attachment field. | A thin caller cannot supply the audit as an existing lifecycle artifact. |
| `backend/application/paper_lifecycle_persistence.py` | `persist()` accepts exactly one canonical lifecycle result; 13 closed artifact kinds. Completed readback requires exactly the canonical artifact-kind sequence. | Injecting an audit kind or extra artifact is not a supported extension; readback rejects it. |
| `backend/core/repositories.py` | `insert_bundle()` is the low-level write for the lifecycle bundle; reads enumerate all artifact rows for that run. | Direct SQL/repository insertion does not grant new owner authority or preserve the closed read contract. |
| `backend/core/models.py` | Only lifecycle run/artifact tables and infrastructure-only `SystemMetadata`; metadata `set()` can overwrite existing content. | Metadata is not an immutable source-evidence store, and no independent audit/link table exists. |

RTI-03's formal specification also expressly closes its artifact vocabulary and
stores only the artifacts retained by RTI-02. See
`P01-RTI-03-CONTROLLED-PAPER-PERSISTENCE-SPECIFICATION.md`, sections 2–4 and 8.
The fact that SQL stores artifact kind as text does not make arbitrary kinds a
supported application contract.

## Exact blocker and smallest safe direction

Reusing the lifecycle tables for a new audit artifact would require revising the
closed RTI-03 write/read, artifact-count/order and exact idempotence contracts.
Appending raw audit data to an existing artifact would change its canonical
owner payload/digest. Reusing infrastructure metadata would violate its scope
and immutable duplicate-content requirements. None is a safe composition-only
implementation of the current owners.

Preserving those owners requires an explicitly selected append-only audit/link
storage contract, linked to the existing lifecycle identity, with a compatible
schema migration. The minimum missing decision is that storage extension and
its atomicity/idempotence/readback relationship with the existing RTI-03 bundle.
No migration, table, writer, API or contract revision is created in this batch.

An isolated in-memory audit serializer would be preparatory work and would not
complete the requested durable linkage or corrupted-readback/duplicate-write
acceptance cases. It is not substituted as a completed milestone. Operational
adapter qualification, quota/latency, qualifying runtime/database and provider
smoke require their separate operational authority and are not selected.

## Verification and checkpoint

Bounded source-contract probes PASS: exact single lifecycle write input, 13
closed kinds, no lifecycle audit field, no audit table, infrastructure-only
metadata, and strict artifact count/order/unsupported-kind/readback rejection.
Only the named collection/lifecycle/persistence owners and their relevant formal
specifications were inspected. No repository-wide scan, provider/database call,
secret read, dependency installation or full local suite was performed.

Formal durable audit contract/specification and production implementation:
NOT STARTED. New focused tests and implementation regressions: NOT RUN because
the storage prerequisite is blocked. This checkpoint changes only review/state/
changelog documentation; no implementation PR is opened. The controller must
select/authorize the compatible storage extension before this path can resume.

Risk Governor remains INDEPENDENT / MANDATORY / HIGHER AUTHORITY. No provider,
wallet/signing/broadcast/DEX/settlement/live authority. G2 remains BLOCKED /
UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED. Historical progress,
MASTER_BLUEPRINT and closed owner behavior are unchanged.
