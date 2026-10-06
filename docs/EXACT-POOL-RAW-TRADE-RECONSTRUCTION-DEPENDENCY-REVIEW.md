# Exact-pool raw-trade reconstruction dependency review

## 1. Status, baseline and authority

- Record: **`exact-pool-raw-trade-reconstruction-review-v1`**; this is an evidence/design record, not an implemented source or an accepted diagnostic contract.
- Review date: **2026-10-06 WIB**.
- Exact offline baseline: main **`1e9c9b7245268ca43181cb241a37a0a7962cc1a2`**, tree **`8fe8f458a4bf62443c974d785540d458826d494f`**.
- PR #147 MERGED / CLOSED, unchanged head `8b02a7bc4bee14bd99ac992d365f95b74f349fee`; exact-head CI #576 / `37414523852` SUCCESS; post-main CI #577 / `37421023822` SUCCESS. Python 3.13, whitespace and TypeScript PASS. No competing open PR at startup.
- Controller authority: **AUTONOMOUS CONTINUOUS WORK / TEMPORARY NO-GITHUB / OFFLINE-FIRST**, supplied 2026-10-06. Public source/owner research, justified offline contracts/code/tests and one publishable batch are authorized. This does not supply missing source facts or authorize provider access, purchases, vendor contact, paper actions or live authority.
- Remote reads worked at startup. Existing older, dirty checkouts were preserved. A separate clean shallow checkout was reconstructed from exact GitHub blob/tree/signed-commit bytes and verified against the main SHA/tree above. The completed offline checkpoint was local head `1770440ff6c1ca2dcb027363761636a12772ec11`. The continuation re-read remote rules/state and reconfirmed compatible main/open PRs before resuming publication. PR/required exact-head CI/merge/post-main evidence are **PENDING AT THIS SOURCE CHECKPOINT**; no quota recovery or unverified result is claimed.

**Decision: choose separate exact-trade/candle and USD-valuation responsibilities as the conditional design (option D); qualification remains HARD_EXTERNAL_BLOCKER.** Raw reconstruction is technically defensible once complete original swap facts and cutoff evidence exist. Public event schemas resolve useful arithmetic/identity questions, but no inspected source profile proves the complete immutable before-C input set within the existing bounded operation. No production parser, candle builder, RTI-11 companion or A1 integration is implemented in this batch.

Risk Governor remains **INDEPENDENT / MANDATORY / HIGHER AUTHORITY THAN DECISION ENGINE / AI**. G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**; G3/G4/P09 remain **NOT AUTHORIZED**.

## 2. What PRICE_DIRECTION_1M actually requires

Repository truth distinguishes arithmetic from an admitted measurement's meaning:

| Owner | Verified behavior | Consequence |
| --- | --- | --- |
| [price_direction_policy.py](../core/signals/price_direction_policy.py) | `price-direction-v1` re-admits original CoinGecko request/response bytes and compares the last two accepted closes with exact `Decimal` comparison. | The comparison itself is unit-independent; it does not intrinsically require a USD conversion. |
| [coingecko_onchain_ohlcv.py](../core/data/coingecko_onchain_ohlcv.py) | The fixed request selects `currency=usd`; admitted PRICE observations carry `unit=USD` and `quote_asset=USD`. | The current V1 closes have USD semantics. Changing only their numeric values to a native ratio would mislabel evidence. |
| [market_to_opportunity_composition.py](../backend/application/market_to_opportunity_composition.py) | RTI-11 V1 checks CoinGecko request/result types, provider/adapter/endpoint, exact target, three observations and policy/source lineage. | A native observation or another provider must not masquerade as V1 evidence or inherit its digest. |
| [market_intelligence.py](../core/data/market_intelligence.py) | P02 represents bounded provider-neutral values; category contracts define value shape, not measurement semantics. | P02 does not independently impose USD. A separately versioned rational/quote measurement could reuse these owners without globally changing them. Representation permission is not signal or source authority. |

**Native direction is not generally equivalent to USD direction.** Let `r` be quote units per base token and `q` the contemporaneous USD price of one quote token. A base-token USD trade price is `r * q` only when both original facts and their time/source binding are valid.

