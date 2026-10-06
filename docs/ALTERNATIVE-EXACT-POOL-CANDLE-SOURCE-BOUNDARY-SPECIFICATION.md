# Alternative exact-pool candle source boundary

## 1. Status, decision and authority

- Milestone: **P04-ACS-01**.
- Proposed contract: **`alternative-exact-pool-candle-source-v1`**.
- Status: **SPECIFICATION / PUBLIC CAPABILITY REVIEW COMPLETE / CANDIDATE NOT QUALIFIED / HARD_EXTERNAL_BLOCKER**.
- Original specification baseline: main `62013cba3fd994c0337621c23b4b1f5ee5e2c166`; PR #144 MERGED / CLOSED; main CI #570 / `37254641401` SUCCESS for Python 3.13, whitespace and TypeScript; no competing open PR at startup.
- Original controller authority: 2026-10-05 WORK FAST MODE successor specification and batched `PROJECT_STATE.md` reconciliation in one PR. This authority permits public documentation lookup, not operational provider access.
- Current continuous-work authority: the 2026-10-06 AUTONOMOUS CONTINUOUS WORK / TEMPORARY NO-GITHUB / OFFLINE-FIRST directive authorizes technically justified offline contracts/code/tests and one clean publishable batch from a verified baseline. Publication/new-head CI may be deferred without claiming a remote change. Before eventual publication, reconcile current-main rules/state, exact main and open PRs; exact-head CI PASS and guarded merge/post-main verification remain required. The earlier evidence-only implementation prohibition and STOP-on-CI-start are historical and superseded. No provider-data request, credential/account operation, vendor contact, purchase, operational migration, paper action or live authority is opened. See §3.4, §3.5 and §11.

Boundary decision: **NEW PROVIDER BOUNDARY / SPECIFICATION REQUIRED**. Bitquery Crypto Price API `Trading.Pairs` remains a conditional candle candidate; it is not an implemented or qualified substitute. Current source-selection decision is **HARD_EXTERNAL_BLOCKER / NO IMPLEMENTATION-READY PROFILE**, after the public/source review in §3.4 and raw-trade/price-basis review in §3.5. The latter separates possible native candle construction from USD valuation, without treating native and USD direction as equivalent. Existing RTI-11 acceptance is CoinGecko-specific; changing a URL or transport cannot make alternative evidence admissible. A narrow, explicitly versioned source seam is required before future integration.

The boundary accepts three factual, unique, contiguous, closed one-minute candles for one already-selected exact pool and price orientation. It preserves original source times and honest provider provenance. It does not discover, rank or replace targets, supply safety evidence, select investments, or authorize a paper cycle.

Risk Governor remains **INDEPENDENT / MANDATORY / HIGHER AUTHORITY THAN DECISION ENGINE / AI**. G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**. G3/G4/P09 remain **NOT AUTHORIZED**.

## 2. Why continuation needs a new boundary

The controller reports successful local Windows staging runtime, PostgreSQL/schema and authenticated readiness checks, working Solana access, and CoinGecko HTTP 200/authentication/transport. Work did not repeat those operational checks. The reported provider-backed prepare stopped with `PREPARATION_STOPPED` / `DIAGNOSTIC_NOT_PRODUCED`; no run/persist was executed.

| Reported pool label | Raw candle timestamps | Canonical obstruction |
| --- | --- | --- |
| UWU/SOL | `[1791170580, 1791170580, 1791113520]` | Two unique timestamps; remaining spacing 57,060 seconds |
| BONK/SOL | `[1791195120, 1791195120, 1791194220]` | Two unique timestamps; remaining spacing 900 seconds |

These labels are incident context, not authorized public target identities. The timestamps are controller-reported reproduction facts, not independently captured responses or current wall-clock evidence. They demonstrate why those responses cannot be admitted; they do not establish a global CoinGecko outage or a permanent service guarantee change.

CoinGecko's documented Demo profile supports minute/aggregate=1, an exclusive `before_timestamp`, explicit mint orientation, USD and `include_empty_intervals=false`. With empty intervals excluded, a quiet market can have gaps. Neither that profile nor HTTP 200 proves three contiguous factual minutes. No documented parameter correction establishes that duplicate rows can be repaired safely. Enabling empty intervals would allow fabricated carry-forward candles and is rejected. Deduplication, gap filling, older-window substitution and random-pool trials are not continuations of this contract.

### Bounded repository evidence

| Existing owner/reference | Finding |
| --- | --- |
| `core/data/coingecko_onchain_ohlcv.py`; P04-LME-01 specification | Owns a CoinGecko request, raw-response admission, fixed provider/version provenance and P02 materialization. It correctly rejects duplicate/non-contiguous evidence. Bitquery is already mentioned as a future independent audit/backfill candidate, not a V1 runtime path. |
| `core/data/coingecko_onchain_transport.py`, `coingecko_onchain_diagnostic.py`, `coingecko_onchain_orchestration.py`; P04-LME-02 | Bounded explicit CoinGecko transport and exact-pool controlled diagnostic; no alternate candle source. |
| `core/signals/price_direction_policy.py` | Re-admits raw CoinGecko facts and pins CoinGecko signal provenance; a caller-supplied success label cannot bypass admission. |
| `backend/application/market_to_opportunity_composition.py`; P01-RTI-11 specification | Request construction and `_diagnostic_success` pin CoinGecko request/provider/adapter/endpoint identity and original observation/signal lineage. |
| `core/data/a1_rti11_collection.py`; A1 RTI-11 precollection specification | Pre-T facts, request/reuse keys and pure replay are CoinGecko-bound. Source substitution would require a versioned collection/replay integration, not mutation of a sealed V1 packet. |
| `core/data/a1_cpmm_sources.py`; A1 provider-source mapping/preparation | Two-sided USD valuation also consumes the CoinGecko candle contract. Replacing diagnostic evidence alone does not unblock A1 valuation or qualify the whole cycle. |
| `core/data/bounded_cycle_sources.py` | Provider-neutral discovery/pool-candidate abstractions preserve exact targets; they are not a provider-neutral candle admission owner. |
| `core/data/dexscreener_inspection.py` | Snapshot/identity inspection does not produce the required three original-time candle facts. |

