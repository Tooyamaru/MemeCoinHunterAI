# Bounded post-A1 P03 offline implementation dependency review

## Verified closure

PR #138 MERGED / CLOSED; exact head `d5b144ac22d5da56e6da5c5233851265917b9c40`; exact-head push CI #554 / run `37025114858` and PR CI #555 / run `37025119666` SUCCESS; merge/main `652ec1c32c6ed01beff8e088932b97caab4d1751`; post-merge main CI #556 / run `37030291596` SUCCESS. Python 3.13 and TypeScript checks/builds PASS in all three runs. The tested local tree, exact PR-head tree and landed implementation tree are identical: `9e967879698e9e64c07f83172c5a504dd9032919`.

Starting main: `baf27d47eba399066555e03323c0c03d0a9b0182`. Implementation branch: `feature/a1-p03-safety-precollection-replay`. Contract: `a1-p03-safety-precollection-replay-v1`.

Actual local Python 3.13 validation: 58 focused contract tests plus 2 raw-P03/real-paper-owner integration tests PASS; 269 relevant regression tests / 86 subtests PASS; compilation and whitespace PASS. Offline/injected evidence does not qualify operational providers.

This review reads only relevant owners on the verified merged main. It introduces no successor specification, interface, budget admission or implementation. Documentation closure/review landing has its own PR/CI evidence.

## Remaining dependencies

| Dependency | Repository evidence and status |
| --- | --- |
| A1 and P03 common collection/replay | CLOSED offline: one ledger/final T, exact canonical discovery binding and evidence-only P03 replay. |
| RTI-11 diagnostic precollection/replay | Missing production source seam. Market composition accepts an injected diagnostic but defaults to operational `run_ohlcv_diagnostic`; existing orchestration validates exact selected target/predecessor and invokes one diagnostic. |
| Operational adapter qualification | Actual endpoints/provider profiles remain unqualified. No real request was made. |
| Durable collection audit linkage | Common packets are immutable in-memory lineage; no durable collection audit persistence was added. |
| Quota/latency | Selected account credits/shared usage, quota fit and latency remain unmeasured. |
| Qualifying runtime/database | Offline temporary SQLite tests do not attest a deployed stable single-process application and connected durable database. |
| Provider-backed paper smoke | Unexecuted, requires separate controller authorization after dependencies. |
| Live economic authority | Disabled; not a continuation of this offline gate. |

## Diagnostic reuse requires an exact contract

The common packet admits A1 and P03 physical attempts only. No RTI-11 collection stage is admitted. Existing frozen A1 valuation OHLCV responses are potential reuse facts, not an approved general diagnostic adapter. Completed collection cannot be reopened, appended to, or followed by provider I/O after T.

`OhlcvRequest` includes chain, token, pool, base/quote target, reference time, timeout and body cap. Its minute URL encodes aggregate 1, limit 3, USD currency, exact token, no empty intervals and cutoff timestamp. URL equality alone does not encode base/quote orientation, full reference/context, timeout or cap. A1 canonical pool observations orient the base to the candidate mint; original raw request/response metadata must remain authoritative. Same URL/body therefore cannot prove complete diagnostic equivalence.

The integration test injects the existing `ReplayOwners(packet.a1).diagnostic` candle fixture. It demonstrates raw safety replay through actual canonical paper owners, Risk veto and terminal persistence/readback. It does not establish production diagnostic replay for every exact selected target.

The selected pool is known only after canonical discovery, safety evaluation/eligibility and pool selection. Future diagnostic replay must bind to that exact pool and actual predecessor identities without rerunning P02/P03 or changing ranking.

## Smallest proposed next gate

Propose **OFFLINE SPECIFICATION-ONLY bounded RTI-11 diagnostic precollection and pure replay**, with exact selected-pool/P02/P03 binding and explicit A1 candle-reuse rules.

A separately selected future contract would need to settle:

1. Full target/request/context/policy/cap/clock/composition equivalence for reuse, including candidate orientation.
2. Original receipt and source-time lineage plus explicit dependency/reuse links.
3. Which facts require separate bounded pre-T collection when exact reuse is impossible.
4. Complete ledger coverage without reopening a sealed ledger or creating post-T authority.
5. Binding to the actual canonical selected pool and predecessor; existing RTI-11/P04/P05 semantics remain authoritative.
6. Fail-closed offline acceptance cases, including non-equivalent targets and clock/identity/cap conflicts.

This is a dependency finding for controller selection, not a formal successor specification. No successor implementation is authorized. Existing ceilings remain 46 RPC, 69 CoinGecko HTTP-class calls, 115 total physical HTTP-class calls and 86,597,632 reserved bytes, with the existing diagnostic reservation bounded to five calls. No enlargement or implicit borrowing is selected.

## Evidence scope and authority

Relevant evidence: `core/data/a1_p03_collection.py`, `core/data/a1_cpmm_sources.py`, `backend/application/market_to_opportunity_composition.py`, `core/data/coingecko_onchain_ohlcv.py`, `core/data/coingecko_onchain_orchestration.py`, `tests/test_a1_p03_collection_integration.py`, and the prior bounded A1 dependency review. No repository-wide scan.

Local Git fetch stalled during documentation closure; exact main and relevant source content were verified through GitHub. No new local test result is claimed for this documentation-only checkpoint.

No operational market-provider call, credential exposure, wallet/signing, broadcast, DEX execution, settlement or live trade. Risk Governor remains independent, mandatory and higher authority. LEVEL 2 remains NOT VERIFIED. P03/P04 overall and historical progress estimates unchanged. G2 BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 NOT AUTHORIZED.

Review COMPLETE. STOP for NEW controller selection. Any future provider-backed I/O or secrets require separate explicit controller authorization.
