# Autonomous paper one-cycle — provider-neutral V1

Baseline: `main` `a07b9a5f19a1fedbbea4f2145ee8c9812a7242e4`, after PR #129.
Status: IMPLEMENTED / OFFLINE CONTRACT COVERAGE VERIFIED. PR #130 tracks publication and exact-head Python 3.13/TypeScript CI; both jobs are mandatory before merge.
Authority: controller amendment in `Pasted text(3).txt`, 2026-10-01 WIB, authorizes specification, provider-neutral discovery/pool owners, thin application composition, deterministic offline tests and normal PR/CI/merge workflow. It supersedes the unresolved decision slots in PR #128/#129 for this bounded implementation only.

## Source and admission contracts

`core/data/bounded_cycle_sources.py` defines `DiscoverySource.discover_once`, `DiscoveryBatch`, `BoundedDiscoveryOwner`, `DiscoverySnapshot`, `DiscoveredCandidate`, `PoolCandidateSource.pools_once`, `CanonicalPoolObservation` and `BoundedPoolCandidateOwner`. Contract version: `bounded-paper-cycle-source-v1`.

One injected discovery source invocation returns a tuple of at most 64 P02-T03 `AdapterObservation` event envelopes, one source identity, explicit receipt identity and receipt timestamp. Each event must have chain/token identity, source-event identity, source event time and separate receipt time. Only `DISCOVERED` events are allowed. Receipt time must equal the batch receipt and adapter observation time. Event time must not exceed receipt, receipt must not exceed reference, and event age must satisfy the explicitly supplied freshness policy. Discovery payloads are canonical JSON bounded to 8 KiB per observation.

Identical repeated source events/tokens collapse; conflicting versions of either identity invalidate the batch. Sort unique tokens lexically by `(chain_id, token_mint)` and retain at most five. Admission uses the original numeric source cursor order where present, without rewriting cursors; canonical P02 continuity, out-of-order and resync rejection remains authoritative. Route selected events through P02-T04, T05 and T06; any rejection invalidates the entire invocation-local snapshot. Candidate IDs are `candidate:` plus SHA-256 of the canonical JSON chain/token pair. The returned predecessor is built from the actual P02 materializer; no browser-authored accepted object or DexScreener `NOT_ADMITTED` profile is promoted. No previous cycle state is reused.

A pool source is invoked once for each eligible candidate and returns at most 20 immutable observations. Every observation carries chain/token/pool/base/quote, finite nonnegative `Decimal` liquidity in USD, source/reference identity, observation time, receipt time and contract version. Base must equal the candidate token; quote must differ. Freshness and identity are required. Identical pools collapse; conflicting pool observations or any invalid pool facts fail closed for that candidate. There is no volume substitute. Select highest liquidity USD; break ties by lexically smallest pool address. The exact LME target reference digest binds all pool facts, including liquidity and clocks. Existing LME validation retains authority over supported chain and address syntax.

Injected sources must implement a bounded one-shot operation; this contract provides no network implementation or timeout worker. Concrete source/provider mapping and operational access require a later gate. The bounded fake sources are test fixtures, not a claim of production discovery connectivity.

## Application invocation and selection

`AutonomousPaperOneCycleService.run(AutonomousPaperCycleRequest)` is one direct async application invocation, contract `autonomous-paper-one-cycle-v1`. No public endpoint, bearer impersonation, worker, scheduler, polling, retry, second cycle, wallet, signing or economic authority is provided.

The caller supplies invocation identity, one aware reference/evaluation time, processing time, explicit freshness, diagnostic timeout (positive and at most 30 seconds) and response limit (at most 1 MiB). Evaluation time must equal reference time. The service has injected discovery, safety evidence, pool, RTI-11 diagnostic composition, paper request factory and persistence owners; it constructs no concrete provider. Each call has local state; no globally exactly-once/restart/concurrent invocation claim is made.

For each of at most five admitted candidates:

1. Obtain one canonical P03 evidence collection tied to the exact discovery predecessor digest. Verify identity, source time and freshness. Reuse P03-T02 evaluation and P03-T03 eligibility derivation. Rejected candidates do not reach the pool owner.
2. Obtain one bounded pool set and select exactly one pool under the metric above.
3. Invoke RTI-11 at most once for that candidate, reusing LME-03, the closed-candle mapper, `PRICE_DIRECTION_1M` and canonical P04/P05 producer.
4. Retain only canonical composed results. Compare scores only under the exact default P05 ruleset digest, contract/evaluator versions, common reference/evaluation clocks, identical source candle timestamps, and matching feature versions, units, quote currency, reference and freshness. Any comparability mismatch stops before selection.

