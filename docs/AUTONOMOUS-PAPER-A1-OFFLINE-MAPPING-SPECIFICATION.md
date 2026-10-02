# Autonomous paper — A1 offline CPMM and candle mapping

Baseline: main `0669f0f1f6d16f205285130a3fc5d995cd4080be`, PR #132 merged; exact post-main CI [535](https://github.com/Tooyamaru/MemeCoinHunterAI/actions/runs/36844192728) PASS (1,863 Python tests and TypeScript).

Authority: controller continuation “Lanjutkan pengerjaan nya”, following the preferred A1 direction. This advances the previously authorized conditional offline specification/mapper/test work with the narrow source facts below. It does not authorize operational requests or spend the proposed provider budget. Status: OFFLINE A1 MAPPING IMPLEMENTED / SYNTHETIC REPLAY VERIFIED; BOUNDED INJECTED COLLECTION/VERIFICATION CONTRACTS IMPLEMENTED OFFLINE; OPERATIONAL BINDING AND VERIFICATION NOT EXECUTED. Runtime callers must explicitly accept both the event scope and candle-close model through `A1Policy`; no application constructs that policy or wires this source automatically.

## Selected offline universe and original clocks

Discovery is now the successful **legacy SPL Raydium CPMM swap** universe of one finalized block, replacing the earlier mint-initialization proposal for this A1 path. A newly initialized mint often cannot supply three closed candles; observing an existing swap makes history possible but does not guarantee its availability. Highest liquidity means highest among all matching pools in this declared block event set, never all pools on Solana. No user-selected token, GPA scan, earlier-slot scan, catalog or provider-first-N list supplies discovery.

`core/data/a1_cpmm_sources.py` consumes three exact `RpcEnvelope` values: finalized `getSlot`, exact-slot finalized `getBlock` with full jsonParsed transactions/version 0/rewards false, and `getBlockTime(slot)`. It requires matching non-null block times and exact method/params/JSON-RPC IDs. No transport, key, environment access, current clock, RPC or HTTP execution exists. Receipts are supplied by a trusted server-side/replay caller, not accepted as browser authority.

Inspect top-level and fully recorded inner instructions in successful transactions. Legacy/v0 are supported; missing inner recording, malformed CPMM data, conflicting identities, time/finality or budget failures reject the whole discovery. Only the pinned Anchor `swap_base_input` / `swap_base_output` discriminators, 24 bytes and exact 13-account legacy layout qualify. Failed transactions and other instruction types are outside scope. Token-2022 swaps are explicitly outside this narrow legacy-only universe; extensions are never decoded as legacy. Both swap directions normalize by mint bytes, preserving paired vaults. Config and observation accounts remain bound to the pool snapshot. Original signature/instruction positions/account mapping/data are hashed into each event. Repeated identical events collapse; contradictory pool composition fails closed. Tokens aggregate all qualifying pool references before lexical maximum-five P02 admission. No fabricated global cursor exists (`cursor=None`); source positions remain in event/scope digests.

Source event time is Solana's estimated block-production time, not exact intra-block execution or last account mutation. Individual request/receipt times and body hashes are retained separately; batch completion supplies only the existing receipt linkage. No receipt timestamps replace block or candle time. An empty valid event universe reaches the existing empty-discovery terminal.

## Pinned reserve mapping

Official `raydium-io/raydium-cp-swap` source pin: `59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92`; program `CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C`. Source inspection establishes parser semantics, not attestation of the deployed binary. No on-chain program/deployment query occurred.

For each admitted candidate, gather the complete event-scoped set of pool/mint/vault addresses. At most 20 pools require at most 81 unique account keys. One exact finalized base64 `getMultipleAccounts` request with `minContextSlot=discovery.slot`, followed by `getBlockTime(returned context.slot)`, binds all state and quantities to a common snapshot. `minContextSlot` is a lower bound, not a historical snapshot selector. Require context slot at least discovery slot, monotone source time, complete non-null account set and source time at or before the snapshot receipt.