No existing reusable alternative exact-pool OHLCV implementation was found in this bounded review. Closed P02/P03/P04/P05, Risk, paper lifecycle, persistence and audit owners retain their existing authority.

## 3. Candidate audit and unresolved capability gates

The candidate is **Bitquery `Trading.Pairs` over one HTTP GraphQL query**, not its blended `Trading.Tokens`/`Currencies` price, rank-1/top-market selection, subscription, Kafka feed, or legacy archive/backfill path. Official documentation distinguishes pool, venue and token/quote identities and exposes interval and OHLC fields. For Solana, `Pool.Address` and `Market.Address` identify the pool; `Market.Program` identifies its program. The portable exact-pool key is `Pool.Address`. A venue name alone is insufficient.

The documented USD construction is materially relevant: Bitquery normalizes the quote side, applies its price-index rules, and describes current quote valuation in pool-price normalization. Its token/quote orientation follows provider rules. These properties must remain visible, not be called CoinGecko semantics or proof of historical trade-time USD prices.

| Candidate surface | Decision |
| --- | --- |
| Bitquery `Trading.Pairs`, explicitly filtered exact Solana pool/token/quote/60-second interval | Conditional candidate for this boundary; account, coverage, orientation and closed-window semantics still require proof. |
| Bitquery `Trading.Tokens` or `Currencies`, rank-1/top-market selection | Excluded: can aggregate or change market authority rather than bind the supplied pool. |
| Bitquery legacy Solana archive/combined trade aggregation | Not selected: current official Solana documentation warns about incomplete historical coverage; fresh qualification would need a different bounded trade-aggregation contract. |
| CoinGecko Pro or another pool/profile of the existing Demo source | Not selected: no evidence that an account/host change cures this conformance failure. No new target trial is authorized. |
| Repository DexScreener snapshots | Excluded: do not supply this candle/time contract. |

**Documentation is candidate evidence, not capability qualification.** Before any candidate runtime implementation is selected, a governed capability record must resolve:

1. Exact selected CPMM pool coverage, token/quote orientation and returned identity fields on the intended account/product.
2. Whether three returned 60-second OHLC rows represent actual eligible trades within their respective intervals, without empty-interval carry-forward, rolling-hour replacement or cross-pool OHLC blending. Positive reported volume alone does not prove this.
3. Whether the historical interval's OHLC and USD construction respect the cutoff. If later trades or later quote repricing determine a claimed closed-window value, this profile is **INCOMPATIBLE**. A later receipt is permitted; later market input is not. Do not change cutoff semantics to accommodate it.
4. The provider's USD conversion/filter model and any upstream quote-source authority. The selected model must pass the governed capability review within controller-authorized scope; unavailable construction time or ambiguous semantics remain **CAPABILITY_UNVERIFIED**, not a synthetic source timestamp.
5. A fixed query/response schema, absolute interval filtering, completeness/truncation semantics, query cost, account entitlement and bounded limits. A wider lookup, pagination or schema-introspection request is not implicitly permitted.

This specification is coherent as a fail-closed admission boundary even while its candidate remains conditional. It does not assert that Bitquery currently satisfies items 1–5. If they cannot be established, stop at this boundary; do not implement a fake-positive adapter or silently choose a second provider.

### 3.1 Capability-evidence record — 2026-10-05

Historical record: **`bitquery-trading-pairs-capability-record-v1`**, documentation-only, with **controller acceptance PENDING at that source checkpoint**. The current authority and expanded findings are in §3.4. Review baseline: main `4f8fab992ec0acf28f07a99bfc63fff64338001a`; PR #145 MERGED / CLOSED, unchanged head `d3222e0803284f5978cc2214f1f003fc55820e11`; post-main CI #572 / `37313839114` SUCCESS, Python 3.13, whitespace and TypeScript; no competing open PR at startup.

Decision: **B — BITQUERY CONDITIONALLY SUITABLE BUT OFFICIAL CLARIFICATION REQUIRED**. Static official references E1–E15 below support the classified properties; no query, introspection, credential/account operation or provider qualification was performed. `PROVEN` means the expressly scoped documentary property, not tested runtime behavior, intended-account access or availability of three candles on an unspecified target. An example operation does not establish a pinned executable profile. Remaining qualification obligations are stated in every row.

