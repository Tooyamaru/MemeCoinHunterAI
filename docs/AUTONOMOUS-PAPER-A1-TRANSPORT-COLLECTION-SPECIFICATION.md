# A1 bounded transport and completed collection contract

Status: implemented and tested offline. No provider request or secret has been used. This specification composes the existing A1 mapper; its source clocks, reserve arithmetic, model opt-ins and canonical owners are unchanged.

## Injected transport

`A1BoundedTransport` requires an opener, aware monotone clock and collection ledger. It contains no network implementation/default opener. Immutable requests require HTTPS, no URL userinfo, explicit positive timeout and response cap, zero retry and redirects disabled. Fixed safe headers contain no credentials. The opener receives the exact timeout and immutable no-redirect contract; operational behavior must independently be qualified before provider authorization. A malicious injected callable is outside the contract.

A1-HTTP-01 adds a separately constructed `A1HttpAdapter`, tested offline with
fake connections and stdlib HTTP framing, without changing this owner or wiring
a default. Its fixed same-origin private RPC route and Demo header remain
outside canonical requests/audit. The public endpoint is a sanitized logical
route, not the complete authenticated physical request. See
`AUTONOMOUS-PAPER-A1-HTTP-ADAPTER-SPECIFICATION.md` for exact read-only routing,
deadline/byte/cleanup contracts and limits. Offline adapter conformance is not
real endpoint, quota/latency or runtime qualification.

Only the bounded Solana methods are admitted; collection uses `getGenesisHash`, `getSlot`, `getBlock`, `getBlockTime`, `getMultipleAccounts`. IDs are explicit and unique within a collection. Existing strict `RpcEnvelope.read` rejects malformed/duplicate-key JSON, wrong ID and RPC errors. HTTP status other than 200 and changed final URL fail closed. Streaming reads enforce the sentinel byte cap and clock checks around opener/read; failed attempts remain charged and close the ledger. No fallback, switching, pagination, background I/O or retry exists.

## Collection lifecycle

`A1OperationalCollectionService.collect_once` is terminal and injected only:

1. Start immutable collection identity/environment/intended mainnet identity and a finite ledger.
2. Verify genesis, then the exact CPMM executable/programdata linkage before admitting discovery facts.
3. Collect one finalized block and original block time, then complete bounded reserve snapshots for lexical at most five event-scoped candidates.
4. Collect exact two-sided USD responses through the collection-local registry. Parse identity/candles and check original source clocks/skew before completion.
5. Once every receipt is complete, freeze `completed_at = reference_time = T`. Validate all facts again against this final T; publish no packet if final freshness fails.
6. Produce frozen context/packet containing wire/body digests, exact immutable wire requests rechecked during replay, request identities, all receipt clocks, reuse lineage, policy/budget and verification evidence. Canonical deterministic SHA-256 binds this material.
7. Packet replay creates the existing offline discovery/pool suppliers without any transport reference. Real P02 admission remains with bounded owners. No source network call occurs after T.

OHLCV wire `before_timestamp` is committed to the UTC minute at collection start. The final T must be in the same minute; crossing the minute STOPs without recollection. This conservative restriction preserves the existing OHLCV wire/mapper contract. The maximum aggregate deadline is 180 seconds, selected explicitly; same-minute and remaining-per-request deadlines can terminate earlier. No availability, worst-case latency or full-cardinality success promise is made. Mapper wall clock is never consulted. Block/reserve/candle source timestamps are never replaced by receipts.

## Exact deduplication

`A1ValuationRequestKey` includes collection ID, planned cutoff, endpoint/version, network, pool, exact token mint, base/quote composition, every existing ordered query parameter (USD, aggregate 1, limit 3, include-empty false, before timestamp), timeout and byte cap. The registry returns the identical immutable HTTP receipt only for an exact key within that collection. Every logical use records original request/body digest and start/receipt times. No module/global/stale cache, cross-cycle or cross-T reuse exists. Sealing closes the registry, including failed rollover. Final `OhlcvResponse` is constructed only after T freezes.

## Exact request and byte disclosure

