# P04-LME-01 — Live Market Evidence and Signal Policy Specification

**Status:** OWNER ACCEPTED / LIMITED OFFLINE IMPLEMENTATION AUTHORIZED
**Phase:** P04 — Market & Signal Intelligence  
**Scope:** source decision, canonical mapping, and deterministic signal policy  
**Updated:** 2026-09-21

## 1. Decision

The V1 source owner for canonical historical price evidence is the CoinGecko
Demo Onchain API pool-OHLCV endpoint. The source is authoritative only for the
analytical observation received from that endpoint. It is not authoritative
for settlement, wallet state, execution, accounting, or G2 realization.

The selected endpoint is:

```text
GET https://api.coingecko.com/api/v3/onchain/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}
```

The V1 Solana request profile is fixed to:

```text
network=solana
timeframe=minute
aggregate=1
limit=3
currency=usd
token={exact candidate token mint}
include_empty_intervals=false
before_timestamp={closed-minute cutoff}
```

Authentication uses the `x-cg-demo-api-key` header. The secret name is
`COINGECKO_DEMO_API_KEY`; it is server-side only and must never appear in a URL,
browser request, log, fixture, digest, or repository file.

The official endpoint documentation states that the response contains OHLCV
rows shaped as `[timestamp, open, high, low, close, volume]`, timestamps are
Unix epoch values, `before_timestamp` supports historical pagination, the
response includes base/quote token addresses, and empty intervals are skipped
unless explicitly requested:

- https://docs.coingecko.com/demo/reference/pool-ohlcv-contract-address
- https://docs.coingecko.com/demo/reference/authentication

Bitquery is retained as a future independent audit/backfill candidate, not a
V1 runtime dependency. Its Solana DEX API exposes trade, pool, transaction, and
block-time identity and separates recent/realtime from archive behavior:

- https://docs.bitquery.io/docs/blockchain/Solana/solana-dextrades/

No automatic source failover is authorized. Silent fallback would change the
meaning of evidence and could mix incompatible price construction semantics.

## 2. Architectural position

```text
approved candidate + exact pool identity
    -> bounded CoinGecko OHLCV request
    -> source-shaped response envelope
    -> identity/time/content validation
    -> accepted P02-T09 price observations
    -> deterministic P04-LME-01 signal evidence
    -> existing canonical evidence producer
    -> existing P04/P05 chain
```

This task closes the specification gap between a provider response and the
already-implemented `produce_canonical_p04_to_p05` input contract. It does not
replace or modify P02 admission, P03 safety, P04 normalization/quality/
evaluation/aggregation, P05 scoring, P06 decisions, or the Risk Governor.

## 3. Inputs

The future implementation must receive all of the following explicitly:

1. `chain_id`, fixed to the repository's canonical Solana identity.
2. Exact candidate token mint.
3. Exact selected pool address.
4. Exact pool base-token and quote-token identities from the admitted
   inspection/candidate context.
5. Timezone-aware `reference_time` supplied by the caller.
6. Explicit request timeout and response-size limits.
7. A server-side API key supplied through environment secrets.

The producer must not search for a different pool, select a top pool, infer a
token from symbol/name, or accept browser-supplied source authority.

## 4. Request cutoff

The request must exclude the currently forming one-minute candle.

```text
closed_minute_cutoff = floor(reference_time_utc_epoch / 60) * 60
before_timestamp = closed_minute_cutoff
```

The adapter requests exactly three rows. Returned rows are canonically sorted
by provider timestamp ascending after validation. A row at or after the cutoff
is rejected. Future timestamps, duplicate timestamps, non-monotonic ordering,
and intervals other than exactly 60 seconds fail closed.

Because `include_empty_intervals=false`, missing swap intervals are not filled
or interpolated. If the three most recent returned candles are not contiguous,
the result is `INSUFFICIENT_HISTORY`; no velocity, acceleration, or favorable
signal may be produced.

## 5. Source envelope and provenance

The source-shaped result must preserve:

- provider ID: `coingecko-onchain-demo`;
- endpoint contract version;
- HTTP response status;
- provider request ID from `data.id` when present;
- canonical network ID;
- pool address;
- requested token mint;
- returned base and quote token addresses;
- request parameters excluding credentials;
- request start and receipt timestamps;
- raw candle timestamps;
- SHA-256 digest of bounded response bytes;
- adapter version;
- explicit success/failure outcome and reason codes.

Raw response bytes may be retained only within the bounded diagnostic result or
an explicitly authorized persistence boundary. The API key is never included
in provenance or canonical material.

## 6. Identity validation

