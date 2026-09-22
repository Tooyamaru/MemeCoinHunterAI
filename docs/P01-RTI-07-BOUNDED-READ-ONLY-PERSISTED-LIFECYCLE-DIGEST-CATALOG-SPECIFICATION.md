# P01-RTI-07 — Bounded Read-Only Persisted Lifecycle Digest Catalog

## 1. Status

IMPLEMENTED / LOCAL VERIFICATION PASS / CI PENDING

The owner approved the P01-RTI-07 specification direction and authorized final
reconciliation plus limited implementation on 2026-09-22. This specification
is the controlling contract for that implementation.

## 2. Purpose

P01-RTI-07 provides one HTTP-independent application query for discovering a
bounded page of canonical `lifecycle_result_digest` identities already present
in the append-only P01-RTI-03 root store. It does not return lifecycle details
or certify complete bundle integrity.

The dependency direction is fixed:

```text
explicit limit and optional after_digest
    -> P01-RTI-07 application catalog
    -> bounded PaperLifecycleRepository root-digest select
    -> immutable P01-RTI-07 page result
```

Complete detail lookup remains:

```text
explicit lifecycle_result_digest
    -> P01-RTI-05
    -> P01-RTI-03 read and integrity owner
```

## 3. Ownership

- P01-RTI-07 owns catalog input validation, bounded query orchestration, page
  outcome semantics, and its canonical result digest.
- P01-RTI-03 remains the owner of canonical lifecycle digest syntax. RTI-07
  must reuse its authoritative validator rather than copy a regex or parser.
- P01-RTI-03 remains the sole complete bundle persistence, snapshot,
  corruption, artifact-integrity, and artifact-ordering owner.
- P01-RTI-05 remains the complete single-result application query owner.
- P01-RTI-04 is not invoked or modified.
- P01-RTI-06 is not invoked or modified and gains no collection route.

## 4. Application input contract

The query accepts keyword-only inputs:

- `limit`: integer, default `50`, minimum `1`, hard maximum `100`; and
- `after_digest`: optional canonical lifecycle result digest.

`bool`, non-integer, zero, negative, and values above `100` are malformed and
raise an application `ValueError`. A malformed `after_digest` also raises
`ValueError` using the authoritative P01-RTI-03 validation semantics. Malformed
input is not converted into a page or storage outcome.

There is no input by offset, page number, timestamp, database row ID,
invocation ID, admission digest, paper-result digest, history digest, token,
symbol, pool, opportunity, wallet, or other secondary identity.

## 5. Ordering and continuation

The repository selects only `paper_lifecycle_runs.lifecycle_result_digest` and
orders it lexicographically ascending. Database ID, insertion order, and
`created_at` are not read or exposed.

Continuation is exclusive keyset pagination:

```text
lifecycle_result_digest > after_digest
ORDER BY lifecycle_result_digest ASC
```

The service requests at most `limit + 1` identities, returns at most `limit`,
and sets `next_after_digest` to the final returned digest only when the extra
identity proves another page exists. Callers pass that value as the next
`after_digest`. Offset pagination is forbidden.

A valid cursor need not identify an existing row. It is a lexical boundary. If
no identity sorts after it, the result is a successful empty page.

## 6. Outcome vocabulary

The closed outcome vocabulary is:

- `PAGE`: the bounded read completed, including an empty catalog or empty
  continuation page; and
- `STORAGE_UNAVAILABLE`: database runtime or bounded repository read failed.

There is no `NOT_FOUND`, `FOUND`, or `CORRUPT` catalog outcome. Catalog
presence means only that a root identity exists. It must never be presented as
the complete-bundle `PaperLifecycleReadOutcome.FOUND` owned by P01-RTI-03.

Canonical reason codes are:

- no reasons for `PAGE`;
- `DATABASE_UNAVAILABLE` when no connected database session boundary exists;
  and
- `DATABASE_READ_FAILED` when the bounded select fails.

Storage failures expose no identities, continuation value, SQL, connection
details, credentials, payloads, exception text, or stack traces.
Malformed or non-canonical identity data returned by the repository also fails
closed as `STORAGE_UNAVAILABLE` / `DATABASE_READ_FAILED`; it is never emitted
and does not create a separate corruption vocabulary.

