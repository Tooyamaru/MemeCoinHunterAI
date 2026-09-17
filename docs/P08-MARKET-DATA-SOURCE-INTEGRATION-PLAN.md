# P08 — Market-Data Source Integration Plan

**Status:** IMPLEMENTATION BLOCKERS CONFIRMED / INSPECTION TOOL RECOMMENDED
**Contract:** `p08-read-only-market-data-observation-v1`
**Scope:** Official CoinGecko and DexScreener documentation only
**Implementation authorization:** None

## 1. Decision

Neither considered source can currently produce an accepted P08 observation
without undocumented semantics or derived values. The recommended next scope is
therefore a minimal, read-only DexScreener fetch-and-inspect tool for one
explicit token address. It must preserve the source response and report
unavailable P08 evidence; it must not construct a `ReadOnlyMarketDataObservation`,
claim P08 acceptance, feed discovery or decisions, or authorize paper admission.

DexScreener is recommended for this narrow inspection scope because its official
endpoint is address-scoped, its documentation exposes pair market fields, and
the documented endpoint does not require a CoinGecko plan or API key. This is
not a recommendation that DexScreener satisfies the P08 contract. CoinGecko
remains a conditional comparison only; its documented on-chain endpoints use
API-key authentication and still lack the source semantics required for P08.

The audited validator and downstream contracts remain unchanged. Do not change
`required_fields` to make incomplete source data appear accepted.

## 2. Required versus optional metrics

The distinction is between structural metric presence and consumer acceptance.
The implementation defines `_REQUIRED_METRICS` as
`{"price", "liquidity", "volume", "asset_age"}` and `_OPTIONAL_METRICS` as
`{"holders", "transactions"}` in
`core/data/read_only_market_data.py`.

`_check_observation_structure` requires all four names in `_REQUIRED_METRICS` to
exist in `observation.metrics`. It does not require all four to be
`PRESENT` at that structural step. `_check_metric` permits `MISSING`,
`UNAVAILABLE`, and `INVALID` only with `value=None`; a `PRESENT` metric must
have a value, unit, semantic version, and any metric-specific context.
`_check_metrics` then applies the caller-supplied
`EvaluationContext.required_fields` and
`EvaluationContext.permitted_optional_fields`:

- a required field that is absent or `MISSING` returns `INCOMPLETE_INPUT`;
- a required field that is `UNAVAILABLE` or `INVALID` returns
  `UNAVAILABLE_INPUT`;
- any `UNAVAILABLE` or `INVALID` metric present in the mapping also returns
  `UNAVAILABLE_INPUT`, even when it is not required;
- an optional `holders` or `transactions` envelope is rejected as
  `UNSUPPORTED_FIELD` unless its name is in `permitted_optional_fields`;
- an optional field may be omitted entirely; and
- `PRESENT` is not universally mandatory in the validator, but is mandatory
  for every field that the selected consumer profile puts in
  `required_fields`.

The relevant implementation symbols are `_REQUIRED_METRICS`,
`_OPTIONAL_METRICS`, `_check_observation_structure`, `_check_metric`,
`_check_metrics`, and `validate_observation`.

| Metric | Envelope must exist in a P08 observation? | When must it be `PRESENT`? | Is `MISSING`/`UNAVAILABLE` permitted? | Current consumer rule |
|---|---:|---|---|---|
| `price` | Yes; it is in `_REQUIRED_METRICS` and Section 7 of the specification. | When `price` is in `required_fields`; discovery requires every selected required field, and a paper profile using market conditions must require it. | Structurally yes with `value: null`; acceptance no when required. | `tests/test_read_only_market_data.py` fixture `context()` uses `("asset_age", "liquidity", "price", "volume")`. |
| `liquidity` | Yes; it is in `_REQUIRED_METRICS`. | Same required-field rule as `price`. | Structurally yes; a required missing/unavailable value fails closed. | Same focused paper-evaluation fixture; Section 10.2 requires it for market-condition profiles. |
| `volume` | Yes; it is in `_REQUIRED_METRICS`. | Same required-field rule, and `_check_metric` requires a `measurement_window` when it is `PRESENT`. | Structurally yes; a required missing/unavailable value fails closed. | Same focused fixture; Section 10.2 requires it for market-condition profiles. |
| `asset_age` | Yes; it is in `_REQUIRED_METRICS`. | Same required-field rule, and `_check_metric` requires `reference_semantics` when it is `PRESENT`. | Structurally yes; a required missing/unavailable value fails closed. | Same focused fixture; Section 10.2 expressly requires asset-age semantics for market-condition profiles. |
| `holders` | No. It is optional and may be omitted. | Only when explicitly included in `required_fields` and permitted by the profile. | Omission is allowed; an explicit unavailable/invalid envelope still produces `UNAVAILABLE_INPUT`. | Section 10 permits it only when explicitly supplied and version-authorized. |
| `transactions` | No. It is optional and may be omitted. | Only when explicitly included in `required_fields` and permitted; `_check_metric` also requires a `measurement_window` when `PRESENT`. | Omission is allowed; an explicit unavailable/invalid envelope still produces `UNAVAILABLE_INPUT`. | Section 10 permits it only when explicitly supplied and version-authorized. |