| # | Capability | Classification | Authoritative evidence and remaining gap |
| --- | --- | --- | --- |
| 1 | Exact schema/query profile | **NOT PROVEN** | E1 “Schema and Fields” names `Price.Ohlc.{Open,High,Low,Close}`, `Interval.Time.{Start,End,Duration}` and identities; E3 identifies Pairs filter branches and operator families. E2 explicitly types Duration filters as `OLAP_Integer`; E1 defines `IsQuotedInUsd` as Boolean. A complete output SDL, nullability, numeric precision/serialization, timestamp precision, exact absolute interval predicates, immutable provider revision and full operation digest are absent from this record. E3 says leaf paths evolve and recommends introspection, which was not authorized or performed. V2 endpoint naming is not an immutable schema pin. |
| 2 | Exact pool binding | **PROVEN** — documented filter/identity semantics | E1's pool-key table identifies Solana `Pool.Address` and `Market.Address` as pool identities, and `Market.Program` as the DEX program. Its row-fan-out definition keys rows by market/pool/quote/token/interval. E3 documents exact `is` filters and AND of sibling predicates. This supports one selected-pool binding, without rank/top-market substitution. It proves neither intended-target data availability nor the temporal/authority correctness of upstream USD conversion. |
| 3 | Raydium CPMM coverage/program | **PROVEN** — documented general coverage | E4 explicitly directs recent CPMM swaps to Trading. E5 “How StonkFun works on-chain” identifies `CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C`; its FAQ links CPMM graduation, indexed programs, per-pool `Trading.Pairs` candles and protocol `raydium_cp_swap`. E1 supplies the program field's meaning. This is program-address evidence, not inference from a DEX name; selected pool/account coverage and returned program equality still require later qualification. No example pool is selected by this audit. |
| 4 | Original base/quote orientation | **REQUIRES PROVIDER CLARIFICATION** | E1/E7 identify Token as base and QuoteToken as quote; E3 exposes both predicate branches. E7 chooses stable/native quotes and otherwise a dynamic liquidity-based quote. Thus universal immutable orientation is **CONTRADICTED**, while exact predicates plus row checks can reject a mismatch. The literal Solana mint/WSOL representation and availability of the controller's original orientation on the intended product remain unresolved. The caller cannot force a reverse pair, infer an alias or invert candles. |
| 5 | Factual unique 60-second rows | **PROVEN** — documented construction/no-fill property | E2 “Supported Time Intervals” and “Bucket arithmetic” establish 60-second epoch-aligned sparse buckets with no fabricated empty bars. E1's OHLC field definition limits interval OHLC to trades with known USD values. Together with E1's row key, these resolve the documented interval/no-fill portion of §3 item 2. They do not promise trades in all three requested minutes, account/target coverage, complete ingestion or cutoff-valid USD inputs. Only an actual exact-window receipt could prove three usable rows. |
| 6 | Historical cutoff/as-of semantics | **REQUIRES PROVIDER CLARIFICATION** | E3 documents absolute time operators, but not an as-of source-availability snapshot. E8/E15 describe pre-aggregated recent Trading history, not immutable knowledge before C. A row-time predicate alone cannot prove all trade/quote facts were available before C, absence of later corrections, or that later computation excludes later inputs. No claim that every historical candle is repriced is justified either. |
| 7 | USD construction/authority | **REQUIRES PROVIDER CLARIFICATION** | E6 describes hour-window decay weighting, quote valuation at weighting time and a separate external spot pipeline for stablecoins. E1 distinguishes USD mode and quote-unit volume. How these rules apply to historical `Pairs.Price.Ohlc`, construction/input clocks, external quote authority and later recomputation is not established. Pair identity does not make the upstream USD model a same-pool trade-time price. Post-C inputs would make this profile incompatible. |
| 8 | Completeness/truncation/4-row sentinel | **REQUIRES PROVIDER CLARIFICATION** | E9 defines `limit.count` as a returned-row maximum and a 25,000-row default; E10 describes no total/`hasMore` flag for sweeps. Neither proves completeness of this exact Pairs profile or a stable ingestion snapshot. Four requested rows can expose visible overflow; three returned rows do not attest that a server cap, partial indexing or grouping omitted evidence. No pagination or added count query is authorized. |
| 9 | Entitlement/quota/cost | **REQUIRES PROVIDER CLARIFICATION** | E12 lists full-schema self-service access, Solana among core chains, a seven-day real-time trial with 1,000 points, personal/commercial license distinctions and recent OHLC retention. E11/E13 describe resource-dependent points; E12 also states five points per real-time call, and E13 states five per realtime cube. The applicable accounting for this exact Trading operation/account must be confirmed. E14 distinguishes quota, rate and shared-compute/entitlement blocks. A one-query attempt is offered in principle; cost, access and completion within 10 seconds/1 MiB remain unqualified. |
| 10 | A1 two-sided USD valuation | **NOT PROVEN** — independent blocker | Repository `core/data/a1_cpmm_sources.py::_price/map_valuation` require two CoinGecko-typed USD receipts, one per original reserve mint from the same pool/interval. This boundary admits only the original base-token diagnostic. E1 exposes one base-price OHLC and quote volume, not two separately bound historical USD candle receipts. Quote volume or USD/base ratios are not a substitute for the missing quote-side receipt. No A1 valuation replacement or integration is authorized. |

### 3.2 Resolved inclusive-to-exclusive interval representation

**CONTRADICTED:** equating Bitquery's raw `Interval.Time.End` directly with this contract's exclusive boundary. E2 documents raw End = Start + Duration - 1 second. For Duration 60, raw End is Start + 59 seconds and the canonical exclusive end is Start + 60 seconds.

The 2026-10-06 deeper review resolves this as a lossless representation mapping, not a candle-semantic incompatibility. Retain raw Start/End/Duration; require integral UTC seconds, Start aligned to 60, Duration = 60 and raw End = Start + 59; then represent canonical exclusive end = raw End + 1 = Start + 60. Reject inconsistent fields, units, unsupported typing or an unpinned profile. Do not move starts, alter prices, resample, deduplicate, fill, extend freshness or change cutoff/closedness. Original raw fields and the mapping/profile remain in provenance.

The new controller directive authorizes this narrow offline specification refinement. No runtime mapper or RTI-11 acceptance change is implemented. Exact output SDL/typing, historical USD/source-availability and completeness still require evidence; missing those facts continues to produce `CAPABILITY_UNVERIFIED`. Interval arithmetic alone is not candidate qualification.

### 3.3 Minimal questions requiring an official answer

Answers must identify the precise Trading.Pairs product/revision and distinguish documentary guarantees from account-specific availability. No message to Bitquery is sent by this review.

1. **Pinned profile:** Can Bitquery supply the supported SDL/revision, scalar precision/serialization/nullability, UTC timestamp units, literal mint fields and exact one-operation filter/projection for pool, program, Token, QuoteToken and Duration 60? Which absolute interval predicates implement [C-180s, C), and how do row Block.Time, raw inclusive End and construction time differ? Is a schema/model revision selectable, or must changes force client rejection and a newly reviewed profile?
2. **Coverage/orientation:** Does that product expose the original selected CPMM pool/program/mint tuple without pool blending or native/WSOL alias substitution, returning pool/program/base/quote identities on every interval? Can the required Token=original base orientation be absent or change, and how is a mismatch represented? Account/target verification must later use separately supplied public identities; this audit supplies none.
3. **Cutoff:** Does a historical query guarantee only trade and quote-source facts available before C? Can late ingestion, corrections/reorganizations, later trades or recomputation change a closed interval, and is there an as-of cutoff/watermark that proves the required source-availability boundary?
4. **USD/model:** Are Pairs OHLC extrema/opens/closes derived from eligible trades in that interval or from index/reference-price updates? Which quote-USD sources, weighting/conversion clocks and revisions determine each historical value? Can any input at/after C reprice it? Resolve the filter descriptions: E6 lists only zero/tiny-amount exclusions while E8 also describes MEV/outlier removal. Supply the relevant model/source-clock provenance; unknown upstream timestamps cannot be replaced by receipt time.
5. **Completeness:** For the fixed target/window, does one ordered query return a complete snapshot, without hidden caps, partial success, extra grouping or pagination? Is `limit.count=4` a reliable overflow sentinel, and what signal distinguishes missing trades from incomplete indexing/truncation? Returning three rows alone is insufficient.
6. **Account/budget:** Which license/plan, Solana/Trading entitlement and point accounting apply to this exact single query, including timeout/failed attempts? What account-level cost cap/access evidence can be provided without credentials or a purchase? Confirm feasibility under one attempt, 32,768 request bytes, 1,048,576 response bytes and a 10-second deadline. Those are client ceilings, not an assumed provider SLA.

