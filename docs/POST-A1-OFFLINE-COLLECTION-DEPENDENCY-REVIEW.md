# Post-A1 offline transport/collection dependency review

Status: BOUNDED REVIEW COMPLETE / NEXT GATE PROPOSED FOR CONTROLLER SELECTION.
No successor specification, implementation or provider execution is authorized by this review.

## Verified baseline and scope

Reviewed GitHub main `2e4b5c847d458ece293f6889f8e782b3df0c867d` after PR #135 merged.
Final closure head `8cafd868a89f99fa918912a1ca68a4dea1fc52cc` has exact-head
CI #547 / run `36966905725` SUCCESS. Post-merge main CI #548 / run
`36970039513` SUCCESS. Both runs have successful Python and TypeScript jobs.
PR #134 implementation and its exact-head/main CI #541/#542 remain the
implementation evidence. A1 OFFLINE TRANSPORT/COLLECTION MILESTONE CLOSED;
closure documentation fully landed and verified.

Read REPLIT_RULES.md, then PROJECT_STATE.md. Inspection was limited to the
A1 collection/budget/transport/preparation contracts and existing safety,
diagnostic, cycle, persistence and single-process runtime seams listed below.
No repository-wide scan, new dependency, source change, workflow change,
MASTER_BLUEPRINT change, operational provider request or secret access.

## Findings and remaining dependencies

| Area | Existing proof / reusable owner | Remaining gap and gate type |
| --- | --- | --- |
| A1 transport and accounting | Injected bounded no-default-opener transport, strict response checks, pre-call finite accounting, exact collection-local valuation dedup and immutable completed T are implemented offline. Whole-cycle caps reserve 46 RPC plus 69 CoinGecko calls, 115 HTTP total. | Reservations do not collect missing facts or qualify a real injected opener. Adapter conformance can first be specified and tested offline; actual endpoint behavior requires separately authorized operational evidence. |
| Common collection lifetime | collect_once creates its own ledger/transport and seals registry and ledger before returning the completed packet. The packet carries verification, discovery, reserve/valuation envelopes and source/receipt/request/body lineage. | P03 and diagnostic packets are absent. Appending after T or reopening the sealed ledger is incompatible with the contract. A common pre-T session/freeze seam must be specified before adding either stage. |
| P03 safety | SolanaJsonRpcSource preserves source block time separately from receipt time. Existing OAF composition derives authority and holder-concentration evidence, then canonical P03 evaluation/eligibility. The one-cycle owner requires evidence bound to its exact discovery P02 predecessor. | The existing source uses getAccountInfo, getTokenLargestAccounts, getTokenSupply and slot block-time lookup; getTokenLargestAccounts and getTokenSupply are not in A1's RPC allowlist. Its default urllib path is not A1-qualified and lacks the common ledger. Full OAF compose creates a separate selected-mint P02 predecessor. A bounded raw-fact precollection and pure replay contract must preserve existing safety semantics while binding the exact A1 discovery predecessor. |
| RTI-11 diagnostic | Existing controlled composition validates exact token/pool/P03 identity and delegates one diagnostic to unchanged P04/P05 owners. CoinGecko transport already has finite request/body/timeout and no-redirect semantics. Offline integration injects replayed candle bodies. | Default diagnostic performs provider I/O and reads runtime credentials; it cannot be invoked as a post-T default. Exact independent diagnostic request/window/cap/timeout, original clocks, selected pool/mints and common ledger lineage need a separate precollection/replay gate. Valuation response reuse requires exact request/context equivalence, not merely the same URL or body. |
| Collection audit persistence | Frozen A1 in-memory lineage and existing RTI-03 atomic lifecycle persistence/readback are separately implemented. | No durable A1 collection packet or cycle/lifecycle link exists. RTI-03's closed lifecycle artifact family has no collection artifact. Specify a separate credential-safe audit contract; do not arbitrarily enlarge the closed owner. Frozen wire requests retain endpoint text: future durable audit must exclude credential-bearing endpoint/header material while retaining verifiable sanitized identity/digests. No committed credential was observed. |
| Quota and latency | Offline caps disclose 46 RPC + 69 CoinGecko, reserved maximum 86,597,632 bytes, aggregate deadline <=180s and stricter same-minute cutoff. Selected safety cap must be <=256 KiB, timeout <=30s. | Actual selected-account quota, credits, shared usage and latency remain unverified. A plan's advertised rate and fake timing are insufficient. Account evidence and any actual provider measurement require a separate authorized packet; budgets must not be silently enlarged. |
| Runtime / database | Existing operator readiness requires exact environment, connected durable database and configured services. The launcher fixes one worker and no reload; active cases retain process-local ownership. | A manifest-only check is declarative, not a database/provider/runtime attestation. A known stable process, intentionally provisioned secrets and connected durable database need real environment evidence. The Replit autoscale target remains non-qualifying. No restart-safe active-case reconstruction is selected. |
| Cluster / program | Offline mandatory mainnet genesis and Raydium executable/loader-v3 ProgramData LEVEL 1 checks exist before admission. | Verification against the selected real endpoint remains operational evidence. LEVEL 2 deployed binary/source equivalence is NOT VERIFIED; offline fixtures do not change that status. |
| Paper authority / terminal outcome | Existing one-cycle composition preserves P03 before pool selection, exact RTI/PFX/PFS/CIP/OCI/OSC owners, mandatory independent Risk veto and terminal RTI-03 persistence/readback. Fake full-chain tests prove offline composition and veto. | Those tests use synthetic safety and temporary SQLite; they do not prove real P03 precollection or operational readiness. One provider-backed paper preparation/invocation and terminal STOP require separate controller authorization after remaining gates. No loop or live authority follows from closure. |