The normative rules are `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION.md`
Sections 5, 7, 10.1, and 10.2. The code does not contain a production profile
registry: requiredness is caller-supplied through `EvaluationContext`. The
focused test fixture is evidence of the current exercised
`paper-evaluation-v1` shape, not permission to change downstream profiles.

## 3. Timestamp compatibility

`observed_at` is required for every observation by the Section 5 top-level
contract. The implementation checks it in `_check_observation_structure` and
uses it for freshness in `_check_freshness`. The required relationship is:

```text
observed_at <= availability_at <= evaluation_context.cutoff_time
```

`source.source_observed_at` is nullable at the structural level, but when it is
present `_check_provenance_links` requires exact equality with
`observation.observed_at`. Provenance also copies `observed_at` and
`availability_at`; these are not interchangeable.

For this plan:

- a source observation time must describe the returned market fields, not merely
  a related event;
- local receipt time is retained as `received_at` in the inspection report and
  is never emitted as P08 `observed_at`;
- HTTP `Date` and fetch/processing time are local transport facts, not source
  observation facts;
- DexScreener `pairCreatedAt` is pair creation time, not observation time; and
- CoinGecko `last_trade_timestamp` is documented as last-trade time, not as the
  observation instant for price, reserve, and rolling volume in the response.

Using any of those timestamps as `observed_at` would require undocumented
matching semantics and would violate Section 9 rules 8–10. The inspection tool
must therefore output `p08_observed_at: null` and an explicit
`p08_acceptance: "NOT_ATTEMPTED"` for every result.

## 4. Confirmed and conditional source blockers

### 4.1 CoinGecko

The official candidate endpoints are:

```text
GET https://pro-api.coingecko.com/api/v3/onchain/tokens/multi?tokens=<network>:<address>
GET https://pro-api.coingecko.com/api/v3/onchain/simple/networks/{network}/token_price/{addresses}
```

The documentation shows the `x-cg-pro-api-key` header. The simple token-price
endpoint documents up to 100 addresses, `token_prices`,
`h24_volume_usd`, `total_reserve_in_usd`, and `last_trade_timestamp`.
The multi-token endpoint documents token identity, price, reserve, rolling
volume, transactions in included pool data, and last-trade fields.

Confirmed blockers:

1. no documented source-supplied token-origin or asset-age value;
2. `last_trade_timestamp` is not documented as a complete market snapshot
   observation time;
3. rolling `h24` values are named windows but no exact UTC start and end
   timestamps are supplied for the P08 `TimeWindow`; and
4. `total_reserve_in_usd` is not documented as the P08 liquidity semantic and
   would need an approved source-field semantic contract.

Conditional issues:

- API-key and plan access are transport requirements, not proof of semantic
  compatibility;
- `price_usd`/`token_prices` could map to P08 price if a source contract
  supplies compatible snapshot timing; and
- `total_reserve_in_usd` could be retained as an inspectable source field, but
  must remain unavailable for P08 liquidity unless its semantic equivalence is
  separately approved.

The official rate-limit documentation says paid limits depend on plan, demo
access is 100 calls/minute, and keyless access is IP-rate-limited. The plan
does not recommend acquiring a paid CoinGecko plan.

### 4.2 DexScreener

The official lookup endpoint selected for the inspection tool is:

```text
GET https://api.dexscreener.com/token-pairs/v1/{chainId}/{tokenAddress}
```

The official API reference documents a 300-requests-per-minute limit for this
endpoint and returns pools/pairs for the supplied token address. Pair records
document price, liquidity, volume, transactions, and `pairCreatedAt`.
The endpoint is an address/pair lookup, not candidate discovery.

Confirmed blockers for P08 acceptance:

1. no market-field observation/update timestamp is documented;
2. `pairCreatedAt` is pair creation time, not token age and not observation
   time; and
3. rolling fields such as `volume.h24` do not include exact UTC window
   endpoints.

Conditional issues:

- a token may return multiple pairs, so the inspector must retain every returned
  pair and must not choose, aggregate, or rank one;