These six groups were recorded under the historical evidence-only authority. Current offline implementation authority is supplied by the 2026-10-06 directive in §3.4; it does not supply the missing source facts. The deeper public research narrows the actual external evidence gate without sending a vendor message, opening an account or requesting credentials. The interval representation is resolved by §3.2; the remaining profile/cutoff/USD/completeness obligations are not resolved.

### 3.4 Deep public/source and alternative review — 2026-10-06

Current record: **[`exact-pool-candle-source-public-capability-review-v1`](EXACT-POOL-CANDLE-SOURCE-PUBLIC-CAPABILITY-REVIEW.md)**. Verified main `25afac375ad88bac64aa1862ccffb49087048a97`; PR #146 MERGED / CLOSED with unchanged head `329370e41cfcfe9d9bcc6cf48a4a94360f2c8f23`; post-main CI #574 / `37395411420` SUCCESS, Python 3.13, whitespace and TypeScript. No competing open PR at startup.

The record covers all 42 controller-requested Bitquery capability questions, official schema/operator/scalar and SDK/protobuf artifacts, pinned Raydium events/oracle, and 17 scoped alternative source/design surfaces. New substantive facts include scoped UTC/RFC3339 scalar semantics and WSOL Token versus Currency identity, the lossless inclusive-End mapping, Dune's interpolated/forward-filled minute USD and delayed Solana curated data, Codex event-based pool-price bars versus trade prices, paid T+1 CPMM Data Store limitations, SQD's explicit one-response continuation limit and the inability to inherit Snowflake Time Travel through imported data shares. A retained owned-table snapshot is a possible as-of mechanism, not an already provisioned Solana source profile. No provider/API data or sample dataset was requested.

**Decision: HARD_EXTERNAL_BLOCKER / NO IMPLEMENTATION-READY SOURCE PROFILE.** Bitquery Pairs remains conditional rather than globally rejected. The inspected public response contracts/artifacts do not establish the immutable knowledge-before-C historical trade/quote state, exact historical USD model/clock and complete bounded result needed by this contract. A later response hash, event timestamp, positive volume or three rows cannot prove those predicates. Raw reconstruction additionally needs complete transactions and an independent cutoff-valid USD authority; it does not bypass them. No runtime layer with invented positive fixtures is added.

The smallest next gate is the authoritative supported schema/model plus as-of/input-clock and one-operation completeness evidence bundle in the public review §6. Offline adapter/seam engineering is authorized when technically justified by that evidence; credentials and a latency test cannot substitute for missing internal historical guarantees. A1 two-sided USD remains independent and unqualified. This public-review milestone landed through PR #147, unchanged final head `8b02a7bc4bee14bd99ac992d365f95b74f349fee`, exact-head CI #576 / `37414523852` SUCCESS; resulting main `1e9c9b7245268ca43181cb241a37a0a7962cc1a2`, post-main CI #577 / `37421023822` SUCCESS. Closure reconciliation is batched with §3.5 under Rule 22.

### 3.5 Raw-trade reconstruction and explicit price basis — 2026-10-06

New record: **[`exact-pool-raw-trade-reconstruction-review-v1`](EXACT-POOL-RAW-TRADE-RECONSTRUCTION-DEPENDENCY-REVIEW.md)**, from exact main/tree `1e9c9b7245268ca43181cb241a37a0a7962cc1a2` / `8fe8f458a4bf62443c974d785540d458826d494f`. It audits the smallest RTI-11/P02/price-policy/A1 owners, pinned official CPMM swap events/instructions, standard RPC, Helius, Yellowstone/LaserStream, Triton/Fumarole/Old Faithful, Shyft, Bitquery raw trades, Vybe, Tardis and DexPaprika, retaining earlier candidate evidence.

**PRICE_DIRECTION arithmetic does not intrinsically require USD; current V1 measurement semantics do.** Native quote/base closes can produce a different direction from USD closes when the quote's USD price changes. A future native-only source must identify original quote units, rational values, fee basis and a new direction-policy/source lineage. It must not label native values USD, reuse `price-direction-v1` for a changed meaning, or alter the USD Pairs profile in §§4–10. P02's provider-neutral value shape is not independent source or signal authority.

Pinned CPMM events provide original mint/amount/fee facts suitable for deterministic native reconstruction. `base_input` is exact-input versus exact-output instruction mode, not requested base/quote orientation. Transaction/instruction identity, original decimals, complete ledger order, admitted clocks and an explicit quantity basis remain necessary. The conditional design requires exactly three factual minute buckets, exact rational OHLC/volume, full immutable provenance and pure replay; it does not permit deduplication, empty candles or gap filling.

**Selected conditional design: separate exact-trade/candle and USD-valuation responsibilities (option D); qualification stays HARD_EXTERNAL_BLOCKER.** Finalized retrieval, `minContextSlot`, block time, a terminal cursor and a later response digest do not themselves prove original knowledge before C or complete eligible trades. The public profiles inspected do not establish that full bounded packet. Helius is a candidate raw carrier and Old Faithful a ledger reference, not approved runtime sources. No production parser/builder/companion is added on invented positive evidence.

This separates the source facts needed for native construction from historical USD conversion and A1's two separately bound original-mint receipts. Native OHLC multiplied by a later/current quote price cannot supply historical USD OHLC or A1 valuation. The new record §8 defines the minimal evidence bundle and conditional implementation plan; implementation authority already exists when those correctness facts support it. The original target, factuality, cutoff, freshness, provenance, no-retry/fallback and one-operation/10-second/body ceilings are preserved. The offline batch was prepared first; remote compatibility was reverified before resuming publication. PR/required exact-head CI/merge/post-main evidence are PENDING at this source checkpoint.