After bounded evaluation, choose highest canonical P05 score, then lexical `(candidate_id, chain_id, token_mint)`. Exactly that candidate/pool result enters the paper path. The selector never computes its own score or reruns market evidence for the winner.

## Reused paper owners and stops

The explicit paper request factory must return an `OafPrepareCaseRequest` retaining the exact selected RTI-11 result in both PFX and PFS requests. It supplies simulation facts/policy explicitly; no defaults or provider fetch are added.

The service calls PFX first: RTI-12/P05-T06–T08 → RTI-13/P06 → RTI-14/independent Risk/Capital. P06 actions other than BUY terminate as `DECISION_REJECTED`; Risk/Capital must explicitly approve. A veto stops before PFS/CIP/lifecycle. Then PFS creates simulation-only fill/evidence, CIP prepares the exact OSC-02 request, and OCI invokes OSC-02 → RTI-15/P07 admission → RTI-16/RTI-02 controlled lifecycle. All exact request/object links and canonical owner result contracts are verified. This reuses owner authority and does not copy business rules or amend closed owners.

Only `OBSERVATION_PRODUCED` lifecycle output is persistence-eligible for this cycle. Invoke RTI-03 persist once. Require `STORED` or `ALREADY_STORED` and the exact lifecycle digest. Invoke RTI-03 read once; require `FOUND`, that same lifecycle root and matching artifact count. Any failure stops without fallback or reinvocation. The returned immutable result preserves per-stage owner outcome/reasons/digests, discovery receipt reference, selected pool provenance, final candidate/token/chain/pool and durable result digests. Lifecycle readback remains paper evidence, not economic settlement.

## Budgets

| Operation | Maximum per invocation |
| --- | ---: |
| Discovery source requests | 1 |
| Raw discovery observations | 64 |
| Canonical candidates considered | 5 |
| P03 evidence collections | 5 (one per candidate) |
| Pool source requests | 5 (one per eligible candidate) |
| Pool observations per candidate | 20 |
| Selected pools per candidate | 1 |
| Exact-pool diagnostics | 5 (one per eligible candidate with a valid pool) |
| Final paper candidate / lifecycle | 1 / 1 |
| Persistence / readback | 1 / 1 |
| Retry / scheduler / automatic successor | 0 / 0 / 0 |

## Terminal vocabulary

`CYCLE_COMPLETED`, `NO_DISCOVERY_CANDIDATES`, `NO_ELIGIBLE_CANDIDATE`, `NO_VALID_POOL`, `MARKET_EVIDENCE_UNAVAILABLE`, `OPPORTUNITY_REJECTED`, `DECISION_REJECTED`, `RISK_OR_CAPITAL_REJECTED`, `PAPER_NOT_ADMITTED`, `PAPER_TERMINATED_WITHOUT_PERSIST`, `PERSISTENCE_FAILED`, `READBACK_FAILED`, `INVALID_INPUT`, `OWNER_UNAVAILABLE`.

Underlying reasons remain in bounded stage evidence. Source/owner exceptions never cause retry. Partial upstream failures may remove a candidate; downstream failure of the selected candidate terminates the cycle and never selects a fallback candidate.

## Acceptance and next gate

Offline tests use actual canonical P02/P03/P04/P05/P06/Risk/PFS/CIP/OCI/OSC/P07/RTI owners, injected deterministic facts and SQLite durable storage. They prohibit socket connections and verify identity, ordering/duplicates/cardinality, liquidity/ties, safety and decision/risk vetoes, score comparison/ties, mutation budgets, persistence failures and exact readback.

This milestone does not close P03/P04 overall, execute provider-backed smoke, or establish live readiness. Historical whole-program estimates are unchanged; no autonomous production percentage is justified by fake-source success. The next gate is separately authorized concrete source/provider mapping and operational verification of its fact contracts, budgets and comparable evidence. The existing controlled-paper provider-backed smoke remains a separate authorized operational decision. G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.