## 7. Immutable result contract

`PaperLifecycleDigestCatalogResult` contains exactly:

- `contract_version`: `p01-rti-07-v1`;
- `outcome`: `PAGE` or `STORAGE_UNAVAILABLE`;
- `reason_codes`: immutable canonical tuple;
- `limit`: the validated requested bound;
- `after_digest`: the validated optional input cursor;
- `lifecycle_result_digests`: immutable ordered tuple, length at most `limit`;
- `next_after_digest`: final returned digest only when another page exists; and
- `result_digest`: lowercase SHA-256 of the canonical representation of every
  preceding field.

The result is immutable. Digest order must be strictly ascending with no
duplicates, every returned digest must sort after `after_digest`, and a
continuation value must equal the last returned digest. Supplying a mismatched
`result_digest` is invalid.

## 8. Read-only and integrity boundary

P01-RTI-07 reads only root digest values. It performs no artifact query, root
snapshot construction, artifact ordering, payload parsing, digest-linkage
checking, lifecycle reconstruction, or full-bundle integrity validation.

A corrupt root may therefore appear as a catalog identity. A caller that needs
the authoritative state selects that digest through P01-RTI-05, where
P01-RTI-03 returns `FOUND`, `NOT_FOUND`, `CORRUPT`, or `STORAGE_UNAVAILABLE`.

P01-RTI-07 performs no insert, update, delete, upsert, repair, migration,
regeneration, retry, or automatic correction.

## 9. Determinism

For identical validated inputs and unchanged persisted root identities, the
complete result and `result_digest` are identical. The query has no dependency
on wall clock, operational timestamps, randomness, filesystem order, provider,
network, current market state, decision policy, RTI-04 execution, scheduler,
worker, or mutable ambient state.

The store is append-only, so a later query may observe newly appended roots.
P01-RTI-07 does not claim a multi-page snapshot across separate calls. Within
unchanged state, exclusive keyset traversal has no duplicate or missing
identity.

## 10. Authorized implementation shape

The implementation may add only:

- one small application module containing the immutable result and service;
- one bounded digest-only method on the existing repository;
- a public delegation point for the existing authoritative RTI-03 lifecycle
  digest validator without changing RTI-03 read behavior;
- focused offline tests and exports; and
- specification and checkpoint documentation.

No model, migration, dependency, HTTP route, public API schema, frontend,
dashboard, provider, network call, worker, scheduler, queue, wallet, signing,
broadcast, execution, live trading, realization, settlement, economic metric,
G2, G3, G4, or P09 behavior is authorized.

## 11. Verification requirements

Focused tests must establish:

1. empty storage returns a successful empty `PAGE`;
2. default `50`, allowed maximum `100`, and rejected invalid limits;
3. lexicographic ordering independent of insertion order/timestamps;
4. exclusive keyset continuation and bounded `limit + 1` probing;
5. valid non-existing cursors work as lexical boundaries;
6. malformed cursors reuse RTI-03 validation and raise `ValueError`;
7. immutable output and canonical deterministic `result_digest`;
8. database-unavailable and read-failure outcomes are bounded and safe;
9. root identities can be listed without artifact or full-bundle validation;
10. only `SELECT` occurs and storage is not mutated;
11. no transport, provider, execution, worker, scheduler, dashboard, wallet,
    G2, G3, G4, or P09 dependency; and
12. RTI-03, RTI-04, RTI-05, and RTI-06 regressions remain unchanged and green.

Focused tests, relevant RTI regressions, the full Python suite, module
compilation, whitespace checks, TypeScript typechecks/builds, and required
GitHub CI must pass before closure.

The implementation checkpoint passes 21 focused tests, 37 relevant
RTI-03/05/06 regressions, 86 combined P01-RTI-01 through RTI-07 regressions,
and the full 1,456-test Python 3.13 suite. Module compilation, whitespace
checks, TypeScript typechecks, and all workspace builds also pass locally.

## 12. Following gate

P01-RTI-07 authorizes no HTTP collection route. Any transport for this catalog,
filter/search/latest/history behavior, richer projection, dashboard use,
provider runtime, or operational loop requires a separate specification and
explicit approval. No next gate is selected automatically by completion.
