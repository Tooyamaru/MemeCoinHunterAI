# A1-AUD-01 — offline durable collection audit linkage

Contract: `a1-durable-collection-audit-v1`.

Status: OFFLINE IMPLEMENTED / MERGED / POST-MERGE CI PASS.
PR #143 MERGED / CLOSED; exact head
`3e371a1c53c28d0bf15585458a4f5ff7940c6f8f`, PR CI #567 /
`37195942557` SUCCESS. Main `8b549e599038c8418589baae16fc303b5e8c36ac`;
post-main CI #568 / `37212294693` SUCCESS, Python 3.13 and TypeScript PASS.
This evidence is reconciled with the next substantive A1-HTTP-01 batch;
operational migration and runtime/database qualification remain unperformed.
Starting main: `981f16c4fc34b41bf7f19b4075c52a03caabfe1a`; PR #142 merged,
post-merge CI #566 / `37116227151` SUCCESS, Python 3.13 and TypeScript PASS.

## Selection and scope

The historical dependency review stopped because RTI-03 has 13 closed artifact
kinds and infrastructure metadata is mutable. After that storage proposal, the
controller delegated the next arrangement ("Coba kamu aturkan"), asked that work
advance promptly, and requested continuation. This batch selects the smallest
additive source change: one separate audit/link table and one migration. It
prepares and tests that migration only on isolated temporary databases. Applying
it to an operational database is a separate deliberate action.

Review, formal contract, offline code/tests and state reconciliation travel in
ONE implementation PR. Preserve Fast Mode: focused/relevant local validation;
full suites in PR CI; STOP when that CI starts. No closure PR or waiting loop.

## Inputs and original-owner binding

The producer takes the exact frozen `DiagnosticCollectionPacket`, connected and
finished `RTI11DiagnosticReplay`, and canonical `P01Oci01Result`. The latter must
retain a returned OSC-02/RTI-16 `OBSERVATION_PRODUCED` lifecycle. Their constructors
and the existing collection validators are reused without invoking discovery,
P03 evaluation/eligibility, pool selection, diagnostic composition, decision,
Risk, PFS, paper simulation or persistence owners again.

The packet must be the very object in the replay graph. Original discovery,
predecessor, safety, selected pool and RTI-11 request identities remain governed
by the merged replay validators. All captured binding/lineage pairs must agree.
The selected RTI-11 request must be the original bound request, and its canonical
result digest must equal that replay's recorded result. CIP/PFX/PFS/OCI/OSC/RTI-16
preserve their closed identity chain. The lifecycle retains the exact prefix
decision and approved paper-only Risk authorization objects.

No active-case reconstruction or second execution is supported. Equality of a
foreign object graph cannot replace original-object binding during capture.
Completed successful lifecycles are the only supported attachments in v1;
collection STOPs, vetoes and incomplete cycles do not manufacture lifecycle roots.

## Durable material and integrity

The canonical audit JSON retains:

- Full packet material, original request/response bytes, pre-T receipts, source
  clocks, immutable T, verification evidence, policies and complete ledger.
- Discovery, P03 evidence, pool and diagnostic binding projections and digests;
  selected-pool valuation/reserve lineage, exact requests and reuse/separate-call
  references; every recorded replay lineage and the selected canonical RTI-11
  result.
- Digests linking that selected result through PFX/PFS/CIP/OCI/OSC/RTI-16 to the
  lifecycle, decision and independent Risk authorization.
- The exact existing RTI-03 root projection and ordered artifact digest/payload
  digest manifest. It does not add an RTI-03 artifact or change artifact counts.

Raw bytes use canonical base64 in a content-addressed blob map; repeated A1
candle reuse does not duplicate the body. Hash-only owner projections remain
unchanged. Every referenced body is retained, checked for length/SHA-256, and
used; extra, missing or altered blobs fail readback. The existing whole-cycle
budgets remain unchanged; the audit document has a separate 256 MiB encoding
cap, at most 231 deduplicated request/response blobs, each at most 1 MiB.

Canonical JSON rejects duplicate keys, nonfinite numbers and noncanonical
encoding. Packet/context/binding/request/selected-result hashes and their links
are rechecked on readback. The selected observations must refer to the retained
raw response's hash; existing PFS friction provenance in the canonical parent
fill artifact independently anchors the winning RTI-11 result digest.
The payload hash and a separate audit identity hash
bind the contract, lifecycle, collection, packet, selected result and payload.
These are integrity checks, not signatures against an attacker rewriting the
entire database. Losing-candidate result digests are recorded replay lineage;
the winning result is additionally validated through canonical retained owners.

## Storage and atomicity

Revision `0003_a1_collection_audit`, after `0002_paper_lifecycle`, creates only
`a1_collection_audits`. One row contains the payload and its link. `run_id` has a
RESTRICT foreign key to the existing lifecycle root; unique run/lifecycle/audit
identities prevent a second attachment. No existing table or migration changes.
The repository exposes append/read only, following the current application
storage convention; privileged SQL is outside that interface.

The caller explicitly invokes the audit service after existing RTI-03 persistence.
Audit capture completes before opening its one write transaction. In that
transaction, the existing RTI-03 comparison validates the exact already-stored
lifecycle bundle before insertion. Missing parent -> `LIFECYCLE_NOT_FOUND`;
parent/content disagreement -> `CONFLICT`. No lifecycle is inserted by this
service. Audit failure rolls back the attachment and preserves the independently
completed lifecycle. That lifecycle alone does not prove a durable source audit.

Identical full content -> `ALREADY_STORED`, no extra row. Different content for
the same lifecycle -> `CONFLICT`, no overwrite. A uniqueness race may have one
read-only resolution after rollback; it never retries an insertion. All storage
failure paths are explicit, without internal automatic retry.

Readback by lifecycle digest returns `FOUND` only if the complete audit, foreign
identity and canonical RTI-03 root/artifact manifest all validate. Otherwise:
`NOT_FOUND`, `CORRUPT` or `STORAGE_UNAVAILABLE`. It returns immutable evidence
and original bytes for inspection, never executable owner instances. There is
no HTTP API, scheduler, automatic wiring or database qualification claim.

## Acceptance and boundaries

Focused tests cover real synthetic one-cycle owner composition, lossless raw
bytes, deterministic immutable capture, reused/separate diagnostics, exact
object substitution, clock/body/request/pool/lineage mismatch, missing lifecycle,
successful attachment/readback, duplicate/conflicting and concurrent writes,
corrupt audit/parent rejection, rollback, unavailable/missing storage and Risk
veto. Actual Alembic upgrade/downgrade/re-upgrade on a populated isolated SQLite
database must preserve existing lifecycle rows, artifacts and schema, and verify
the new foreign/unique constraints. PostgreSQL migration SQL is compiled without
opening a connection. PostgreSQL operational migration and runtime
qualification remain unperformed and are not inferred from SQLite tests.

No network/provider execution, credentials, quota/latency work, runtime changes,
wallet/signing/broadcast/DEX/settlement/live trading or MASTER_BLUEPRINT revision.
Risk Governor remains INDEPENDENT / MANDATORY / HIGHER AUTHORITY. G2 remains
BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.

## Local verification evidence

Python 3.13.15: 38 audit cases plus 2 migration cases PASS in bounded focused
runs, including the final 11-case linkage recheck. Relevant A1/P03/RTI-11,
RTI-03 write/query/catalog and foundation regressions: 219 tests PASS.
Compilation, whitespace and bounded source/governance audit PASS. Full suites
were delegated to exact-head PR CI, now verified together with post-merge main
CI above. Operational database migration remains separate and unperformed.