## 4. Source authority and immutable request identity

The following are proposed identifiers, not existing runtime registrations:

| Field | Required binding |
| --- | --- |
| Boundary contract | `alternative-exact-pool-candle-source-v1` |
| Provider authority | `bitquery` |
| Source profile | `bitquery-trading-pairs-60s-usd-v1` |
| Adapter contract | `bitquery-exact-pool-candle-adapter-v1` |
| Logical endpoint version | `bitquery-http-graphql-trading-pairs-v1` |
| Logical method/host/path | HTTP `POST`, `https://streaming.bitquery.io/graphql` |
| Operation kind | One read-only GraphQL query; no mutation, subscription or batching |
| Price construction | Explicit Bitquery pair-level USD OHLC model, identified by a reviewed capability-record digest |

Source selection must be explicit, supported by the governed capability record and within controller-authorized scope before collection. The server-owned profile pins the host/path, operation, allowed fields, schema revision/profile and limits. A caller cannot supply an arbitrary URL/query or self-register a provider by changing a string. Unknown or unapproved profiles stop before I/O.

Each request binds boundary/provider/profile/adapter/endpoint versions; operation name and exact UTF-8 query SHA-256; canonical public variables SHA-256; original target reference ID/digest/version; complete target identities and orientation; reference/cutoff/window; freshness policy; and effective timeout/body/request limits. A request digest covers that complete descriptor. Stable canonical JSON uses sorted keys, UTF-8, compact separators, UTC times and finite decimal strings; credentials are absent.

The future implementation must freeze a literal reviewed operation and response-field/schema mapping under this profile. Those query/schema digests are **PENDING** in this specification; no runnable request or verified schema snapshot is fabricated. Schema/operation changes require a new reviewed profile/version, not automatic introspection or field guessing.

For a future separately authorized collector, the proposed configuration name is **`BITQUERY_ACCESS_TOKEN`** only. An intentionally provisioned bearer token is injected exclusively at the pinned TLS host. No credential value enters source, request digests, packet, logs, errors or PRs. Account authentication, token acquisition/refresh, billing and operational use are not authorized here. No environment proxy, redirect, alternate host or transport fallback is allowed.

## 5. Exact target and orientation

Input is one existing canonical target plus its original P02 predecessor and P03 safety/eligibility lineage. The public tuple is:

`(chain_id, pool_address, token_mint, base_mint, quote_mint, expected_program_id, target_reference_id, target_digest, target_contract_version)`.

- `chain_id` is exactly the repository's Solana identity. A documented profile maps it explicitly to Bitquery's `Solana` network; no symbol/chain alias inference is accepted.
- Pool/mint/program strings retain their exact case-sensitive public address identity. Base and quote are distinct and come from the original target owner; the candle adapter does not discover or recompute them.
- The bounded initial candidate orientation requires `token_mint == base_mint`. Returned `Token.Address` must equal that mint and `QuoteToken.Address` must equal the original quote mint. A quote-side token target is unsupported by this initial profile and stops before I/O; there is no inversion, orientation guessing or replacement mint.
- Every row must bind `Pool.Address == pool_address`, `Market.Address == pool_address`, the expected Solana network and the exact expected CPMM program. Missing or conflicting fields fail. A name such as “Raydium” cannot replace the program address.
- Program identity is checked against the already-established original source-verification authority. Bitquery's identity field does not establish genesis, executable/ProgramData verification, on-chain pool ownership or LEVEL 2. This candle boundary does not add an RPC request to obtain them.

The query filters the exact pool, token, quote, network/program, denomination and absolute window. It must not use ranking, `limitBy`, “latest token price”, discovery or mixed pools. All returned rows undergo identity checks; an unrelated row cannot be discarded to manufacture a valid packet. If the schema cannot express the bounded target and window, capability remains unverified and collection stops.

## 6. Factual candle and temporal admission

Freeze an explicit timezone-aware UTC `reference_time = R` before the first attempt. Let `C` be R truncated to its UTC minute. The only admitted candle starts are:

`[C - 180 seconds, C - 120 seconds, C - 60 seconds]`.

The requested interval window is `[C - 180 seconds, C)`. This does not authorize shifting R to find history. Original `Interval.Time.Start`, `End` and `Duration` must be retained; neither receipt time nor `Block.Time` is substituted for the start. Here, end means the **canonical exclusive boundary**. Bitquery's documented raw End is inclusive; §3.2 now defines its lossless mapping. The complete typed provider profile is still PENDING. Do not compare raw End directly to the exclusive boundary, use unsupported field semantics or interpret this specification as an implemented/qualified mapper.

Admission requires all of the following:

1. Exactly three original rows with unique, integral minute-aligned UTC starts; duration exactly 60 seconds; canonical exclusive end exactly start + 60 seconds. Raw order must be monotonic ascending or descending. Only after uniqueness/order/spacing validation may the adapter order the three rows ascending.
2. Starts equal the complete requested set, with adjacent spacing exactly 60 seconds. All starts are strictly below C; the latest end equals C. Every interval is closed at receipt (`end <= received_at`). A missing minute, older third candle, extra row or forming candle fails; no deduplication, truncation-to-three, resampling, interpolation or gap fill.
3. Three genuine provider OHLC rows backed by actual eligible trades within those intervals, according to the approved capability record. Require positive finite reported base and USD volume and `Price.IsQuotedInUsd == true`, but never treat those fields alone as proof of factual/no-fill construction.
4. OHLC/volume are exact finite decimal values, never booleans, NaN or infinity. Prices are positive; low <= open/close <= high; volume is not fabricated. Provider decimal strings or JSON numeric tokens are mapped losslessly according to the pinned schema, not through binary float conversion.
5. Original source observation time remains the candle start, preserving existing P02 observation semantics. The separate candle end, provider construction semantics and source receipt clocks remain in provenance. An absent provider update/conversion timestamp is explicitly absent; it cannot be filled with receipt time.
6. An explicit finite positive `FreshnessPolicy.stale_after` applies to **each** candle's original start at the supplied admission/evaluation time and, where applicable, final collection reference T. Negative age, expired oldest evidence, clock contradiction or cross-owner freshness/skew failure rejects the entire packet. No widening the policy to force admission.
7. UTC chronology is checked: R <= request start <= receipt <= processing <= evaluation. Independent monotonic elapsed time enforces the deadline. Retained clocks are observations, not defaults read during replay.
8. Only market inputs available before C may determine the candle, as required by §3. Historical computation/receipt may occur later only if the approved source contract proves the immutable before-C input set and excludes later trade/quote inputs. Post-cutoff market/quote inputs, unknown source-availability semantics, stale or future facts and unsupported schema fail closed even if row timestamps look valid. An event-time filter is not an as-of proof.