The old 200-envelope disclosure was a loose bound: five candidates × twenty pools × two mint prices. The tighter non-dedup worst case is 128: at most 32 distinct swap pools, each involving at most two selected candidates, with two prices per candidate/pool incidence. A deterministic 32-pool ring fixture achieves 64 incidences while each of five candidates has at most twenty pools. Exact collection-local dedup reduces this attainable valuation bound to **64** (two mints per pool).

| Scope | Solana RPC | CoinGecko HTTP | Physical HTTP total |
| --- | ---: | ---: | ---: |
| Cluster/program verification | 3 | 0 | 3 |
| Discovery | 3 | 0 | 3 |
| Five reserve snapshots plus block times | 10 | 0 | 10 |
| Exact two-sided valuation, deduplicated | 0 | 64 | 64 |
| A1 collection subtotal | 16 | 64 | 80 |
| Selected P03 safety reservation (6 per candidate) | 30 | 0 | 30 |
| Separately owned RTI-11 diagnostics | 0 | 5 | 5 |
| Whole-cycle disclosure | **46** | **69** | **115** |

`A1OperationalBudget` permits lower caps only: 46 Solana/115 total calls, per-host 46/69, 64 valuations, five diagnostics, thirty safety calls, five candidates, twenty pools/candidate, zero retries/scheduler. Reservation consumes call/host/kind and full response-byte cap **before** invoking transport. Exact timeout must fit remaining aggregate time. A refusal causes no next invocation.

Whole-cycle maximum reserved body bytes is **86,597,632**: verification 32 KiB; discovery 1 MiB + 16 KiB; reserve collection 5 MiB + 40 KiB; valuations 64 MiB; diagnostics 5 MiB; selected safety 30 × 256 KiB. RPC collection timeout ceiling is 10 seconds, other scopes at most 30 seconds, aggregate at most 180 seconds. The safety 256 KiB cap is a required future binding selection, not a claim that the existing OAF owner's broader configuration has been changed. A1 collection reserves at most 73,490,432 bytes. Transport's exact chosen cap and timeout are retained per attempt.

RTI-11 diagnostics are disclosed separately; their wire identity/timeout and predecessor-specific interpretation are not automatically deduplicated. Existing P03/RTI-11 operational transports are **not** silently wrapped or allowed after T. Full operational composition still requires precollected safety/diagnostic facts, use of the same aggregate ledger before sealing and pure replay through their existing owners. Current integration tests use synthetic P03 and exact raw candle replay. They prove canonical offline paper persistence/readback and Risk veto, not provider readiness.

Current public CoinGecko Demo pricing reports 100 calls/minute and 10,000/month; the May 19, 2026 status notice records its increase from 30. A nominal 69 CoinGecko calls is below that public rate, but actual selected-account quota, shared usage, credits and latency remain unverified. No endpoint/key/plan switch or rate-limit retry is allowed. See [pricing](https://www.coingecko.com/en/api/pricing) and [notice](https://status.coingecko.com/info_notices/373520). Future execution must demonstrate fit within actual quotas and the same-minute/source-age budget.

## Verification levels

Cluster identity uses exact `getGenesisHash` result `5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d`, independent of endpoint URL. Missing/malformed/mismatched identity stops before discovery. This verifies the supplied RPC identity claim, not an independent Byzantine-consensus proof.

Raydium **LEVEL 1** checks exact `CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C`, existing executable program, owner `BPFLoaderUpgradeab1e11111111111111111111111`, loader-v3 Program tag/linkage, then one atomic Program/ProgramData snapshot rechecking linkage, non-executable programdata, owner, deployment slot and optional upgrade-authority metadata. Two small data-sliced snapshots are bounded; unsupported loader/layout fails closed. Upgradeability metadata is evidence, not immutable deployment assurance.

**LEVEL 2 is NOT VERIFIED**: source pin establishes decoder semantics only. No ELF download/hash or reproducible source-commit/binary equivalence attestation exists. The future paper gate may accept LEVEL 1 only under explicit controller approval; it must retain this limitation.

Primary evidence: [Anza mainnet genesis](https://docs.anza.xyz/clusters/available), [Solana genesis RPC](https://solana.com/docs/rpc/http/getgenesishash), [program deployment](https://solana.com/docs/core/programs/program-deployment), [loader-v3 state layout](https://docs.rs/solana-loader-v3-interface/latest/solana_loader_v3_interface/state/enum.UpgradeableLoaderState.html). No operational query was made.
