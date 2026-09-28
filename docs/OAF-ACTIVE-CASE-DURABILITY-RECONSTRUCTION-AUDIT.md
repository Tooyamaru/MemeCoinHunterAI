# OAF Active-Case Durability / Reconstruction Audit

Status: AUDIT COMPLETE / CURRENT SINGLE-PROCESS DESIGN RETAINED / NO DURABLE ACTIVE-CASE IMPLEMENTATION SELECTED

Repository checkpoint: `63d5213bb5f9a10e74804be63a6a0ba87dc27095` (`main` after PR #98).

## Question

Can the current Operator Facade active prepared case be made restart-safe or
cross-process by simply storing it in the existing database, without changing
closed owner contracts or rerunning provider/domain owners?

## Repository findings

### 1. The active OAF case is deliberately an exact in-memory object graph

`OperatorPaperCaseRegistry` owns one finite process-local record containing the
exact `OafPrepareCaseResult`. The run and persist paths do not merely compare
digests: they preserve exact object relationships produced during prepare.

Examples of current identity invariants include:

- `P01Cip01Request` requires PFX and PFS to share the same exact RTI-11 object;
- `P01Cip01Result` requires its prepared OSC-02 request to retain the exact
  RTI-14, execution observation, simulation configuration, initial paper state,
  replay identity, fill instruction and lifecycle evidence objects;
- OCI validates the OSC-02 result against the exact prepared OSC-02 request;
- the OAF run registry requires the OCI result to retain the exact prepared CIP
  identity;
- persistence takes the exact lifecycle object returned by that terminal OCI/OSC
  graph and delegates it once to RTI-03.

Those invariants are stronger than ordinary digest equality.

### 2. Existing durable RTI-03 persistence is terminal-lifecycle persistence

The current database schema stores append-only `PaperLifecycleRun` and
`PaperLifecycleArtifact` records. It is intentionally downstream of a completed
controlled-paper lifecycle.

RTI-03 stores canonical lifecycle artifact snapshots and can provide durable
readback/catalog results. It does not store an OAF prepared-case handle,
`OafPrepareCaseResult`, `P01Cip01Result`, OCI claim state, or a reconstructable
pre-run object graph.

Therefore RTI-03 cannot currently restore a lost `REVIEW_READY` or
`RUN_CLAIMED` process-local case.

### 3. Current canonical representations are validation/digest surfaces, not full reconstructors

Several application results expose deterministic digest material or
`canonical_representation` summaries. These are sufficient for validation,
lineage and persistence of their governed outputs, but the repository does not
define a general inverse constructor that can rebuild the complete OAF object
graph while preserving every identity relationship required by CIP/OCI.

Storing one summary/digest payload therefore does not make the active case
reconstructable.

### 4. Replaying prepare is not reconstruction

The browser/operator prepare input plus server configuration is not a safe
replacement for the lost active object graph. Re-running prepare would invoke
trusted source/RTI-11 and closed deterministic owners again, producing a new
invocation with potentially different source availability/timestamps and new
Python object identities.

That would violate the current no-hidden-rerun design and cannot be presented as
the same already-reviewed case.

## Candidate approaches

### A. Keep one stable process for active cases — SELECTED FOR CURRENT PAPER PHASE

Use the current process-local registry for the bounded lifetime from prepare to
review/run/persist. Require the PR #98 deployment acknowledgement in
staging/production and operate only in a topology that guarantees one stable
application process for an active case.

Durable RTI-03 readback remains available after successful persistence.

This preserves every existing owner contract and exact-identity invariant.

### B. Serialize/deserialize the current Python object graph — NOT SELECTED

A generic pickle/object dump would create an unsafe trusted-runtime boundary,
couple storage to Python implementation details, complicate version migration,
and still require explicit guarantees for atomic run/persist claims.

A hand-written canonical serializer/reconstructor would be a substantial new
cross-owner contract, not an infrastructure-only registry change.

### C. Persist prepare inputs and rerun owners after restart — REJECTED

This would rerun trusted provider/RTI-11 and preparation owners and would no
longer be the exact already-reviewed case. It also risks changing evidence
availability/freshness while retaining an old operator handle.

### D. Store only case/digest claim state in a shared database — INSUFFICIENT ALONE

A shared claim row could coordinate duplicate requests but cannot supply the
exact prepared object graph to OCI on another process. It may become one part
of a future distributed design, but it does not solve reconstruction.

## Required design work before any durable active-case implementation

A future restart-safe/cross-process OAF design requires a separately authorized
contract that decides, at minimum:

1. the exact canonical snapshot boundary to persist before run;
2. complete versioned serializers and reconstructors for every required owner
   artifact, or explicit replacement of selected Python `is` invariants with
   canonical lineage/digest equivalence;
3. migration and unsupported-version behavior;
4. distributed atomic claim semantics for run and persist;
5. restart recovery for `RUN_CLAIMED` and `PERSIST_CLAIMED`;
6. treatment of uncertain external/process failure after claim;
7. TTL/expiry and cleanup semantics;
8. proof that reconstruction never reruns provider/domain owners;
9. security rules for any stored operator inputs or source evidence.

That is an architecture milestone, not a small persistence patch.

## Current decision

No durable/reconstructable active-case implementation is selected now.

For the current controlled-paper phase:

- PR #98 fail-closed deployment guard is the correct minimum hardening;
- active OAF mutation remains single-process and process-local;
- autoscale/multi-worker/restart-safe mutation must not be claimed;
- persisted terminal lifecycle readback remains database-backed and durable;
- the next practical verification is one explicit provider-backed paper-only
  smoke sequence in a known single-process environment when runtime secrets are
  intentionally available.

## Authority boundary

This audit authorizes no source-code implementation and no provider invocation.
It does not open autonomous discovery, polling, retries, worker/scheduler
execution, wallet/signing, DEX routing, settlement, live trading, or economic
realization.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