Observations are materialized through the existing P02-T07/T08/T09 owners using the exact original predecessor and explicit clocks/policy. All three must be admitted before any successful diagnostic/signal result. No partial observation collection is usable. PRICE_DIRECTION_1M retains the existing exact-decimal comparison of the final two admitted closes; this grants no new decision/economic meaning.

## 7. Budget, transport and no-retry policy

These are proposed **maximums for one alternative-source diagnostic incidence**, not operational authorization or a proven service SLA. A lower caller or existing aggregate limit wins.

| Limit | Hard maximum |
| --- | --- |
| Physical provider attempts | 1 HTTP GraphQL POST |
| Provider query operations | 1 read-only query, one exact target/window |
| Request body | 32,768 bytes |
| Response body | 1,048,576 bytes (1 MiB) |
| Per-attempt / total provider execution deadline | 10 seconds, including connection, headers and bounded body read |
| Returned rows requested | At most 4 as an overflow sentinel; exactly 3 admissible |
| Redirect, retry, fallback, token-refresh, pagination, polling | 0 |

The fourth-row sentinel detects overflow rather than selecting the first three. An extra row fails. The approved schema must establish whether a capped result can conceal additional rows; ambiguous server truncation/completeness is a capability STOP. The consumer may read at most one extra body byte to detect oversize; that byte is not admitted evidence. Interrupted/partial content or a declared-length mismatch fails. No automatic decompression or content transformation may bypass byte accounting or alter the digest of admitted bytes.

Reserve the entire permitted response cap and charge the physical attempt before I/O. Failed/denied attempts remain charged. A deadline miss is terminal; do not launch a replacement request. HTTP 200 with GraphQL `errors`, partial `data`, wrong content/schema, invalid UTF-8/JSON, duplicate object keys or non-finite JSON numbers is not success. Transport must check pinned TLS destination, status, bounded size, framing/truncation and complete response before admission; no raw provider error text is surfaced.

Future embedding cannot enlarge the existing A1 whole-cycle call/byte/time limits or silently reclassify Bitquery POST as CoinGecko GET. A concrete versioned aggregate budget must be reviewed before that embedding. This one-request contract proves nothing about the historical 46 RPC + 69 CoinGecko / 115-request cycle budget, its 86,597,632-byte cap or 180-second ceiling.

## 8. Receipt packet, provenance and deterministic replay

The source boundary produces an immutable raw-fact receipt, not a caller-asserted accepted diagnostic. It retains:

- The complete public request descriptor/digest from section 4 and original target/predecessor/safety lineage references.
- Exact response bytes, SHA-256 and byte count, content/schema profile, bounded HTTP status/result category, attempt number/count and monotonic duration.
- Original request-start and full-body-receipt UTC timestamps, supplied processing/evaluation times, R/C/window, freshness policy and effective limits.
- Each original candle start/end and explicit provider/model identity; query/variables/schema/capability-record versions and digests.
- A provider-issued response/request identifier only when documented and safe. Absence is marked `ABSENT`; the application's request digest must not be presented as a provider-issued ID.
- Deterministic bounded outcome/reason codes. Provider credentials, authorization headers, private routing, account details and raw exception/error text are excluded.

The raw body is never logged. If response/header retention risks exposing a credential, stop and do not publish/persist that body. A body hash establishes byte lineage, not authenticity, completeness, LEVEL 2 or independent provider attestation.

Pure admission/replay reparses the retained original bytes, verifies their digest and exact request/target/profile/clock bindings, and invokes the existing P02 owners. It reads no environment, clock or network and trusts no pre-asserted `PRODUCED` flag. Successful PRICE_DIRECTION_1M evidence and provenance carry `source_id=bitquery`, the exact source profile/adapter/endpoint/model/request/response identities and the admitted observation digests. They never carry CoinGecko provider IDs, request metadata or a CoinGecko adapter version.

Source substitution is an explicit new request with different provenance and digest. It is not a retry/fallback after CoinGecko failure. Identical payload bytes from two providers remain different source evidence. Any reuse key must include provider/profile/operation/variables/target/orientation/cutoff/freshness/limit/clock-context equality and preserve the original receipt; cross-provider cache reuse is forbidden.

## 9. Narrow RTI-11 compatibility seam

The future proposed seam contract is **`p01-rti-11-candle-source-v2`**. It is a companion opt-in request/result path, not permission to reinterpret `p01-rti-11-v1` or to relabel a Bitquery response as `OhlcvResponse`.

The seam is necessary at three tightly coupled points:

1. Replace the alternative path's CoinGecko-only request/envelope check with a typed, server-approved candle-source request/receipt binding and the strict raw admission in sections 4–8. Legacy V1 keeps its exact classes, profile and validation.
2. Apply the existing PRICE_DIRECTION_1M arithmetic to actual newly admitted observations while carrying the honest source binding. Never overwrite the existing CoinGecko policy's provider constant globally or accept externally supplied signal facts as canonical.
3. Add a source-aware RTI-11 diagnostic-success/lineage check for the companion request/result. Preserve exact candidate/target/P02/P03 handoff, one diagnostic admission, all-or-nothing observation/signal linkage, one existing canonical P04-to-P05 producer delegation and the current STOP boundary. An arbitrary callback declaring success is not a source authority.

The source-selection descriptor participates in the new request and result canonical digests. Legacy V1 representations, digests, stored results, rejection behavior and tests must remain unchanged. Existing P04/P05 domain owners and Risk are reused without changed acceptance or economic semantics. V2 wrappers cannot masquerade as V1 objects. OAF, downstream RTI callers and persistence consumers must continue rejecting unsupported versions until an explicitly reviewed compatibility integration is authorized; no automatic rollout is implied.

