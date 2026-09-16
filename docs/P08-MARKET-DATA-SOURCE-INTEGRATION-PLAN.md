# P08 — Market-Data Source Integration Plan

**Status:** SOURCE DECISION BLOCKED / DOCUMENTATION-ONLY
**Contract:** `p08-read-only-market-data-observation-v1`
**Scope:** Official CoinGecko and DexScreener documentation only
**Implementation authorization:** None

## 1. Decision

Neither source currently satisfies the complete P08 read-only market-data
observation contract. No provider is selected for implementation.

CoinGecko is the closest conditional candidate for a minimal, address-scoped
lookup because its official on-chain token endpoints provide price, volume,
reserve/liquidity-like data, and a source timestamp field. It still cannot be
accepted under the current contract because the documented response does not
provide source-supplied asset age, an observation timestamp for the complete
market snapshot, or an exact timestamp-bounded measurement window for its
rolling volume field. DexScreener has the same asset-age problem and additionally
does not document a market-observation timestamp.

The validator must not be weakened, and fetch time must not be substituted for
`observed_at`. The smallest contract-preserving resolution is to approve a
source response or source composition that explicitly supplies:

1. one observation timestamp applying to the returned market fields;
2. a source-supplied asset-origin/asset-age value with unit and reference
   semantics; and
3. the exact measurement window required for rolling volume.

Until those facts are documented by the selected source and a source-to-adapter
contract is approved, no source adapter, dependency, network call, or fixture
implementation may be added.

## 2. Existing contract that must remain unchanged

The future source-specific layer must translate into the existing
`ReadOnlyMarketDataObservation` contract. It must not modify the provider-neutral
validator or its authorized files.

The integration must preserve:

- exact P02 predecessor `chain_id`, `token_identity`, market-subject identity,
  source identity, predecessor digest, and provenance;
- source-supplied `observed_at`; transport receipt or processing time may only
  be represented as explicit availability context when supplied by the caller;
- explicit `PRESENT`, `MISSING`, `UNAVAILABLE`, and `INVALID` metric envelopes;
- source units, semantic versions, reference semantics, and measurement windows;
- raw-payload and observation SHA-256 digests;
- deterministic canonical serialization and immutable values;
- bounded requests and bounded response processing; and
- fail-closed behavior for missing, contradictory, stale, future, unsupported, or
  semantically insufficient data.

No source field may be converted into `asset_age`, `observed_at`, liquidity,
zero, a healthy value, or a usable measurement merely because it is nearby in
meaning. `asset_age` is distinct from P08 `data_age`.

## 3. Official-source comparison

