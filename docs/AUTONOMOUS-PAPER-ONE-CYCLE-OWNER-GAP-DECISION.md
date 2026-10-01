# Autonomous paper one-cycle — canonical discovery and pool decision packet

**Baseline:** GitHub `main` `a1907061071f8b6e7d2d1c3f27ff6f68cb3d347b` (PR #128 merged, main CI pass).
**Status:** BOUNDED OWNER AUDIT COMPLETE / IMPLEMENTATION STOPPED / CONTROLLER DECISION REQUIRED.
**Scope:** reconcile the controller's one-shot paper-cycle decision with existing owners. This is an audit and decision packet, not a completed implementation specification or runtime authorization.

## Verified owner chain

| Stage | Repository owner | Proven usable boundary | Gap for this one-cycle request |
| --- | --- | --- | --- |
| P02 discovery | `core/data/adapters.py`, `discovery.py`, `discovery_orchestration.py`, `materialization.py` | P02-T03 defines an adapter protocol and deterministic fake; T04 accepts one supplied observation; T05 forwards an accepted result; T06 materializes it and exposes a canonical ordered current view. | No production owner in this path acquires an unselected candidate event or enumerates a one-shot universe from an explicit invocation. An empty in-memory materializer does not discover tokens. |
| Selected Solana mint | `core/data/solana_oaf_source.py`, `backend/application/oaf_trusted_prepare.py`, `oaf_solana_upstream_composition.py` | A bounded finalized snapshot of **one supplied mint** can produce exact P02 current-token and paired P03 evidence/evaluation/eligibility for OAF prepare. | It requires `token_mint` before the call and cannot decide which token to inspect. Existing authority applies to the explicit operator-selected prepare, not an unselected universe acquisition. |
| Candidate listing | `artifacts/api-server/src/routes/candidate-listings.ts` | Bounded DexScreener latest-profile listing, order/duplicates/invalid entries preserved. | Listing is `NOT_ADMITTED`; it has no canonical P02 event time/cursor/continuity or P02 admission authority. It cannot be promoted by renaming its result. |
| Pool target | `core/data/coingecko_onchain_orchestration.py`, `docs/P04-LME-03-CONTROLLED-ORCHESTRATION-SPECIFICATION.md` | `ExactPoolDiagnosticTarget` accepts a **caller-chosen** chain/token/pool/base/quote and reference; LME-03 validates it and invokes the exact-pool diagnostic at most once. | LME-03 explicitly does not discover, rank or select pools and forbids choosing highest-liquidity/volume pool. No canonical pool-candidate set or authoritative ordering metric is produced there. |
| Opportunity and downstream | `backend/application/market_to_opportunity_composition.py`, P05 score owner, PFX/PFS/CIP/OCI/OSC, RTI-03 | RTI-11 consumes exact P02 predecessor, paired P03 output and exact pool target; on diagnostic success it calls the canonical P04/P05 producer. Existing decision, Risk/Capital veto, paper lifecycle and exact terminal persistence/readback owners remain available for a qualifying single case. | Their availability does not create discovery or pool selection. No owner may be rerun or bypassed to mask upstream absence. |

The read-only DexScreener token-pairs inspection also preserves every source pair without selecting one; its transport may retry a token lookup. It is neither an admitted discovery stream nor a canonical pool-selection owner under the current contract.

## Material ordering contradiction

The requested order is `discovered candidates → P03 PASS → market evidence → P05 score → select token → select pool`. The existing RTI-11 request **requires** `ExactPoolDiagnosticTarget` before the controlled OHLCV diagnostic. Only after that exact-pool diagnostic succeeds does it call `produce_canonical_p04_to_p05` and yield a P05 score. Therefore a comparable P05 score for each candidate cannot be obtained under this owner chain while pool choice remains deferred until after candidate selection.

One admissible future design could choose a canonical pool for **each** eligible candidate before scoring, with independently authorized per-candidate bounded diagnostic calls. Another could consume already-produced canonical score snapshots that carry exact pool/identity/provenance. Neither path is currently established by this decision, and neither may be inferred from the one-cycle or one-discovery cardinality. A selector must never invent a score, compare scores across mismatched reference clocks/policies, or reuse a score from a different pool.

## Exact controller decisions needed

1. **Discovery fact source:** Identify an approved one-shot source/owner that can return one bounded set of candidate events or an already-admitted canonical universe snapshot without a manually preselected token. Specify source event identity, observation/receipt times, ordering/continuity/resync, freshness, bounded cardinality, and how the existing P02-T03/T04/T05/T06 owner accepts it. If a current canonical materializer is proposed, identify the producer and proof that its entries are already admitted/current; do not accept browser-authored canonical objects or `NOT_ADMITTED` profiles.
2. **Pool candidates and metric:** Identify the authoritative pool-candidate source/owner and an existing or explicitly approved deterministic comparable metric, with source time, chain/token/base/quote linkage, required fields, missing/tie handling and one-shot budget. LME-03's caller-owned target reference is validation/provenance, not that source or metric. If the metric requires a new domain/source contract, authorize that gate separately.
3. **Score/selection order:** Choose whether pool selection occurs for each candidate **before** canonical P05 scoring, or whether existing trusted pool-bound scores are supplied by a separately identified canonical owner. Bind a single reference/evaluation/freshness policy across candidates and numeric maximum candidates/provider calls. Only then can the highest-score lexical identity tie-break be specified without a circular dependency.
4. **Trigger and mutation access:** The selected explicit caller-directed `AutonomousPaperOneCycleService` is a bounded proposal, not a scheduler. Before operational wiring, specify service credential/authorization and whether one invocation may automatically pass review/run/persist. The current browser bearer and process-local handle do not grant this authority.

Until (1)–(3) have exact owner and evidence answers, the implementation gate fails closed before any discovery fetch, market diagnostic, P05 score, paper lifecycle or persistence. The terminal outcome vocabulary from the controller request remains a future facade contract, not a substitute for missing owners. No `CYCLE_COMPLETED` claim is made.

## Reconciliation with PR #128 and governance

PR #128 remains a **draft conditional contract**; its earlier "unselected" discovery/pool entries are now a verified owner gap, and its prohibition on score-ranked selection is superseded only as a proposed policy **after** canonical score production and exact pool-order resolution. This packet does not modify canonical P02–P07 owners or silently amend their contracts. The documented alternatives are a controller decision point, not implementation choices delegated to the facade.

No source call, runtime secret access, provider-backed smoke, operational paper experiment, worker/scheduler/retry, wallet/signing, DEX execution or live/economic action was performed. P03/P04 overall are not closed. G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**; G3/G4/P09 remain **NOT AUTHORIZED**.