For A1, existing `a1-rti11-diagnostic-precollection-replay-v1`, packet membership/hash checks, CoinGecko request keys, host/method restrictions and durable audit identities remain unchanged. A later separately approved integration must version alternative raw receipts, ledger/source keys and replay/audit lineage, collect before irreversible seal T, and replay only the original retained facts afterward. No post-T I/O or clock/environment refresh is permitted. Preserve the bounded diagnostic-target cap, original P02/P03 target bindings, independent Risk veto and paper/audit consistency. This document does not define a replacement autonomous graph or authorize editing those owners.

**Remaining independent blocker:** A1's two-sided latest-closed-candle USD valuation still uses CoinGecko. This diagnostic source boundary neither substitutes those valuation facts nor proves an autonomous-paper cycle ready.

## 10. Deterministic fail-closed results

All non-success outcomes expose only stable reason codes and safe public binding/digest metadata. They emit no usable observations, signal or opportunity composition. No outcome schedules corrective work or retries.

| Outcome | Representative reason codes |
| --- | --- |
| `SOURCE_NOT_AUTHORIZED` | `UNAPPROVED_SOURCE_PROFILE`, `UNAPPROVED_SOURCE_SUBSTITUTION` |
| `CAPABILITY_UNVERIFIED` | `SCHEMA_NOT_PINNED`, `FACTUAL_CANDLE_SEMANTICS_UNPROVEN`, `USD_CUTOFF_SEMANTICS_UNPROVEN`, `COMPLETENESS_UNPROVEN` |
| `CONFIGURATION_INVALID` | `INVALID_TARGET_BINDING`, `UNSUPPORTED_ORIENTATION`, `INVALID_CLOCK_OR_LIMIT`, `CREDENTIAL_UNAVAILABLE` |
| `TRANSPORT_REJECTED` | `AUTHENTICATION_FAILED`, `RATE_LIMITED`, `QUOTA_REFUSED`, `REDIRECT_FORBIDDEN`, `UNEXPECTED_HOST`, `TIMEOUT`, `CONNECTION_FAILED` |
| `RESPONSE_REJECTED` | `RESPONSE_TOO_LARGE`, `TRUNCATED_RESPONSE`, `INVALID_JSON`, `GRAPHQL_ERRORS`, `UNSUPPORTED_RESPONSE_SCHEMA`, `SECRET_EXPOSURE_RISK` |
| `IDENTITY_MISMATCH` | `POOL_MISMATCH`, `PROGRAM_MISMATCH`, `TOKEN_MISMATCH`, `BASE_QUOTE_MISMATCH`, `SOURCE_BINDING_MISMATCH`, `RESPONSE_DIGEST_MISMATCH` |
| `CONTRADICTORY_EVIDENCE` | `CONFLICTING_DUPLICATE_CANDLE`, `CONFLICTING_INTERVAL_OR_PRICE_FACTS` |
| `TEMPORAL_INVALID` | `DUPLICATE_CANDLE_TIMESTAMP`, `NON_MONOTONIC_CANDLES`, `UNALIGNED_INTERVAL`, `FUTURE_EVIDENCE`, `OPEN_CANDLE`, `CUTOFF_VIOLATION`, `CLOCK_CONTRADICTION`, `STALE_EVIDENCE` |
| `INSUFFICIENT_HISTORY` | `MISSING_CANDLE`, `NON_CONTIGUOUS_CANDLES`, `WRONG_REQUESTED_WINDOW`, `NO_FACTUAL_TRADE_EVIDENCE` |
| `ADMISSION_REJECTED` | `INVALID_OHLC_OR_VOLUME`, `EXTRA_CANDLE`, `P02_ADMISSION_REJECTED`, `PREDECESSOR_OR_SAFETY_LINEAGE_MISMATCH` |
| `PRODUCED` | No reason codes; all three factual observations and honest signal provenance present |

Validation order is fixed: authorization/capability/configuration; transport/byte/JSON/schema; request and row identities/digests; numeric and interval structure; conflicting duplicate facts; duplicate/order/closed/cutoff checks; requested count/contiguity/freshness; original owner admission. Within a stage use the listed canonical field order and stable reason-code order. Conflicting rows for one timestamp are contradictory evidence; identical duplicates are temporal invalidity. Either rejects the full packet. Failed transport stops before attempting semantic interpretation of partial bytes.

## 11. Future acceptance evidence and next governed step

No executable tests or runtime adapter are added by this specification. A later explicitly authorized offline implementation must demonstrate, with original local fixtures and network prohibited:

- Three valid exact-window rows admit through actual P02 owners; honest source/receipt/query/digest lineage survives signal and companion RTI-11 checks.
- Both controller-reported duplicate/gap timestamp sequences reject, including identical and conflicting duplicate values. Three unique but non-contiguous rows also reject.
- Wrong pool/program/mint/quote, changing orientation, USD=false, fabricated empty candles, unsupported USD construction, stale/future/post-cutoff/open candles and altered hashes reject without partial output.
- Oversize/truncated bodies, invalid JSON, partial GraphQL errors, redirect/auth/quota/timeout/connection errors and unsafe credential retention stop after at most one attempted POST.
- Provider/source/version changes alter digests; there is no cross-source reuse, hidden retry/fallback or post-T I/O. Existing CoinGecko V1 behavior and canonical digests remain unchanged.
- Original P02/P03/P04/P05 and independent Risk authority remain intact. Tests of future A1 integration must preserve sealed replay and audit lineage; source-only fixture success is not cycle qualification.

The current controller directive already authorizes technically justified bounded offline adapter/admission, raw-trade reconstruction and companion-seam work. The first remaining dependency is **external source correctness evidence**, not another engineering permission request. For the USD Pairs profile, resolve §3.4's pinned schema/model, immutable before-C trade/quote inputs and complete bounded retrieval. For conditional native construction, §3.5's record separates exact complete before-C swaps and explicit native measurement/policy from the additional USD authority. Until the chosen profile is proved, it cannot honestly produce a successful diagnostic. Afterward, implement/test within the existing offline authority and prepare the exact operational packet. Real account/target access still needs separately explicit budget, environment, public identities and authorization; a documentation merge is not provider qualification.