| Contract need | CoinGecko official documentation | DexScreener official documentation | Result |
|---|---|---|---|
| Token lookup identity | `GET /api/v3/onchain/tokens/multi?tokens=network:address,...` returns network and address. `GET /api/v3/onchain/simple/networks/{network}/token_price/{addresses}` accepts comma-separated contract addresses and documents up to 100 addresses. | `GET /token-pairs/v1/{chainId}/{tokenAddress}` returns pairs for a token; pair identity includes chain and pair address. | Both can locate token-related records, subject to an explicit identity policy. |
| Discovery | `GET /api/v3/onchain/search/pools?query=...` searches pool address, token name, symbol, or contract address and returns up to 20 pools per page. | `GET /latest/dex/search?q=...` provides pair search; token-pair lookup provides address-scoped discovery. | Both expose discovery-like lookup, but neither establishes P08 acceptance by itself. |
| Price | `price_usd` or `token_prices` is source-supplied and can map to `price` with quote asset `USD`. | `priceUsd` is source-supplied and can map to `price` with quote asset `USD`. | Potentially compatible, subject to source contract and timestamp. |
| Liquidity | `total_reserve_in_usd` is documented as total reserve, not as a complete observation of the P08 `liquidity` field. Mapping it to liquidity requires an approved semantic alias and valuation context. | `liquidity.usd` is explicitly returned, but is pair-specific and requires deterministic pair selection. | Neither is contract-ready without an explicit semantic and subject-selection policy. |
| Volume | `volume_usd.h24` or `h24_volume_usd` is source-supplied with a 24-hour label. The documentation does not give exact UTC start/end instants for the rolling window. | `volume.h24` is source-supplied with a 24-hour label. The documentation does not give exact UTC start/end instants. | Neither can populate the required exact `TimeWindow` without deriving or inventing boundaries. |
| Asset age | The documented token and simple-price responses do not supply token age or a token-origin timestamp. `last_trade_timestamp` is a last-trade field, not asset age. | `pairCreatedAt`/`pool_created_at` identifies pair or pool creation, not token age; turning it into age would be a derived value and may not identify the token’s origin. | Blocking for both. |
| Source observation time | `last_trade_timestamp` is documented as the last trade timestamp. It is not documented as the observation instant for price, reserve, and volume in the same response. | No market-field observation/update timestamp is documented. `pairCreatedAt` is creation time, not observation time. | Blocking for both. |
| Optional transactions | The reviewed CoinGecko token-price responses do not provide the required P08 transaction-count envelope. | Pair responses expose transaction counts by documented windows, but exact window-boundary timestamps are still not supplied. | Optional only; never substitute for required volume or age. |
| Holders | Not supplied by the reviewed endpoints. | Not supplied by the reviewed endpoints. | Must be explicit `MISSING` or `UNAVAILABLE`, never zero. |
| Raw payload/provenance | The JSON response can be retained by a future source-specific layer for canonical raw-payload hashing and bounded metadata. | The JSON response can likewise be retained and hashed. | Transport/parser responsibility, not validator responsibility. |
| Freshness and bounded access | On-chain simple price documents up to 100 addresses per request, real-time/cacheless paid behavior, and 60-second demo/keyless cache behavior. CoinGecko rate limits are plan-dependent; demo documents 100 calls/minute. | Official API reference documents 300 requests/minute for search, pair, and token-pairs endpoints. | Both permit bounded lookup, but rate limits do not solve missing contract semantics. |

## 4. Conditional closest candidate: CoinGecko

If CoinGecko later documents the missing source facts, the smallest integration
should be an address-scoped lookup, not an unbounded universe scan.

### 4.1 Conditional request shape

Primary candidate:

```text
GET https://pro-api.coingecko.com/api/v3/onchain/tokens/multi
    ?tokens=<network>:<address>,<network>:<address>
```

The official example uses the `x-cg-pro-api-key` header and the Pro API host.
The integration must receive credentials only through the workspace secret
mechanism; this plan does not acquire, register, or display credentials.

For a minimal price/reserve lookup, the documented alternative is:

```text
GET https://pro-api.coingecko.com/api/v3/onchain/simple/networks/{network}/token_price/{addresses}
```

The documented address bound is 100 per request. The future transport must also
enforce a configured maximum URL length, response-byte limit, timeout, and
address count before sending a request. It must not silently split a request
unless the caller explicitly supplies deterministic batch boundaries.

### 4.2 Conditional identity and field translation

Only a P02-linked identity may be accepted for downstream use. A future
translation would:

- copy P02 `chain_id` and `token_identity` exactly;
- use CoinGecko’s network/address only to verify the supplied opaque identity,
  never to replace it with a name, symbol, or CoinGecko coin ID;
- use a token or explicitly selected top-pool identifier as
  `market_subject_id` only under an approved deterministic subject policy;
- preserve `source_event_id` as explicit `null` unless CoinGecko documents a
  stable event identity;
- map `price_usd`/`token_prices` to `price` with `quote_asset: "USD"` only
  after the source timestamp and semantic contract are resolved;
- map `volume_usd.h24`/`h24_volume_usd` only if the source supplies the exact
  measurement window required by P08;
- keep `total_reserve_in_usd` as unavailable until its equivalence to P08
  liquidity is explicitly approved; and
- emit `asset_age`, holders, and transactions as explicit unavailable/missing
  envelopes when the source does not supply them.

The last three rules are deliberate fail-closed behavior. They do not permit a
consumer profile that requires those fields to accept the observation.

## 5. DexScreener disposition

DexScreener is not selected as a fallback. Its documented pair data is useful
for pair lookup and includes price, liquidity, volume, transactions, and
`pairCreatedAt`. However:

1. `pairCreatedAt` is pair creation time, not token age and not market
   observation time;
2. no source observation/update timestamp for the returned market fields is
   documented;
3. a token can have multiple pairs, so choosing one requires an approved
   deterministic market-subject policy; and
