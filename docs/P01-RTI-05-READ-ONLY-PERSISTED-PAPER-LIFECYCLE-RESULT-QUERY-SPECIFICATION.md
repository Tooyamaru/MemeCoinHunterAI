# P01-RTI-05 — Read-Only Persisted Paper Lifecycle Result Query

## Status

AUTHORIZED / IMPLEMENTED / LOCAL CHECKPOINT PASS / CI PENDING

## Boundary

P01-RTI-05 is a thin, HTTP-independent application query boundary. It accepts
exactly one explicit canonical `lifecycle_result_digest`, delegates exactly one
read to `ControlledPaperPersistenceService.read(...)`, and returns the same
authoritative `PaperLifecycleReadResult` without wrapping or semantic rewriting.

P01-RTI-03 remains the sole persistence, validation, snapshot, corruption, and
artifact-ordering owner. P01-RTI-05 owns query delegation only.

## Input and malformed-input contract

The only lookup identity is the lowercase 64-character SHA-256
`lifecycle_result_digest`. P01-RTI-05 performs no independent digest validation.
It delegates validation to P01-RTI-03. Consequently, malformed identities retain
the authoritative `ValueError("lifecycle_result_digest must be a digest")`
behavior and are never converted into `NOT_FOUND`. A well-formed identity absent
from storage returns `NOT_FOUND`.

No fallback lookup by invocation, database row, admission, paper-result,
history, timestamp, token, symbol, or opportunity identity is permitted.

## Output

The output is the existing immutable P01-RTI-03 `PaperLifecycleReadResult` and
its existing vocabulary:

- `FOUND`
- `NOT_FOUND`
- `CORRUPT`
- `STORAGE_UNAVAILABLE`

For `FOUND`, existing `PaperLifecycleRunSnapshot` and ordered
`PaperLifecycleArtifactSnapshot` values pass through unchanged, including their
contract versions, digests, canonical payloads, identity, and provenance.

## Determinism and read-only behavior

The result depends only on the supplied digest and authoritative persisted
state. Query execution performs no insert, update, delete, upsert, repair,
migration, regeneration, or reconstruction. Corrupt data is reported and never
repaired. P01-RTI-05 introduces no clock, randomness, filesystem-ordering,
provider, network, current-decision-rule, RTI-04, admission, lifecycle,
scheduler, or worker dependency.

## Forbidden scope

This gate adds no HTTP/FastAPI route, public schema, dashboard, provider
runtime, polling, scheduler, worker, queue, wallet, signing, broadcast,
execution, live trading, economic interpretation, realization, or settlement.
It neither invokes nor changes P01-RTI-04. G2 remains blocked and unresolved;
G3, G4, and P09 remain unauthorized.

## Test ownership

Focused RTI-05 coverage owns delegation, exact-identity preservation, direct
result pass-through, the four read outcomes, malformed-input propagation,
ordering/provenance preservation, repeatability, read-only SQL, lack of repair,
and dependency isolation. P01-RTI-03 continues to own its deeper persistence and
corruption-integrity mechanics.

## Local checkpoint

Twelve focused RTI-05 tests, 51 combined P01-RTI-01 through P01-RTI-05
regressions, and the full 1,421-test Python 3.13 suite pass. Module compilation,
whitespace checks, TypeScript typechecks, and all workspace builds pass. One
pre-existing Starlette warning and the known frontend sourcemap warning remain
non-blocking. GitHub CI and merge are pending.