| Two successive closes | Native outcome | USD outcome |
| --- | --- | --- |
| `r: 0.001 -> 0.001`, `q: 100 -> 110` | FLAT | RISING (`0.100 -> 0.110`) |
| `r: 0.001 -> 0.0011`, `q: 100 -> 80` | RISING | FALLING (`0.100 -> 0.088`) |
| `r: 0.001 -> 0.0009`, `q: 100 -> 120` | FALLING | RISING (`0.100 -> 0.108`) |

A constant positive conversion preserves direction, but a stablecoin symbol/peg is not factual proof that the conversion remained constant. Do not assume USDC/USDT/USD1 or native/wrapped SOL aliases have identical values or identities.

Therefore a future native-ratio source need not acquire USD merely to construct native candles. It must carry an explicit original quote mint, rational units, fee basis and versioned direction policy. Its semantics and downstream source/basis admission need explicit compatibility review. It cannot silently replace the current USD `PRICE_DIRECTION_1M` or label a changed policy `price-direction-v1`. The existing CoinGecko V1 and proposed USD Pairs profile remain unchanged.

## 3. What original CPMM swaps can reconstruct

Pinned official source: Raydium [commit `59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92`](https://github.com/raydium-io/raydium-cp-swap/tree/59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92). The executable identity remains `CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C`. A source-code pin is not deployed binary/LEVEL 2 verification.

| Original artifact | Git blob | Bounded documentary fact |
| --- | --- | --- |
| [SwapEvent](https://github.com/raydium-io/raydium-cp-swap/blob/59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92/programs/cp-swap/src/states/events.rs) | `ad9ae98bf2444c66e962181570315bc7b4d60567` | Carries pool, original input/output mints, integer amounts, transfer/trade/creator fees and vault facts. It does not itself carry a transaction signature, slot, transaction timestamp, ingestion clock or completeness proof. |
| [swap_base_input](https://github.com/raydium-io/raydium-cp-swap/blob/59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92/programs/cp-swap/src/instructions/swap_base_input.rs) | `514a2dec36f7bf337302c1b25a2a883f2e230945` | Emits `base_input=true` for the exact-input instruction; input amount is after the input transfer fee, and the output transfer fee is separately recorded. |
| [swap_base_output](https://github.com/raydium-io/raydium-cp-swap/blob/59fb845a9e5bb569c8b2f3415f13b0c0ebcc6b92/programs/cp-swap/src/instructions/swap_base_output.rs) | `dd07d44bbdcefc413316eef9d5f58731a0bf2dce` | Emits `base_input=false` for the exact-output instruction, retaining original input/output mints and fee facts. |

`base_input` identifies instruction mode; **it does not identify whether the original requested base mint is the input mint**. Both swap directions can use exact-input mode. Resolve direction from original input/output mints and the explicit requested base/quote tuple. Preserve all raw fees and the selected gross/net measurement basis; do not mix wallet-paid, wallet-received and pool-side amounts or silently subtract a fee twice.

Conditional deterministic construction, after source admission:

1. Bind exact genesis/network, program, pool, base/quote/token mints, original mint decimals, source/schema/event profile and original request/response digests. Require a successful transaction, correct invoked program/event origin and an unambiguous supported event layout. Logs from another program are not proof merely because their bytes decode.
2. Retain signature, slot, block/parent identity, transaction index, outer/inner instruction location and event ordinal. One transaction can contain multiple legitimate swaps. Reject a repeated raw transaction record or repeated full trade identity; never deduplicate provider rows silently.
3. Derive the agreed base and quote raw amounts in the requested orientation. For integer amounts `B,Q` and original decimals `db,dq`, native price is the exact positive rational `(Q * 10^db) / (B * 10^dq)`. Preserve reduced numerator/denominator; do not round through ambient `Decimal` or binary float to fit a legacy scalar.
4. Require a supported original event-time basis and the exact half-open window `[C-180s,C)`. Boundary trades at `C-180s` belong; trades at `C` do not. Minute starts are exactly `C-180`, `C-120`, `C-60`, with exclusive ends 60 seconds later. All three minutes need actual eligible trades; an empty/missing minute STOPs without carry-forward or a synthetic candle.
5. Use the pinned ledger transaction/instruction/event ordering as the deterministic intra-minute tie-breaker. Define open/close from actual eligible trade order and high/low by exact rational comparison. Sum the same explicitly defined base/quote quantity basis for volume. Retain event IDs/counts and source clocks; no token/pool replacement or unsupported ordering repair.
6. Admit all three candles atomically only after original identity, finality, before-C input availability, retrieval completeness and freshness checks. Pure replay uses only the retained packet; it performs no I/O, clock/environment read, retry or request expansion.

These are necessary design constraints, not an implemented parser or proof that a provider supplies such a packet. The eventual exact source/event/fee profile must be governed before positive fixtures can represent a legitimate production admission.

## 4. Finality, event time and availability are different facts

[Solana getBlockTime](https://solana.com/docs/rpc/http/getblocktime) describes block production time as an estimate from stake-weighted vote timestamps. That clock is useful for an explicit chain-time measurement; it is not an authenticated first-ingestion or first-receipt clock. A wall-clock candle source cannot silently reinterpret it as a different timestamp guarantee.

| Fact | What it establishes | What it does not establish |
| --- | --- | --- |
| `blockTime < C` | A reported event-time predicate. | That the complete input was available before C, exact wall-clock publication, or absence of later indexing. |
| `commitment=finalized` at retrieval | The selected node returns its finalized view at retrieval. | That the transaction/finality/input set was already known before C. |
| `minContextSlot=R` | A lower bound on processing context. | An exact root, an upper bound, a frozen as-of snapshot or knowledge at C. Multiple later roots satisfy the same lower bound. |
| Fixed slot upper bound and block ancestry | A bounded ledger branch/input selection, subject to real root/coverage evidence. | Original knowledge-before-C, complete time-window mapping, or a missing-trade absence proof from filtered rows alone. |
| Signature/block hash/body digest | Transaction/byte identity and retained lineage. | Complete retrieval, source clock accuracy, missing records or independent source attestation. |
| A later `received_at` | When this collector received the body. | Original ingestion/publication time before C. |

The indistinguishability counterexample remains decisive: identical finalized response bytes with an event timestamp before C can come from an input first observed at `C-1s` or at `C+1s`. If the response omits that distinction and its source contract supplies no immutable as-of proof, a parser cannot recover it.

Require a reviewed source-maintained original availability clock/as-of snapshot or a genuinely retained complete before-C capture. Keep event, original availability, provider update/construction, finality observation, collector receipt and reference/cutoff clocks distinct. Unknown values remain unknown and fail admission. Retrospective finality cannot replace this predicate. A future bounded capture would need its own source/topology/clock/coverage/finality and operational budget approval; this batch does not start a stream or enlarge the 10-second/one-operation budget.

## 5. Bounded completeness is an independent gate

Three candle rows, positive volume, a terminal cursor, a block hash or a success HTTP status cannot alone prove that an index supplied every eligible swap. The source profile must define terminal/partial/error behavior and the complete covered range, including all matching transactions/instructions/events and how unavailable/skipped slots and null timestamps are represented.

For a raw route, retain the exact range/query/filter, original terminal/completeness evidence, finality/root/branch and original clock proofs. Unknown indexing lag, partial transactions, missing metadata/loaded addresses/decimals, truncated logs, pagination, unsupported transaction versions, inconsistent counts, malformed frames or an unfinished stream must stop the whole packet. A filtered block's full transaction count is not automatically the number of filtered pool swaps. A response digest cannot repair missing records.

The existing alternative-incidence ceilings remain: **one physical operation/attempt, 32,768 request bytes, 1,048,576 response bytes, 10 seconds**, or a stricter caller/aggregate cap. Count decoded/uncompressed retained content under the body bound; no hidden SDK continuation/reconnect/retry, fallback, redirect, token refresh or second target. Streaming/range APIs must prove a terminal bounded result under these limits before adoption. No throughput/SLA or entitlement is inferred from an example.

## 6. Source assessment

Classifications below concern the required complete cutoff-valid packet, not whether a vendor is generally useful. Public documentation was read; no market-data endpoint, live sample, account or credential was used.

| Source/surface | What public evidence establishes | Remaining qualification gap / classification |
| --- | --- | --- |
| Solana standard RPC; S1-S3 | Finalized `getBlock` can return transactions/metadata for one slot; `getBlocks` lists a bounded slot range. | Enumerating slots plus block bodies is multiple operations, not one timestamp-window trade request. Original availability, time-window completeness and the bounded full packet remain **NOT PROVEN**. |
| Helius `getTransactionsForAddress`; S4 | Address filter, successful status, finalized commitment, slot/block-time bounds, raw full detail and keyset cursor. Current reference allows 1-1000 full transactions; the older introductory blog's 100-full-record figure is not the current profile. | The exact-pool raw carrier is promising. No original before-C knowledge/snapshot clock or reviewed complete-window/partial-index contract is established: **REQUIRES PROVIDER CLARIFICATION**. A cursor is not independent completeness proof. No request is made. |
| Yellowstone / LaserStream; S5-S7 | Update creation timestamp, slot/transaction/block metadata and finalized subscriptions; replay up to about 48 hours. The current guarantee page describes exactly-once ordered confirmed/finalized delivery. | Older replay is documented as finalized-block-only, not original processed/fork/intra-slot history. `created_at` means update creation, not a proven immutable first-availability/as-of field. Replay proceeds toward live data and client recovery can add calls. Bounded terminal cutoff/clock/budget remain **NOT PROVEN**. |
| Triton Fumarole; S8 | Stores up to four days and supports persistent subscriber replay. Subscriber cursors are cluster-local. | Persistent subscriber creation/bookkeeping is a separate external stateful operation; original availability and bounded read-only one-window terminal evidence are **NOT PROVEN**. No subscriber is created. |
| Old Faithful; S9-S10 | Historical ledger/entry archive, integrity tooling, and finite `StreamBlocks`/`StreamTransactions` slot ranges with documented filters. | Strong ledger reference, not a wall-clock before-C trade/quote capture. Timestamp-to-slot coverage, original knowledge clocks, exact profile/terminal/error bounds and account/budget remain **NOT PROVEN**. The epoch-208 integrity report is scoped, not this target/window qualification. |
| Shyft; S11-S12 | CPMM transaction parsing examples preserve instruction/transaction metadata; the inspected transaction API documents a 3-4-day history. | Parsing an example is not archive completeness/as-of or an authenticated event-layout/version guarantee: **NOT PROVEN**. No SDK default reconnection or live stream is used. |
| Bitquery raw cubes; S13-S14 | `DEXTrades` and `DEXTradeByTokens` expose chain-level trades; current retention reference distinguishes ~12-hour realtime DEXTrades, ~7-day realtime DEXTradeByTokens and the latter's archive history. | A pin must distinguish realtime/archive/combined and trade-side/orientation rows. Time filtering does not establish immutable input availability or complete retrieval: **REQUIRES PROVIDER CLARIFICATION**. Existing Pairs qualification decision is unchanged. |
| Vybe historical trades; S15 | Original pool/program/mint/slot/signature and quote-price fields; page/limit maximum 1000. Pool filter overrides base/quote mint filters, requiring row verification. | The price field is quote units, not USD. Original before-C availability, full window completeness and clock/model guarantees are **NOT PROVEN**. |
| Tardis; S16-S17 | Capture-arrival clock is preserved; filtered HTTP slice sizes 1-10 can include three minutes in one request. | Reviewed coverage does not prove Raydium CPMM exact-pool swaps or this quote identity/complete packet: **NOT PROVEN**. The one-minute default is not a universal one-minute limit. |
| DexPaprika pool transactions; S18 | Exact pool route, swap amounts, two USD fields, pagination and transaction timestamp fields. | USD fields and `created_at` do not establish original input/conversion availability/as-of. Bounded completeness is **NOT PROVEN**. No stablecoin peg or token-wide aggregation is substituted. |
| Birdeye | Prior official candle review remains applicable; new raw-pair reference URLs were not retrievable in this session. | A documentation retrieval failure is not a capability rejection. A current raw-pair schema/clock/completeness profile remains **NOT PROVEN**. |
| Previously reviewed CoinGecko/GeckoTerminal, Dune, SQD, Allium/warehouse and Flipside paths | Retain the scoped facts and exclusions in the [landed public review](EXACT-POOL-CANDLE-SOURCE-PUBLIC-CAPABILITY-REVIEW.md). | No previously unproven archive/snapshot/USD claim is promoted to qualification. Native construction does not silently solve their completeness/availability gaps. |

No account entitlement, quota, paid upgrade, provider latency or response-size qualification is claimed. Helius is the smallest documented HTTP raw-carrier candidate worth clarifying; Old Faithful is a useful ledger verification reference. Neither is selected as an approved runtime source.

## 7. A1 valuation remains separate

[a1_cpmm_sources.py](../core/data/a1_cpmm_sources.py) currently requires two separately bound CoinGecko USD receipts, one per original reserve mint, from the same selected pool/latest closed interval, then performs the existing deterministic reserve valuation. A source-neutral PRICE value, native candle, swap USD total, stablecoin label, current token quote or base-only receipt cannot substitute those facts.

A separately versioned valuation design could consume source-backed contemporaneous quote observations and original trade/reserve/mint lineage only after its own approval/evidence. Do not rename such facts CoinGecko receipts or change existing V1 digests/validators.

Per-trade USD construction would require `native_price_i * historical_quote_usd_i` with the correct original source/clock at each eligible trade. USD OHLC extrema are then extrema of those products. Multiplying a native candle's high by one latest quote close is generally wrong: native trades `(1,2)` with respective USD quote observations `(3,1)` produce USD prices `(3,2)`, whose high is 3, while `native_high * last_quote = 2`. A native candle close alone also does not supply both A1 valuation receipts. Missing before-C quote observations remain a valuation blocker, independent of native reconstruction.

## 8. Minimum continuation and conditional implementation plan

Selected design: **separate exact-trade source, deterministic native candle construction, explicit versioned native measurement/direction semantics, and separate USD valuation authority**. Preserve existing P02 owners where their bounded representation supports the reviewed value shape; preserve all CoinGecko/RTI-11 V1/P04/P05/Risk/A1 owners and digests.

Before runtime implementation, obtain an authoritative source/evidence bundle with:

1. Pinned original transaction/event/schema and gross/net fee/price basis, exact pool/program/mint/decimal binding, transaction/instruction ordering and unsupported-version behavior.
2. Immutable original before-C availability/as-of evidence, including what replay creation clocks retain, late indexing/corrections/forks, finality/root timing and the complete time-to-slot coverage rule.
3. One-operation terminal completeness/partial/truncation/null-log behavior plus entitlement/account cost and the existing hard timeout/body limits. No pagination/reconnect is admitted as one logical call.
4. For USD V1 compatibility or A1 valuation, a separately governed contemporaneous historical quote-USD authority and the corresponding input-clock and two-original-mint bindings. Native-only construction must explicitly remain native-only.

Once those source facts exist, the current controller authority already permits the smallest justified offline parser/rational builder/admission/replay and explicitly versioned companion design. This is not another request for engineering permission. Positive local fixtures must model the approved raw packet and original proofs; they cannot manufacture qualification. No layer that can only STOP on an unapproved profile is added merely to defer the external dependency.

An operational capture alternative is a different gate: it needs explicit one-shot capture duration, topology, source clocks/coverage and finality budget, with no scheduler/loop. It is not authorized by this document and must not be squeezed into or silently enlarge the current one-request/10-second boundary.

## 9. Focused validation and future test plan

Local research calculations: **14 checks PASS under Python 3.12.14**, covering native/USD direction counterexamples, conditional constant-conversion equivalence, per-trade USD extrema, integer decimal scaling, nonterminating rational values and comparison, half-open boundaries, count-versus-completeness, minimum-versus-pinned context, indistinguishable finalized availability histories, multiple legitimate swaps per transaction and instruction-mode versus orientation. These are mathematical/design checks, not an implemented-source acceptance test or provider proof.

Focused legacy pytest invocation did not start: Python 3.13 and pytest are unavailable in this current workspace; offline cache resolution also found no pytest. No dependency download, lock change or full local suite was attempted. Baseline CI #577 remains verified PASS; new-head Python 3.13/TypeScript CI is **PENDING AT THIS SOURCE CHECKPOINT**. Production files are unchanged and their baseline blob identities are checked separately.

Focused documentation validation **PASS**: exact baseline SHA/tree and intended branch, exactly four changed documents, UTF-8/newlines/Markdown fences, eight local links/anchors, 18 primary-source groups and the 14-check research inventory. Parent-spec §§4–10 remain byte-identical to baseline; eight rules/owner/landed-review blobs remain unchanged. Explicit identity/cutoff/budget/authority and deferred-publication disclosures are present. Staged `git diff --check` **PASS**. These checks validate this documentation batch, not a raw-source or operational qualification.

Future implementation must test:

- Three actual minute buckets; exact lower/upper boundary swaps; deterministic OHLC/base/quote volume; exact rational serialization/order/replay without I/O.
- Repeated raw transaction; duplicate full trade location; multiple distinct valid swaps in one transaction; missing/empty/noncontiguous minute; no deduplication or filling.
- Wrong pool/program/mints/decimals/orientation/fee basis; unsupported event/transaction layout; spoofed or truncated logs, loaded-address/metadata absence and null/unsupported event clocks.
- Pre/post-cutoff input availability and events; stale/future clocks; root/branch/finality mismatch; missing original creation clocks, replay-only finalized history and later correction/reindexing.
- Partial retrieval, omitted slots/transactions/events, inconsistent counts, cursor/continuation/unfinished stream, pagination, retry, request/body/deadline expansion and unsafe credential retention.
- Native-versus-USD semantics and lineage; unchanged legacy V1 objects/digests/rejections; independent Risk veto and existing STOP boundaries when any future composition integration is authorized.

Documentation scope: this new record, a narrow parent-spec link/clarification, PROJECT_STATE and CHANGELOG in **one offline batch**. No MASTER_BLUEPRINT, executable source/test/dependency/schema/workflow change, provider call, credentials, purchase, vendor message, paper action or live action.

## 10. Authoritative sources

Sources were retrieved as public documentation/static upstream code only on 2026-10-06. Statements above separate documentary facts from design requirements and unproven capabilities.

- **S1:** [Solana getBlock](https://solana.com/docs/rpc/http/getblock) and [JSON structures](https://solana.com/docs/rpc/json-structures).
- **S2:** [Solana getBlocks](https://solana.com/docs/rpc/http/getblocks).
- **S3:** [Solana getBlockTime](https://solana.com/docs/rpc/http/getblocktime).
- **S4:** [Helius getTransactionsForAddress reference](https://www.helius.dev/docs/api-reference/rpc/http/gettransactionsforaddress); [older introductory post](https://www.helius.dev/blog/introducing-gettransactionsforaddress) is historical context only.
- **S5:** [Helius Subscribe schema](https://www.helius.dev/docs/api-reference/laserstream/grpc/subscribe), especially update `created_at` and block/transaction metadata.
- **S6:** [LaserStream historical replay](https://www.helius.dev/docs/laserstream/historical-replay).
- **S7:** [LaserStream delivery guarantees](https://www.helius.dev/docs/laserstream/delivery-guarantees); the overview's navigation also says at-least-once, so pin/clarify the actual service profile rather than infer a cross-version guarantee.
- **S8:** [Triton Fumarole](https://docs.triton.one/project-yellowstone/fumarole) and [persistent subscriber operation/cursor description](https://blog.triton.one/introducing-yellowstone-fumarole/).
- **S9:** [Old Faithful overview](https://docs.triton.one/project-yellowstone/old-faithful-historical-archive) and [finite gRPC method examples](https://docs.old-faithful.net/references/grpc-methods/examples).
- **S10:** [Scoped epoch-208 historical integrity report](https://docs.triton.one/project-yellowstone/old-faithful-historical-archive/public-report-epoch-208).
- **S11:** [Shyft CPMM transaction parsing](https://docs.shyft.to/solana-yellowstone-grpc/examples/raydium-cpmm/solana-raydium-cpmm-transaction-parsing-example).
- **S12:** [Shyft transaction API/history limits](https://docs.shyft.to/solana-apis/transactions/transaction-apis).
- **S13:** [Bitquery Solana DEX trades](https://docs.bitquery.io/docs/blockchain/Solana/solana-dextrades/).
- **S14:** [Bitquery current data coverage/retention](https://docs.bitquery.io/docs/graphql/data-coverage-retention/).
- **S15:** [Vybe historical trades](https://docs.vybenetwork.com/docs/fetch-historical-trades).
- **S16:** [Tardis filtered HTTP slices](https://docs.tardis.dev/api/http-api-reference) and [original capture/ordering clock](https://docs.tardis.dev/faq/data).
- **S17:** [Tardis documented exchange coverage](https://docs.tardis.dev/historical-data-details).
- **S18:** [DexPaprika pool transactions](https://docs.dexpaprika.com/api-reference/pools/get-transactions-of-a-pool-on-a-network-paging-can-be-used-up-to-100-pages).

Pinned Raydium artifacts are listed in §3. Repository owner references in §2/§7 are from the exact offline baseline, not a new architecture or deployment attestation.