- `priceUsd` and `liquidity.usd` are inspectable source fields but cannot be
  treated as a validated P08 snapshot without source timing; and
- `transactions.h24` is optional source evidence only and cannot repair missing
  required volume or asset age.

The absence of a documented authorization header for this DexScreener endpoint
supports the no-credential inspection scope; it does not establish authority,
freshness, or P08 acceptance.

### 4.3 Discovery versus lookup

`/token-pairs/v1/{chainId}/{tokenAddress}` and CoinGecko’s address endpoints
inspect a token that the caller already selected. They do not discover a
candidate universe.

DexScreener `/latest/dex/search?q` and CoinGecko
`/onchain/search/pools?query=...` are search/discovery-like endpoints, but their
results are not safety, eligibility, liquidity, or authorization decisions.
They are out of the minimal scope. No search result may be promoted into a P08
candidate without a separately authorized discovery translation and profile.

## 5. Recommended implementation scope: DexScreener inspection only

This is the one concrete recommended next implementation. It produces
inspectable real source data while explicitly preserving the unresolved P08
evidence. It does not resolve downstream eligibility.

### 5.1 Exact future files requiring authorization

No files in this section are authorized now. A future authorization should name
exactly:

```text
core/data/dexscreener_transport.py
core/data/dexscreener_inspection.py
tests/test_dexscreener_inspection.py
tests/fixtures/dexscreener/token_pairs.json
```

Responsibilities:

1. `dexscreener_transport.py` performs one bounded HTTPS request and returns raw
   response bytes plus explicit transport metadata. It does not normalize
   market fields.
2. `dexscreener_inspection.py` parses and normalizes the response for human and
   test inspection. It must retain every returned pair, keep source field names,
   expose unavailable P08 evidence, and provide the proposed CLI.
3. `tests/test_dexscreener_inspection.py` tests transport and normalization
   offline with no provider calls.
4. `tests/fixtures/dexscreener/token_pairs.json` is a bounded, redacted,
   deterministic fixture containing the official response shape; it is not a
   live cache.

The inspector must not import or modify
`core/data/read_only_market_data.py`, and it must not return
`ValidationResult(VALID)`.

### 5.2 Bounded request and retry policy

One invocation accepts exactly one explicit `chain_id` and one token address:

- request count: at most 1 initial request plus 1 retry;
- endpoint: `/token-pairs/v1/{chainId}/{tokenAddress}`;
- timeout: 10 seconds per attempt;
- response-size limit: 1 MiB; reject, never truncate, larger responses;
- pair-count limit: 128 returned pairs; reject, never truncate, larger arrays;
- retry: one fixed 1-second retry only for HTTP 408, 429, 500, 502, 503, or
  504 and transport connection/reset failures;
- no retry for 400, 401, 403, 404, malformed JSON, oversized responses, or
  invalid source shapes; and
- no pagination, search, batching, pair selection, aggregation, ranking, or
  fallback provider.

The retry count, HTTP status, response byte count, endpoint, and local receipt
time must be included in the inspection provenance. No retry may change or
invent a source observation time.

### 5.3 Lossless normalization and provenance

The inspector must:

- hash the exact response bytes before parsing as `raw_payload_sha256`;
- parse JSON numeric tokens without binary floating point, using decimal-preserving
  parsing and rendering normalized numeric values as strings;
- retain the exact raw payload digest and the source field path for every
  normalized value;
- preserve source strings and decimal scale where the parser can observe them;
- report non-finite, malformed, or unrepresentable numeric fields as explicit
  invalid evidence rather than rounding or dropping them;
- record local `received_at` separately from all source timestamps;
- retain `pairCreatedAt` as `source_pair_created_at` only; and
- emit `p08_observed_at: null`, `asset_age.status: "UNAVAILABLE"`, and
  `p08_acceptance: "NOT_ATTEMPTED"` because the source does not document the
  required semantics.

The output is an inspection report, not a P08 observation. It may include
`priceUsd`, `liquidity.usd`, `volume.*`, and `txns.*` under a source-preserving
`pairs` array, but it must not rename them into accepted P08 metric envelopes
or claim that they satisfy the P08 units, windows, or freshness rules.

### 5.4 Proposed executable manual command

After the four files above receive separate authorization, the manual command
should make one public read-only request for an explicit token and print the
fetched/normalized report:

```text
uv run python -m core.data.dexscreener_inspection \
  --chain-id ethereum \
  --token-address 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
```

Expected top-level output fields are:

```text
tool_version
source
request.endpoint
request.chain_id
request.token_address
request.attempts
receipt.received_at
receipt.http_status
receipt.response_bytes
payload.raw_payload_sha256
payload.pair_count
payload.pairs[]
payload.pairs[].pairAddress
payload.pairs[].chainId
payload.pairs[].dexId
payload.pairs[].baseToken
payload.pairs[].quoteToken
payload.pairs[].priceUsd
payload.pairs[].liquidity
payload.pairs[].volume
payload.pairs[].txns
payload.pairs[].pairCreatedAt
evidence.p08_acceptance
evidence.p08_observed_at
evidence.asset_age.status
evidence.unavailable_fields
```

The command must not print credentials, Authorization headers, or private
payload data. It must make clear that the report is real fetched source data
with local receipt provenance, not an accepted market observation.

## 6. Offline tests and acceptance criteria

The future focused suite must use the fixture and fake transport only. It must
cover:

- exact URL and one-address request construction;
- one-request plus one-retry bounds;
- timeout, connection failure, each retryable status, each non-retryable
  status, malformed JSON, oversized body, and over-limit pair arrays;
- raw-byte SHA-256 preservation;
- decimal and integer values without binary-float conversion or silent
  rounding;
- preservation of every returned pair and source field;
- duplicate pair records and conflicting source fields as explicit inspection
  findings, never implicit selection;
- distinct `received_at` and `pairCreatedAt` fields;
- `p08_observed_at: null` and `p08_acceptance: "NOT_ATTEMPTED"`;
- explicit unavailable asset age and missing exact observation/window evidence;
- zero network calls in normalization tests; and
- no imports or behavior from P05, P06, P07, execution, wallet, persistence,
  or the P08 validator beyond documenting the boundary.

Acceptance criteria for the inspection scope:

1. only the four explicitly authorized future paths are changed;
2. the tool performs at most one request and one bounded retry;
3. the exact source payload is digestable and all returned source fields remain
   inspectable;
4. numeric values are not converted through binary floating point;
5. receipt time is never labeled `observed_at`;
6. pair creation time is never labeled asset age or observation time;
7. no P08 `VALID` result, candidate decision, paper admission, ranking, or
   discovery claim is produced; and
8. focused offline tests and the manual command produce the documented report
   fields.

This alternative delivers inspectable real data but does not resolve downstream
eligibility. A future P08-accepted integration would still require a separate
source contract that supplies a complete market observation timestamp, source
asset-age semantics, and exact volume windows. Relaxing `required_fields` or
relabeling source timestamps would be a contract change requiring a new
specification, audit, implementation authorization, and downstream impact
review; it is not part of this plan.

## 7. Original blockers: confirmed versus conditional

| Original blocker | Determination | Basis |
|---|---|---|
| No documented source observation timestamp for DexScreener market fields | Confirmed | Official endpoint documents pair fields and `pairCreatedAt`, but not a market snapshot/update time. |
| `pairCreatedAt` cannot stand in for `observed_at` or asset age | Confirmed | It is pair creation time and has different semantics. |
| CoinGecko `last_trade_timestamp` cannot automatically stand in for `observed_at` | Confirmed | It is documented as last-trade time, not complete-response observation time. |
| Neither reviewed source supplies P08 asset age | Confirmed | The reviewed official response fields contain no token-origin age value with P08 reference semantics. |
| Rolling `h24` values lack exact P08 `TimeWindow` endpoints | Confirmed for current docs; conditional only if a future source contract documents exact boundaries | Current docs provide window labels, not UTC start/end timestamps. |
| CoinGecko reserve can be P08 liquidity | Conditional, not accepted | Requires a separately approved semantic alias and valuation context. |
| Pair selection can produce one P08 market subject | Conditional, not accepted | Requires a deterministic subject-selection contract; the inspector retains all pairs instead. |
| A source can be used without a credential | Conditional by source | DexScreener’s selected endpoint has no documented auth requirement; CoinGecko’s official examples require API-key headers and plan/rate-limit rules. |

## 8. Official documentation reviewed

Only these official provider pages support the comparison:

- CoinGecko — [Tokens Data by Token Addresses across Networks](https://docs.coingecko.com/reference/tokens-data-contract-addresses-multi)
- CoinGecko — [Token Price by Token Addresses](https://docs.coingecko.com/reference/onchain-simple-price)
- CoinGecko — [Search Pools & Tokens](https://docs.coingecko.com/reference/search-pools)
- CoinGecko — [Authentication](https://docs.coingecko.com/reference/authentication)
- CoinGecko — [Errors and Rate Limits](https://docs.coingecko.com/docs/errors-and-rate-limits)
- DexScreener — [API Reference](https://docs.dexscreener.com/api/reference)

No live request, credential acquisition, paid request, source change, validator
change, dependency change, workflow change, project-state change, commit, or
push is authorized by this plan.