4. documented rolling windows such as `h24` do not provide exact UTC window
   endpoints for the P08 `TimeWindow`.

Using fetch time, pair creation time, or a chosen pair’s latest-looking field to
repair any of these gaps would violate the current contract.

## 6. Future implementation boundary after blocker resolution

No files in this section are authorized now. If an approved source contract
resolves the blockers, the implementation should be confined to these new
source-specific files:

```text
core/data/coingecko_transport.py
core/data/coingecko_market_data_source.py
tests/test_coingecko_market_data_source.py
tests/fixtures/coingecko_market_data/token_observation.json
```

The responsibilities would remain separate:

1. `coingecko_transport.py`: HTTPS transport, authentication header injection,
   timeout, response-size limit, status/error translation, bounded retries only
   for explicitly retryable failures, and no normalization.
2. `coingecko_market_data_source.py`: deterministic parsing, source-to-P08
   translation, identity/provenance links, explicit missing states, raw-payload
   canonical bytes, and digest construction. It must not modify
   `core/data/read_only_market_data.py`.
3. `tests/test_coingecko_market_data_source.py`: offline contract and transport
   boundary tests.
4. `tests/fixtures/coingecko_market_data/`: bounded, redacted, deterministic
   JSON fixtures only; no live calls or credentials.

No provider-specific code may be placed in the provider-neutral validator,
discovery contracts, market-observation contracts, P05/P06/P07 boundaries, or
any execution, wallet, persistence, or deployment path.

## 7. Required failure and retry behavior

The future source layer must fail closed and preserve bounded provenance for:

- HTTP 400, 401, 403, 408, 429, 500, 503, and undocumented response shapes;
- authentication or plan restriction failures;
- timeout, connection, malformed JSON, oversized body, and unexpected content
  type;
- missing token records, duplicate token records, conflicting pair records, and
  source fields with incompatible types;
- absent source observation timestamp, absent asset age, absent exact volume
  window, or unresolved liquidity semantics; and
- any source value that cannot be represented by the current P08 field contract.

Retries must be bounded, deterministic, and limited to explicitly retryable
transport/server conditions. Do not retry authentication, plan, validation, or
contract-shape failures. A retry must never change the observation timestamp or
make stale data fresh.

## 8. Offline verification and manual inspection

After blocker resolution and separate implementation authorization, verification
must include:

```text
uv run pytest -q tests/test_coingecko_market_data_source.py
uv run python -m compileall -q core/data/coingecko_transport.py core/data/coingecko_market_data_source.py
git diff --check
git diff --no-index --check /dev/null tests/fixtures/coingecko_market_data/<fixture>.json
```

Tests must cover deterministic request construction, batch bounds, timeout and
response-size rejection, each documented status class, redacted provenance,
canonical raw-payload and observation digests, identity preservation,
source-observation-time requirements, exact volume-window requirements,
explicit missing/unavailable values, stale/future observations, duplicate and
contradictory records, and zero network calls.

Manual inspection command:

```text
uv run python - <<'PY'
from pathlib import Path
print(Path("docs/P08-MARKET-DATA-SOURCE-INTEGRATION-PLAN.md").read_text())
PY
```

The inspection must confirm that this plan remains the only file created by the
planning task and that no credentials, account registration, paid request,
wallet, signing, trading, dependency, workflow, or project-state change was
introduced.

## 9. Official documentation reviewed

Only these official documentation pages are used for the provider comparison:

- CoinGecko — [Tokens Data by Token Addresses across Networks](https://docs.coingecko.com/reference/tokens-data-contract-addresses-multi)
- CoinGecko — [Token Price by Token Addresses](https://docs.coingecko.com/reference/onchain-simple-price)
- CoinGecko — [Search Pools & Tokens](https://docs.coingecko.com/reference/search-pools)
- CoinGecko — [Coin Data by Token Address](https://docs.coingecko.com/reference/coins-contract-address)
- CoinGecko — [Authentication](https://docs.coingecko.com/reference/authentication)
- CoinGecko — [Errors and Rate Limits](https://docs.coingecko.com/docs/errors-and-rate-limits)
- DexScreener — [API Reference](https://docs.dexscreener.com/api/reference)

This document does not treat third-party descriptions, undocumented response
fields, provider SDK behavior, or observed live responses as contract evidence.