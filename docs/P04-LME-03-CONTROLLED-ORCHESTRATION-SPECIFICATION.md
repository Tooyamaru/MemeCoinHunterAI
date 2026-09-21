# P04-LME-03 — Controlled Read-Only Diagnostic Orchestration Specification

**Status:** LIMITED IMPLEMENTATION COMPLETE / LOCAL CHECKS PASS / CI PENDING

**Phase:** P04 — Market & Signal Intelligence

**Scope:** one caller-directed composition from a current admitted token and exact pool target into P04-LME-02

**Updated:** 2026-09-21

## 1. Authorization and purpose

The owner requested continuation after P04-LME-02 was merged, then accepted the
recommended limited scope on 2026-09-21. This authorizes the field-level
contract, one orchestration module, one focused test module, minimal exports and
documentation, and the standard PR/CI/merge workflow.

P04-LME-03 defines the smallest useful orchestration above P04-LME-02. It binds
one current P02-T06 token-universe candidate to one exact pool target supplied
by the caller, constructs the existing `OhlcvRequest`, and invokes the existing
one-shot diagnostic exactly once.

It does not discover, rank, recommend, or select a token or pool. It also does
not establish that a caller-supplied pool is economically safe, liquid, or
tradable.

## 2. Existing boundaries remain owners

- P02-T06 owns the current admitted token-universe snapshot.
- `P02T07PredecessorContext` owns the immutable point-in-time predecessor used
  by P02-T07 admission.
- P04-LME-01 owns request identity, response mapping, candle validation, and
  deterministic `PRICE_DIRECTION_1M` evidence.
- P04-LME-02 owns credential lookup, one bounded HTTP attempt, receipt timing,
  and one-shot diagnostic composition.
- The caller owns the exact pool-target decision and the provenance of that
  decision. P04-LME-03 preserves that reference but does not create or approve
  it.

P04-LME-03 must compose these owners rather than duplicate their validation or
manufacture accepted P02/P04 evidence.

## 3. Immutable input

The implementation introduces an immutable `ExactPoolDiagnosticTarget`
containing only:

1. `chain_id`, fixed to canonical `solana`;
2. exact candidate `token_mint`;
3. exact `pool_address`;
4. exact `base_mint` and `quote_mint` in source order;
5. `target_reference_id` owned by the caller, matching
   `[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}`;
6. lowercase SHA-256 `target_reference_digest`; and
7. `target_contract_version`, matching
   `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`.

The orchestration call must also receive explicitly:

- one `P02T07PredecessorContext`;
- one timezone-aware request `reference_time`;
- one finite positive request timeout;
- one response-size limit already allowed by `OhlcvRequest`;
- one explicit `FreshnessPolicy`; and
- optional injected environment, diagnostic function, and clock for testing.

The target reference is provenance for the caller's exact choice. Its presence
does not convert an inspection report, browser input, symbol, or token name into
source authority.

## 4. Required validation order

The orchestration must fail closed in this order before any credential lookup
or network call:

1. require exact supported input types;
2. validate the target reference fields and SHA-256 digest shape;
3. construct `OhlcvRequest`, thereby applying the existing Solana address,
   pool-composition, time, timeout, and size validation; and
4. require that the predecessor snapshot contains the exact
   `(chain_id, token_mint)` candidate; and
5. only then invoke P04-LME-02 once with the original predecessor and freshness
   policy.

The orchestration must not:

- search for a pool;
- choose the highest-liquidity or highest-volume pool;
- infer identity from symbol, name, URL, or display metadata;
- substitute another token, pool, base mint, or quote mint;
- repair an invalid predecessor;
- read the API key when target admission fails; or
- retry a diagnostic result.

## 5. Result contract

The implementation introduces immutable `ControlledDiagnosticResult` and
`ControlledDiagnosticOutcome` values with exactly these orchestration states:

- `DIAGNOSTIC_COMPLETED`: the existing diagnostic was invoked once; its own
  `PriceDirectionResult.outcome` remains authoritative for provider, mapping,
  admission, and signal results;
- `TOKEN_NOT_CURRENT`: the exact candidate was absent from the supplied
  predecessor snapshot and no diagnostic was invoked; or
- `INVALID_INPUT`: the orchestration input could not establish the required
  bounded target and no diagnostic was invoked.

The result must preserve the exact target, target-reference provenance, reason
codes, and constructed request when one exists. It may contain a
`PriceDirectionResult` only after a real diagnostic invocation. It must never
construct accepted observations or signal evidence itself.

`DIAGNOSTIC_COMPLETED` does not mean `PRODUCED`; callers must inspect the nested
P04-LME-02 outcome. Transport failures, authentication failures, rate limits,
invalid responses, stale evidence, and successful signals remain distinguishable.

## 6. Timing and side-effect boundary

- `reference_time` remains the pre-request closed-minute cutoff.
- P04-LME-02 remains the sole owner of request start, receipt, and post-receipt
  evaluation clocks.
- One orchestration call may cause at most one P04-LME-02 diagnostic call.
- The implementation adds no loop, sleep, retry, scheduler, worker, queue,
  persistence, cache, database write, API route, WebSocket publication, or UI.
- No result automatically enters P04/P05 canonical production, P06 decisions,
  paper simulation, risk authorization, or execution.

## 7. Secret and trust boundary

P04-LME-03 must not read, store, log, hash, return, or inspect the CoinGecko API
key. It passes the optional environment mapping unchanged to P04-LME-02 only
after all preflight validation succeeds.

The target reference digest is not a credential and must not be treated as
proof of external truth. Browser-supplied data cannot become authoritative
merely by hashing it.

## 8. Implementation files

The approved limited implementation may add only:

- `core/data/coingecko_onchain_orchestration.py`;
- `tests/test_coingecko_onchain_orchestration.py`; and
- minimal exports and documentation updates required by those files.

No dependency, migration, configuration value, API endpoint, worker, or
frontend file is authorized by this specification.

## 9. Verification gate

Offline tests must prove:

1. an exact current candidate and exact target produce one existing
   `OhlcvRequest` and one diagnostic call;
2. a missing candidate returns `TOKEN_NOT_CURRENT` with zero secret access and
   zero diagnostic calls;
3. invalid target identity, composition, digest, time, timeout, size, or
   freshness fails closed before the diagnostic;
4. no target field is inferred or rewritten;
5. target-reference provenance survives unchanged in the wrapper result;
6. every nested P04-LME-02 outcome is preserved without reinterpretation;
7. one mocked successful call reaches the real P02-T07/T08/T09 and P04 signal
   path;
8. replay with identical inputs and injected facts is deterministic; and
9. no selection, polling, retry, persistence, wallet, signing, execution, G2,
   G3, G4, or P09 behavior is reachable.

Focused P04-LME regression tests, relevant P02 admission tests, compilation,
`git diff --check`, and the locked Python 3.13/TypeScript CI gates must pass.
CI remains offline and credential-free.

## 10. Exit and following gate

The two approved Python/test files and documentation are implemented. Forty-five
focused tests and 284 combined P02/P04 targeted/regression tests pass locally;
module compilation and `git diff --check` also pass. P04-LME-03 exits only after
review and the locked CI gates pass. Owner acceptance does not authorize any
following runtime boundary.

Continuous polling, application/API wiring, persistence, dashboard publication,
paper automation, live provider verification, pool selection, wallet access,
signing, broadcast, transaction execution, G2, G3, G4, and P09 each remain
outside this boundary and require later decisions.