| Layout | Checked semantics |
| --- | --- |
| PoolState, 637 bytes, discriminator `f7ede3f5d7c3de46` | Exact CPMM account owner; ten pinned public keys; ordered mints; swap config/observation/mint/vault linkage; two legacy token programs; authority bump 253; bounded status/creator flags; LP decimals 9; zero reserved padding. Nonzero future padding fails closed. |
| Legacy SPL Mint, 82 bytes | Exact token-program owner, initialized flag, decimals 0..18 matching pool fields. |
| Legacy SPL TokenAccount, 165 bytes | Exact token-program owner, initialized state, exact reserve mint and CPMM authority `GpMZbSM2GgvTKHJirzeGfMFoaZ8UR2X7F4v8vHTvxFbL`. |
| Net reserve arithmetic | Raw vault amount minus protocol, fund **and creator** fee counters, checked u64 values; no fee underflow, disabled creator fee with nonzero counter, or zero net reserve. |

The authority constant was independently derived offline from the public PDA seed `vault_and_lp_mint_auth_seed`, public program ID and bump 253. It contains no credential or wallet operation. Account validity checks establish this narrow reserve projection; they are not a replacement for independent P03 safety, executable-program verification or economic/tradability authority.

## Separate two-sided USD valuation

`map_valuation` requires a genuine `OhlcvResponse` per exact reserve mint and pool. Both use the existing immutable `OhlcvRequest` contract: Solana, `currency=usd`, exact token address, `aggregate=1`, `limit=3`, `include_empty_intervals=false`, explicit reference cutoff. The existing pure `_parse` is reused to validate returned base/quote identity and three contiguous closed minute candles. Existing P04-LME-01 admission/diagnostic code is unchanged; this new pre-ranking owner does not fabricate an admitted P02 market predecessor or call LME-03/RTI-11. Its parser coupling is covered by fixtures and full CI.

Use only the latest fully closed minute `[cutoff-60, cutoff)`, requiring both assets to have that same interval. Older/missing latest intervals, gaps, wrong identity, transport failure, receipt after T and excessive age/skew stop valuation. The three candles validate supplied history; freshness for this valuation applies to the selected latest interval, not a claim that all historical candles are younger than 180 seconds. Confidence is `NOT_PROVIDED`; candle close is a model value, not an exactly timed trade or oracle price.

`A1Policy` has no implicit defaults. Both model opt-ins must be exactly true; caller selects positive source freshness at most 180 seconds and conservative skew 0..120 seconds. Age of discovery/reserves uses original block time; USD age uses interval start; interval end must precede its actual receipt. Maximum absolute distance from reserve time to **both endpoints** must be within skew. All receipts precede the same explicit aware reference T. Completed precollected facts are required; starting network collection after a fixed T cannot satisfy these contracts. Completed collection/reference lifecycle is now specified and implemented in `AUTONOMOUS-PAPER-A1-TRANSPORT-COLLECTION-SPECIFICATION.md`.

`L = net_0 / 10**decimals_0 * USD_0 + net_1 / 10**decimals_1 * USD_1`. Parse decimal prices through the existing finite 128-digit/exponent bounds, convert to exact rational values, add without intermediate rounding, floor once to six USD fractional digits and construct Decimal from canonical text. No stable `$1`, doubled quote reserve, reserve-ratio inferred base price, interpolation or forward fill. Selection retains descending exact USD then lexical pool address. A regression test proved unary Decimal minus could round distinct prices under low ambient precision; `copy_negate()` now preserves exact selection without changing the policy.

## Lineage, injected interfaces and limits

Frozen `A1DiscoveryFacts`, `ReserveFact` and `A1ValuationFact` bind source/version/pin, scope/event identities, source clocks, snapshot/body digests, exact net reserves/decimals, both price mint/pool/composition/parameters/raw timestamps/intervals/prices/receipts/body digests/confidence, policy, T and final microusd quantity. `A1ValuationFact.lineage_json` retains the canonical immutable calculation packet; its SHA-256 is the canonical observation reference. Referenced reserve raw bodies retain original amounts and fee counters. The source adapter retains successful reserve/USD envelopes and valuation packets for audit resolution, plus discovery envelopes/facts. No credential headers or error bodies are kept in output lineage.

`OfflineA1DiscoverySource` implements the existing one-shot discovery interface and stores mapped facts. `OfflineA1PoolSource` requires injected trusted reserve and USD envelope suppliers with no default transport. It verifies the same T, lexical-five membership, exact candidate ID and source event ID; actual P02 predecessor admission remains owned by `BoundedDiscoveryOwner`, not by this check alone. Each candidate may invoke the pool source once, including failures. It calls reserve supplier once and USD supplier once per unique scoped pool; each supplies the exact two envelopes. It validates all pools before publishing a tuple/audit set; errors yield a bounded reason without partial canonical results or retry. Fact suppliers are trusted seams, not enforcement of physical HTTP attempts. The new injected transport enforces pre-call accounting, streaming bounds and zero-retry/no-redirect contracts; operational adapter qualification remains required.

