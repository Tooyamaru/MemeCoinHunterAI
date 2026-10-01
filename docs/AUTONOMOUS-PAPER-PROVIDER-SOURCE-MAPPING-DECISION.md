# Autonomous paper — concrete source mapping decision

Baseline: PR #130 merged at `c822e1300df67a8aaf1e786712ba76cb879daaf4`.
Status: BOUNDED SOURCE AUDIT COMPLETE / PROVIDER ADAPTER IMPLEMENTATION BLOCKED / CONTROLLER SOURCE-TIME DECISION REQUIRED.
Authority: controller handover `Pasted text(4).txt`, 2026-10-01 WIB. Offline adapter specification, implementation and fixture tests are authorized only when the existing source facts safely satisfy the canonical contracts. Operational provider calls and secrets are explicitly unauthorized.

## Verified capability and publication

PR #130 was merged through GitHub's real merge endpoint with expected head `fb7222e0052780c26a9d5b01cd1fba0dcec9ec71`. Exact-head CI run [529](https://github.com/Tooyamaru/MemeCoinHunterAI/actions/runs/36824161653) completed successfully: Python 3.13 tests (1,863 passed) and TypeScript checks/builds. Post-merge CI is [the exact c822e130 run](https://github.com/Tooyamaru/MemeCoinHunterAI/actions/runs/36829533386); its current result must be inspected separately before claiming main CI success.

`AutonomousPaperOneCycleService`, `BoundedDiscoveryOwner` and `BoundedPoolCandidateOwner` are now on main. Their provider-neutral contracts, selection policy, Risk Governor veto, simulation-only lifecycle and exact persistence/readback remain unchanged. The older PR #129 discovery/pool/score-order decision is resolved for provider-neutral composition; the blocker below concerns concrete source facts only.

## Exact blocker and repository evidence

| Required fact | Audited owner and evidence | Mapping result |
| --- | --- | --- |
| Unselected discovery with source event time and separate receipt | `artifacts/api-server/src/routes/candidate-listings.ts`: DexScreener latest profiles supply identity and metadata; the response retains HTTP `receivedAt` and `admission_status=NOT_ADMITTED`. `PROJECT_STATE.md` candidate-listing checkpoint explicitly keeps source freshness UNKNOWN. | Identities alone cannot populate the required source event time. No admitted canonical discovery output is selected. |
| Canonical source-event provenance | `core/data/bounded_cycle_sources.py`: batch source identity, source-event identity, aware source/receipt clocks and exact batch receipt linkage are required before P02-T04/T05/T06 admission. `core/data/discovery.py::_from_adapter_observation` maps `raw_event.event_time` to discovery time. | A deterministic digest can identify an adapter occurrence but cannot establish the missing source clock. Provider order cannot establish cursor continuity. |
| Liquidity USD with source observation time | `core/data/dexscreener_inspection.py` preserves `liquidity` and `pairCreatedAt`, but explicitly records `NO_DOCUMENTED_MARKET_FIELD_OBSERVATION_TIMESTAMP`. `core/data/market_data_temporal_evidence.py` requires `source_observed_at=None` and `source_freshness=UNKNOWN`. | `liquidity.usd` is a usable numeric source field; its observation age is unavailable. No canonical pool source is selected under V1 freshness rules. |
| Pool freshness and one-shot budget | `CanonicalPoolObservation.validate` requires a source clock plus receipt/reference/freshness consistency. `core/data/dexscreener_transport.py` allows two HTTP attempts. | Existing transport cannot be wired unchanged into the zero-retry cycle. A new injected one-attempt transport seam would solve retry control, but would not solve source time. |
| Existing source with anchored time | `core/data/solana_oaf_source.py` obtains finalized `context.slot` and `getBlockTime(slot)` for one supplied mint. `docs/P01-OAF-01-TRUSTED-SOLANA-UPSTREAM-SOURCE-AUTHORITY.md` prohibits receipt time replacing discovery/safety observation time. | Time authority is available for selected-mint verification, not an unselected universe or canonical pool liquidity USD. Reusing it unchanged does not complete discovery/pool mapping. |
| Existing CoinGecko owner | `core/data/coingecko_onchain_ohlcv.py` and `core/data/coingecko_onchain_orchestration.py` require an already selected exact pool. Candle timestamps are real source time. | The existing OHLCV owner is not discovery or a pool-reserve/liquidity source. Candle time cannot timestamp unrelated profile/liquidity fields. |