## Smallest natural next gate

Proposed next gate: **offline specification-only A1 P03 safety precollection and
exact-predecessor replay**, including only the common pre-T ledger/freeze seam
necessary for that safety handoff. Controller selection is still required.
This review is not that formal specification and creates no interface or
implementation authority.

Why this gate: P03 is the first missing source-backed stage in the existing
cycle, and it must run before candidate pool selection/RTI-11. The A1 collector
currently seals its local session before that stage can be added. Blindly
wiring the existing OAF source/composer would introduce an unqualified
transport or a different P02 predecessor. A contract decision resolves these
specific blockers without redesigning the completed cycle or specifying all
remaining operational work at once.

The proposed specification should settle:

1. A finite, validated mint set from the bounded discovery facts, capped at
   five; pre-T collection must not assume a different final P02 membership,
   freshness decision or selection policy. Define fail-closed handling when
   final pure replay rejects a collected mint.
2. At most thirty charged safety RPC attempts, including block-time lookups,
   in the same whole-cycle ledger; exact methods, commitment, IDs,
   timeout <=30s and selected body cap <=256 KiB. Any narrow method/scope
   extension must be explicit and reviewed; this review authorizes none.
3. Immutable raw safety facts and exact request/body/receipt/slot/source-time
   lineage collected before T. T must be completed and immutable only after
   all admitted precollection stages finish; no ledger reopening, hidden
   transport calls, retry or post-T I/O.
4. Pure replay at the same final T into the exact A1 discovery state
   version/digest/contract and token/chain identity, reusing existing safety
   semantics and canonical P03 evaluation/eligibility ownership. Do not
   recompute the OAF selected-mint P02 predecessor or duplicate Risk logic.
5. Preserve original source times; missing, stale, future, contradictory,
   partial, malformed, identity/predecessor mismatch or budget failures
   fail closed under existing STOP semantics. Receipt time is not source time.
6. Offline acceptance cases for source/receipt lineage, frozen T, exact
   predecessor matching, finite accounting and no-network replay. Synthetic
   safety is insufficient to prove source-backed replay.

Explicitly excluded from this proposed gate: concrete operational adapters,
RTI-11 replay implementation, durable audit storage, quota/latency measurement,
runtime launch/database attestation, provider-backed smoke/cycle, source/binary
LEVEL 2 verification and any owner redesign. These remain separate gates.

After controller selection, prepare and review the narrow formal offline
specification first. Implementation requires its own explicit authorization.
No provider request is needed to resolve the proposed contract.

## Evidence paths and verification limits

- core/data/a1_operational_collection.py — collection-local session, packet and seal/T lifecycle.
- core/data/a1_collection_budget.py — scope reservations, immutable sealed ledger and finite caps.
- core/data/a1_bounded_transport.py — injected opener, current methods and strict transport boundary.
- core/data/solana_oaf_source.py — safety calls, block-time cache and default transport.
- backend/application/oaf_solana_upstream_composition.py — compose creates P02; safety mapping binds supplied p02_ref.
- backend/application/oaf_trusted_prepare.py — existing selected-mint upstream composition.
- backend/application/autonomous_paper_one_cycle.py — exact discovery predecessor, safety-first order and Risk/persistence ownership.
- backend/application/market_to_opportunity_composition.py — controlled diagnostic and handoff.
- core/data/coingecko_onchain_diagnostic.py and core/data/coingecko_onchain_transport.py — operational defaults and bounded GET semantics.
- tests/test_a1_collection_integration.py — fake HTTP, synthetic safety, replay injection and offline proof limits.
- backend/application/paper_lifecycle_persistence.py — closed terminal lifecycle artifact family.
- scripts/operator_single_process_runtime.py and .replit — portable one-worker launcher and non-qualifying autoscale target.
- docs/AUTONOMOUS-PAPER-A1-PROVIDER-EXECUTION-PREPARATION.md — remaining execution prerequisites.

Review used repository facts, not runtime or provider measurements. Local
execution runtime became unavailable after closure verification; no new local
test result is claimed for this documentation checkpoint. Remote GitHub
closure evidence remains verified. The review is complete; landing its
documentation checkpoint has a separate PR/CI state.

## Authority preserved

Risk Governor remains independent, mandatory and higher authority than the
AI/Decision Engine. P03/P04 overall status and historical progress estimates
remain unchanged. G2 BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 NOT
AUTHORIZED. No wallet, signing, broadcast, DEX execution, settlement, live-money
trading, scheduler, worker, retry or provider loop. Prime Agent remains a design
reference; Firecrawl/OmniRoute remain deferred. No external integration was
selected or installed.