| Activity | Authority in this milestone |
| --- | --- |
| Bounded repository/public-documentation audit, justified specification refinement, state reconciliation, PR/CI/guarded merge/main CI | AUTHORIZED |
| Technically justified offline source adapter/admission and narrow `p01-rti-11-candle-source-v2`, fake/injected transport and tests | AUTHORIZED BY 2026-10-06 DIRECTIVE; SOURCE CORRECTNESS EVIDENCE BLOCKED; NOT IMPLEMENTED |
| Existing CoinGecko V1/closed acceptance weakening or silent provider/A1 substitution | NOT AUTHORIZED |
| A1 source/replay/audit replacement | NO QUALIFIED VALUATION PROFILE / NO AUTOMATIC INTEGRATION |
| Real Bitquery/CoinGecko/Solana calls, credential use, token refresh, account purchase, migration | NOT AUTHORIZED |
| Provider-backed prepare, paper run/persist, full cycle, automatic discovery/polling/retry, scheduler/worker loop | NOT AUTHORIZED |
| Wallet/signing/broadcast/DEX execution/settlement/live or real-money autonomous trading | NOT AUTHORIZED / DISABLED |
| G2; G3/G4/P09; MASTER_BLUEPRINT change | BLOCKED / NOT AUTHORIZED |

## 12. Authoritative documentation reviewed

Review date: **2026-10-05 UTC**. These references inform candidate selection; they are mutable provider documentation, not a pinned schema, executed query or qualification receipt.

- [CoinGecko Demo pool OHLCV](https://docs.coingecko.com/demo/reference/pool-ohlcv-contract-address): request/time/orientation and empty-interval behavior.
- [Bitquery Crypto Price API](https://docs.bitquery.io/docs/trading/crypto-price-api/): product and interval scope.
- [Bitquery Pairs](https://docs.bitquery.io/docs/trading/crypto-price-api/pairs/): pool/venue/quote identity and response fields.
- [Bitquery OHLC API](https://docs.bitquery.io/docs/trading/crypto-price-api/crypto-ohlc-candle-k-line-api/): pair versus blended-token OHLC surfaces.
- [Bitquery Price Index Algorithm](https://docs.bitquery.io/docs/trading/crypto-price-api/price-index-algorithm/): filtering, weighting and quote normalization limitations.
- [Bitquery base/quote design](https://docs.bitquery.io/docs/trading/crypto-price-api/in-depth/): provider orientation rules.
- [Bitquery Solana DEX trades](https://docs.bitquery.io/docs/blockchain/Solana/solana-dextrades/): historical coverage caveats.
- [Bitquery authorization](https://docs.bitquery.io/docs/authorization/how-to-generate/): GraphQL endpoint and bearer authentication; no credential/token operation performed.

### Capability review evidence IDs

These are static official pages reviewed on 2026-10-05 UTC, with the specific sections named in §3.1. They are not executed queries, immutable SDL snapshots or operational receipts.

| ID | Authoritative page / section used |
| --- | --- |
| E1 | [Pairs](https://docs.bitquery.io/docs/trading/crypto-price-api/pairs/): pool keys, row fan-out, denomination, Schema and Fields |
| E2 | [OHLC](https://docs.bitquery.io/docs/trading/crypto-price-api/crypto-ohlc-candle-k-line-api/): Supported Time Intervals / Bucket arithmetic |
| E3 | [Trading filters/operators](https://docs.bitquery.io/docs/trading/query-operators/filters-and-operators/): leaf types, sibling AND, branches, evolving leaf set |
| E4 | [Raydium CPMM](https://docs.bitquery.io/docs/blockchain/Solana/raydium-cpmm-API/): Trading coverage / explicit program filter |
| E5 | [StonkFun](https://docs.bitquery.io/docs/blockchain/Solana/stonkfun-api/): program-address table and indexed-program/per-pool-candle FAQ |
| E6 | [Price Index Algorithm](https://docs.bitquery.io/docs/trading/crypto-price-api/price-index-algorithm/): filters, weighting, stablecoin source, quote normalization |
| E7 | [Base/quote design](https://docs.bitquery.io/docs/trading/crypto-price-api/in-depth/): quote-selection rules |
| E8 | [Trading data overview](https://docs.bitquery.io/docs/trading/trading-data-overview/): cleaned-trade stream and pre-aggregated OHLC |
| E9 | [GraphQL limits](https://docs.bitquery.io/docs/graphql/limits/): limit/count/default and pagination caveat |
| E10 | [Trading sweeps/pagination](https://docs.bitquery.io/docs/trading/query-operators/sweeps-and-pagination/): no total/hasMore and live pagination limitations |
| E11 | [Billing](https://docs.bitquery.io/docs/plans/how-billing-works/): resource points, plan/chain entitlement, trial and approximate record cap |
| E12 | [Current pricing](https://bitquery.io/pricing): access/license/trial/rolling-window and real-time-call accounting |
| E13 | [IDE points](https://docs.bitquery.io/docs/ide/points/): resource accounting, realtime-cube accounting and timeout charges |
| E14 | [Rate limits](https://docs.bitquery.io/docs/plans/rate-limits/): account rate, shared compute and entitlement blocks |
| E15 | [Coverage/retention](https://docs.bitquery.io/docs/graphql/data-coverage-retention/): Trading recent-history window and silently shorter out-of-window results |

Supplemental official examples inspected: [Traders API](https://docs.bitquery.io/docs/trading/crypto-trades-api/traders-api/), [historical TradingView guide](https://docs.bitquery.io/docs/usecases/tradingview-subscription-realtime/historical_OHLC/), and [Arc trade guide](https://docs.bitquery.io/docs/blockchain/arc-mainnet/arc-mainnet-trades-api/). Their examples, chart-side bar stitching and other-chain time notes do not prove this pinned Solana profile. The linked generic [schema overview](https://docs.bitquery.io/docs/schema/evm/top/) describes EVM, not a pinned Trading.Pairs SDL. No IDE query, introspection, live Usage API or alternative source was used.