The official [DexScreener API reference](https://docs.dexscreener.com/api/reference), inspected on 2026-10-01, documents identity/metadata for latest profiles and `liquidity.usd`/`pairCreatedAt` for token pairs. It does not document a profile observation or liquidity update timestamp for these endpoints. `pairCreatedAt` describes pool creation, not observation of current reserves; HTTP receipt or response-generation time cannot prove when market fields were observed. This conclusion combines the documented schema with the repository's explicit UNKNOWN-time contracts; no operational API response was fetched.

Two deterministic local probes confirmed that V1 rejects missing discovery event time and missing pool observation time with `CycleSourceError("invalid source clock")`. They used constructed facts only and performed no network access. This is a genuine missing fact, not a test or adapter parsing defect.

## Controller options

| Option | Concrete direction using represented providers/owners | Tradeoff and exact authorization needed |
| --- | --- | --- |
| A — source-anchored path (preferred under current guarantees) | Keep original-source freshness mandatory. Specify a bounded unselected Solana ledger discovery owner and a separate timestamped pool/USD-valuation authority; reuse the finalized slot/block-time convention from the existing Solana owner. | Stronger evidence, larger bounded source milestone. Authorize an offline source-authority specification identifying exact discovery RPC methods/programs, pool layout/reserve facts, USD valuation source/time, cross-source lineage and finite request/byte/slot budgets. Existing selected-mint RPC and OHLCV do not already provide these capabilities. Stop again if no USD owner can be proven. No operational access implied. |
| B — receipt-observed listing/snapshot policy | Reuse DexScreener profiles plus token pairs, with an explicitly new snapshot admission policy that distinguishes adapter observation/receipt recency from UNKNOWN provider update age. | Smallest reuse path, weaker freshness guarantee. Requires an explicit controller amendment to the autonomous source contract and acceptance policy; it cannot be implemented by filling current `event_time`/`observed_at` with receipt time. Preserve original P02/P03 owners and UNKNOWN provenance, define whether such snapshots are acceptable for paper selection, and keep independent source-backed P03 evidence mandatory. Authorize offline specification first; implementation only after that contract is reconciled. |
| C — CoinGecko source-authority audit | Reuse the represented CoinGecko provider family and audit its documented network new-pools and token-pools REST contracts for a bounded discovery/pool mapping. | One provider family may cover both fact types, but these are new owners. `pool_created_at` and reserve values alone do not establish current liquidity observation time. Authorize an offline endpoint/field/time/identity/budget specification; do not assume the existing exact-pool OHLCV mapping covers these fields. Implementation remains conditional on proof of the required clocks. No API key or provider call is authorized. |

Option A is preferred when preserving V1's original-source freshness is mandatory. Option B is the least implementation work only if the controller explicitly accepts its weaker freshness semantics. Option C is a bounded alternative audit, not a solved timestamp mapping. No option is silently selected or implemented by this packet.

## State, scope and next gate

- Concrete discovery: BLOCKED; preferred existing DexScreener listing cannot satisfy current source-time requirements.
- Concrete pools: BLOCKED; DexScreener provides liquidity USD but no documented observation timestamp for that field.
- Provider-neutral cycle: IMPLEMENTED / MERGED; offline contract coverage and PR-head CI PASS. This does not claim provider-backed operational success.
- Provider-bound adapters/contracts: none created. Do not add a fake positive adapter whose timestamp fields merely conceal absent source facts.
- P03/P04 overall remain open. No new residual P03/P04 task is selected; this source-time decision is the current upstream blocker.
- Whole-program historical estimate remains approximately 68%; controlled-paper/operator remains historical 95%+. These estimates are not remeasured or increased by this audit. Autonomous one-cycle composition has offline proof; concrete provider readiness is BLOCKED, operational one-cycle verification is NOT EXECUTED, live execution readiness is not quantified.
- No runtime secrets/API keys, operational DexScreener/CoinGecko/Solana requests, provider-backed cycle/smoke, polling, retry, scheduler, wallet/signing, DEX execution or settlement occurred. GitHub operations and public documentation lookup are distinct from operational provider activity.
- G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED. `MASTER_BLUEPRINT.md` is unchanged.

Exact next gate: controller selection of the source-time/freshness authority in A, B or C, followed by the selected bounded offline specification. Only a demonstrably compatible mapping may then proceed to injected-transport adapters, contract/integration fixtures and PR/CI/merge. Operational provider verification remains separately unauthorized.