The exact requested token mint must match either `meta.base.address` or
`meta.quote.address`. The supplied pool composition and returned composition
must agree after chain-appropriate canonicalization. Symbols, names, and
CoinGecko coin IDs are descriptive only and cannot establish identity.

The adapter must reject:

- network mismatch;
- pool-address mismatch in caller context;
- requested token absent from returned composition;
- base/quote identity contradiction;
- a selected pool that does not contain the candidate token;
- empty, malformed, oversized, or unexpected response structures.

No cross-pool aggregation is allowed in V1.

## 7. Numeric and time mapping

JSON numbers must be parsed directly into `Decimal`; binary `float` must not be
used as an intermediate representation. Every OHLCV value must be finite and
non-negative; open/high/low/close must be positive. Candle invariants require:

```text
low <= open <= high
low <= close <= high
volume >= 0
```

For each accepted candle:

- `value` is the exact close price text derived from `Decimal`;
- `observation_time` is the provider candle timestamp converted to aware UTC;
- `received_time` is the injected response-receipt time;
- `reference_time` is the caller-supplied evaluation time;
- category is `PRICE`;
- metadata includes measurement `price`, unit `USD`, quote asset `USD`, pool
  address, interval `60s`, and source response digest;
- source-event identity combines provider, network, pool, token, interval, and
  candle timestamp.

The adapter then submits the values through the existing P02 admission and
market-intelligence contracts. It must not instantiate accepted P02-T09 values
by bypassing their processors.

## 8. Deterministic signal policy

The approved V1 policy is observational and non-predictive:

```text
policy_version = price-direction-v1
signal_type = PRICE_DIRECTION_1M
delta = latest_close - previous_close

delta > 0  -> signal_status = RISING
delta < 0  -> signal_status = FALLING
delta = 0  -> signal_status = FLAT
```

The evidence uses the latest two of the three validated closed candles. Its
`observed_at` equals the latest candle timestamp. Its evidence reference is a
digest-bound reference to the exact accepted price observations and source
response. Reason codes are respectively:

- `PRICE_CLOSE_INCREASED`;
- `PRICE_CLOSE_DECREASED`;
- `PRICE_CLOSE_UNCHANGED`.

`confidence=1.0` means only that the deterministic classification has complete,
valid V1 inputs. It is not a probability of future price movement, a win-rate
estimate, or trading confidence.

This signal is never translated directly into `BUY`, `SELL`, entry, exit,
position size, or authorization. Existing P05 scoring continues to use the
separately calculated price velocity and acceleration feature snapshots.

## 9. Fail-closed outcomes

The future result taxonomy must include at least:

- `PRODUCED`;
- `SOURCE_UNAVAILABLE`;
- `AUTHENTICATION_FAILED`;
- `RATE_LIMITED`;
- `TIMEOUT`;
- `RESPONSE_TOO_LARGE`;
- `INVALID_RESPONSE`;
- `IDENTITY_MISMATCH`;
- `TEMPORAL_INVALID`;
- `INSUFFICIENT_HISTORY`;
- `CONTRADICTORY_EVIDENCE`;
- `UPSTREAM_ADMISSION_REJECTED`.

Every non-`PRODUCED` result must contain no `SignalEvidenceCollection` and no
favorable default. Retryability is explicit metadata; retrying is owned by a
later orchestration task.

HTTP behavior maps as follows:

- `401/403` -> `AUTHENTICATION_FAILED`;
- `429` -> `RATE_LIMITED`;
- timeout -> `TIMEOUT`;
- other non-2xx -> `SOURCE_UNAVAILABLE` unless a more specific documented
  mapping applies;
- invalid JSON/schema/numeric material -> `INVALID_RESPONSE`.

## 10. Determinism and replay

The pure mapping layer receives response bytes, request context, and receipt
time explicitly. It performs no wall-clock lookup or network call. Equivalent
inputs must produce byte-equivalent canonical representations and identical
digests.

Replay must preserve the originally captured provider response and receipt
time. A later provider revision must create new evidence; it must never rewrite
historical evidence in place.

## 11. Security and operational limits

- API calls are server-side only.
- Redirects are disabled.
- Host and path are fixed by configuration, not arbitrary user input.
- Pool and token identities are validated before URL construction.
- Timeouts and response-size limits are mandatory.
- Logs contain bounded reason codes and request IDs, not secrets or complete
  provider payloads.
- Provider data is untrusted input.
- No wallet, signing, broadcast, transaction submission, or live execution is
  introduced.

## 12. Required tests for implementation authorization

Focused offline tests must cover:

1. Valid three-candle rising, falling, and flat paths.
2. Exact token/pool/base/quote binding.
3. Candidate token returned as base and as quote.
4. Deterministic decimal parsing and digest replay.
5. Exclusion of the forming candle.
6. Duplicate, missing, non-contiguous, out-of-order, and future candles.
7. Invalid OHLC invariants, negative volume, NaN/infinity, and malformed JSON.
8. Timeout, size limit, 401/403, 429, and generic upstream failure.
9. API-key absence and proof that credentials never enter URLs/logs/digests.
10. P02 admission rejection propagation.
11. Exact production of P04-T01 evidence without bypassing P02.
12. End-to-end offline fixture into the existing canonical P04/P05 producer.
13. Proof that no wallet, execution, provider fallback, or trading action is
    reachable.

Live-provider verification, when separately approved, is diagnostic-only and
must not assert that historical availability or provider correctness is
permanent.

## 13. Proposed implementation scope

The owner explicitly accepted this specification and authorized limited
implementation on 2026-09-21. The authorization permits only:

- `core/data/coingecko_onchain_ohlcv.py` — bounded source envelope and pure
  response mapping;
- `core/signals/price_direction_policy.py` — deterministic V1 mapping;
- `tests/fixtures/coingecko_onchain/pool_ohlcv.json` — sanitized offline fixture;
- `tests/test_coingecko_onchain_ohlcv.py`;
- `tests/test_price_direction_policy.py`;
- minimal exports and project-state documentation needed for those files.

Connecting the API/UI, scheduling polling, durable persistence, provider
fallback, broader indicators, paper-trading automation, wallet integration,
G2, and live execution require separate authorization.

## 14. Acceptance gate

The specification gate passes only when the owner accepts:

1. CoinGecko Demo Onchain pool OHLCV as the V1 analytical source owner.
2. Exact-pool, exact-token, closed-candle semantics.
3. No interpolation and fail-closed gaps.
4. `PRICE_DIRECTION_1M` as observational evidence only.
5. The proposed limited implementation file scope.

Owner acceptance and limited implementation authorization were recorded on
2026-09-21. The live application path remains blocked. This authorization
covers offline mapping and tests, not live-provider verification or application
wiring.

## 15. Limited implementation notes

- `map_pool_ohlcv` consumes a credential-free `OhlcvRequest`, a source response
  envelope, an actual caller-supplied `P02T07PredecessorContext`, and an explicit
  `FreshnessPolicy` with a finite `stale_after`. It does not invent admission or
  silently relax freshness to fit three minutes of history.
- Each candle passes through fresh local T07 admission, T08 materialization,
  and T09 representation processors. A failed candle discards the entire local
  result; no partial accepted history escapes and caller state is unchanged.
- Strictly ascending and strictly descending provider order are supported;
  mixed ordering is rejected before canonical ascending ordering. Duplicate
  timestamps with different rows are contradictory; identical repeats are
  temporally invalid. Neither produces a signal.
- Candle timestamps retain their interval-start semantics. The complete
  interval must have ended by receipt, and receipt must not exceed evaluation
  time. The three-candle freshness threshold remains an explicit caller policy.
- The documented response does not echo pool/network identity. Binding is
  therefore to the exact trusted request envelope plus returned base/quote
  composition, not a claim of independently proven pool identity. No browser
  or arbitrary caller can establish source authority with a self-labeled payload.
- Defensive limits: at most 1 MiB of response bytes, 128 decimal digits,
  absolute decimal exponent at most 100, numeric text at most 160 characters,
  and request IDs at most 128 safe characters. Duplicate JSON keys, unexpected
  structures, invalid UTF-8, non-finite numbers, and numeric strings fail closed.
- `prepare_authenticated_request` only prepares a header from the caller's
  server-side `COINGECKO_DEMO_API_KEY` value. Missing/invalid credentials raise a
  generic `AUTHENTICATION_FAILED`; credentials never enter mapper inputs, URLs,
  normal object representations, or canonical evidence. No environment lookup,
  HTTP client, redirect handling, or streaming transport is implemented. Future
  transport must enforce timeout/size bounds while reading and disable redirects.
- `derive_price_direction` always invokes the mapper on original inputs, so a
  caller-constructed accepted observation cannot shortcut validation. Comparing
  the two exact Decimals implements the sign of delta without ambient rounding.
  Signal references bind policy version, response digest, accepted observation
  IDs/fingerprints, and T08 state digests.
- The fixture is synthetic offline data with syntactically valid addresses. It
  is not evidence that those addresses form a real pool or that live historical
  data is available. No real credential is needed for any test.