| Dimension | Offline hard acceptance cap / future disclosed budget |
| --- | --- |
| Discovery envelopes / slots / bytes | 3 / 1 / 1 MiB + 16 KiB |
| Transactions / instructions / unique swap events / tokens | 2,000 / 8,192 / 32 / 64; excess rejects before lexical truncation |
| Candidates / pools per candidate / unique accounts per snapshot | 5 / 20 / 81 |
| Reserve envelopes per candidate / bytes | 2 / 1 MiB + 8 KiB; per-call 10 s, aggregate 20 s |
| Discovery deadline | Per-call 10 s; aggregate 30 s |
| Valuation envelopes | Two per pool; at most 40 per candidate; old loose 200, tight non-dedup 128, exact collection dedup 64, each at most 1 MiB and 30 s |
| Discovery plus reserve RPC envelope total | At most 13 (3 + 5*2); excludes independent existing P03 safety and selected-pool diagnostics |
| RTI-11 diagnostics | Existing separate maximum five; not counted as valuation requests |
| Retry / pagination / scan / background work | Zero |

These are offline fact/read acceptance caps and a disclosed future transport budget, **not approved operational spending or measured provider availability**. Exceeding scope/budget or any pool/reserve/USD failure rejects the candidate source set rather than retaining first N or silently selecting another metric. Existing cycle exception/terminal behavior remains authoritative. No scheduler/application/transport is wired; no operational cycle or smoke ran.

## Verification and next gate

25 synthetic offline unittest cases prohibit socket connections and cover real P02 admission, original clocks, explicit model acceptance, finalized request/ID/body limits, missing/conflicting time, inner and reversed swaps, unsupported/failed scope, duplicate/conflicting events, validation before lexical-five truncation, independently packed Rust-field binary fixtures, owner/layout/config/vault/fee/decimals checks, atomic snapshot/context, exact two-sided USD/rounding, history/identity/age/skew rejection, replay/lineage, wrong candidate/reference, one-shot supplier failures and exact selection under low Decimal precision. Local `python -m unittest tests.test_a1_cpmm_sources` passes; exact PR-head and post-main Python 3.13/TypeScript evidence is recorded in the milestone PR.

Next gate: operational adapter qualification, precollected P03/RTI-11 replay, durable collection audit linkage and selected-account quota/latency/runtime evidence under `AUTONOMOUS-PAPER-A1-PROVIDER-EXECUTION-PREPARATION.md`. Bounded injected transport, immutable completed T, exact collection-local dedup/budget and mandatory cluster/program LEVEL 1 are implemented offline; see `AUTONOMOUS-PAPER-A1-TRANSPORT-COLLECTION-SPECIFICATION.md`. Provider access/secrets, real endpoint evidence and smoke/cycle remain unexecuted and separately governed. LEVEL 2 binary/source equivalence is NOT VERIFIED. P03/P04 overall, historical estimates and G2/G3/G4/P09 unchanged; MASTER_BLUEPRINT untouched.

## Primary source evidence

- Official pinned [PoolState](https://github.com/raydium-io/raydium-cp-swap/blob/59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92/programs/cp-swap/src/states/pool.rs), [swap account/data mapping](https://github.com/raydium-io/raydium-cp-swap/blob/59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92/programs/cp-swap/src/instructions/swap_base_input.rs), [program ID](https://github.com/raydium-io/raydium-cp-swap/blob/59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92/programs/cp-swap/src/lib.rs), and initialization authority seed read offline. No deployment verification implied.
- Solana [getBlock](https://solana.com/docs/rpc/http/getblock), [getMultipleAccounts](https://solana.com/docs/rpc/http/getmultipleaccounts), [getBlockTime](https://solana.com/docs/rpc/http/getblocktime), [PDA derivation](https://solana.com/docs/core/pda). Numeric caps and supported subset are repository policy, not upstream completeness promises.
- Existing CoinGecko Demo parser and official [pool OHLCV contract](https://coingecko-api-v3.readme.io/v3.0.1/reference/pool-ohlcv-contract-address). No Pro endpoint/key switch.
