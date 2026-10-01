# Paper-only one-cycle composition — bounded specification gate

**2026-10-01 controller amendment:** The historical decision hold below is superseded for the bounded provider-neutral gate by `AUTONOMOUS-PAPER-ONE-CYCLE-SPECIFICATION.md`. Discovery/pool contracts and application service are implemented with verified offline contract coverage; PR #130 tracks publication and CI evidence. No concrete provider or operational call is authorized by this amendment.

**Baseline:** GitHub `main` at `4d383e40e052fd58199cc8ec64830b552b8475b8` (post-operator dependency review, PR #127).
**Status:** DRAFT CONTRACT / CONTROLLER DECISIONS REQUIRED / RUNTIME NOT AUTHORIZED.
**Scope:** one finite paper-only candidate cycle. This document does not authorize a source call, unattended service, scheduler, provider-backed smoke, economic settlement, or execution.

## 1. Existing ownership

| Concern | Reused owner and boundary | Rule for this cycle |
| --- | --- | --- |
| Discovery admission | P02-T03/T04/T05/T06 | Consume an admitted, current, ordered event and its materialized state; the operator-selected Solana mint validation for OAF is not a discovery stream. DexScreener latest profiles remain `NOT_ADMITTED`. |
| Current-token and safety | Existing bounded Solana RPC P02/P03 prepare path | Preserve exact mint, finalized ledger observation time/slot, receipt time, and paired P03 evaluation/eligibility. The approval for one explicit operator prepare does not authorize repeated or unattended RPC use. |
| Exact-pool market and opportunity | RTI-11 through P04-LME-03 and the existing canonical P04/P05 chain | Preserve one selected candidate, mint, exact pool/base/quote, reference time, freshness and provenance. Do not fabricate a P04 snapshot, P05 score, or source time. |
| Decision, veto and paper admission | P06, independent Risk/Capital Authority, P07 and PFX/PFS/CIP/OCI/OSC | An explicit policy decision and independent risk veto precede any simulation-only paper lifecycle. STOP and rejection remain first-class terminal outcomes. |
| Case and durable result | OAF process-local exact-object registry; RTI-03 terminal persistence/readback | Current operator bearer and opaque case handle are not unattended service authorization. No cross-process/restart-safe active-case reconstruction or global exactly-once claim. |

The closed explicit operator sequence remains prepare → review → run once → optional persist once → RTI-03 readback. The new cycle cannot simply replay that HTTP sequence with a script: its human review, mutation authority, and source-call scope are distinct decisions.

## 2. Conditional one-cycle contract

A proposed cycle has one externally selected trigger/event, a bounded candidate set, one selected exact candidate/pool, one explicit reference/evaluation clock, one paper-only decision, and one finite terminal record. The following order is a **design constraint**, not a runtime grant:

1. Admit the triggering event through an approved source and P02 owner. Verify source identity, event/observation/receipt time, ordering, continuity, currentness, duplicate/contradiction and resync state. Missing or contradictory facts terminate without selection.
2. Apply a separately approved deterministic candidate and exact-pool selection rule to only admitted current entries. Resolve chain, token mint and pool identity before trusted prepare. Zero, ambiguous or conflicting eligible targets terminate; no score-ranked or symbol-based fallback.
3. Check authenticated service identity, explicit paper-only scope, source budget, environment and independent stop/kill-switch state before any provider request. Retain the event and policy-version references as bounded audit metadata without forging canonical P02/P03 provenance.
4. If and only if independently authorized for unattended use, invoke the existing trusted Solana P02/P03 path and bounded RTI-11 diagnostic for the one selected target. Keep ledger observation and provider candle interval separate from receipt/evaluation time. Canonical source failure, stale evidence, unknown/ineligible safety, or identity mismatch is STOP. No polling, fallback source or retry.
5. Reuse PFX/PFS/CIP to prepare one exact case in one stable process. Any risk rejection or non-materialized result is terminal for the candidate; an opaque handle locates exact in-memory objects but is never a credential or durable job ID.
6. A separately approved unattended mutation policy must explicitly decide whether review can be replaced by a machine-verifiable precondition, whether OCI run-once is permitted, and whether RTI-03 persist-once is permitted. Without each corresponding decision, stop at review, terminal run, or unpersisted result respectively. Never hide a second owner invocation in review, run, persist, or readback.
7. Preserve the existing OCI/OSC/P07 simulation-only STOP and terminal semantics. Persist only an eligible exact lifecycle object through RTI-03, then read back its exact digest. Durable terminal readback proves only the paper lifecycle result, not economic realization.

One cycle is finite and does not schedule its successor. No background refresh, retry loop, automatic discovery subscription, periodic timer, autonomous token selection, wallet/signing, RPC/DEX execution or live trading is part of this contract.

## 3. Failure, budgets and recovery

A later approved specification must bind numeric maximum events/candidates/provider calls, timeout and response-size bounds, freshness windows, clock source, per-source rate budget, registry capacity/TTL and finite cycle duration. No positive default is inferred here. One event may produce only one selected candidate/pool under the eventual policy; a second selection is a separately admitted cycle, not an implicit retry.

Every stage must have a bounded terminal class: `NO_ADMITTED_EVENT`, `NO_UNAMBIGUOUS_TARGET`, `AUTHORITY_UNAVAILABLE`, `SOURCE_UNAVAILABLE`, `STALE_OR_CONTRADICTORY_EVIDENCE`, `SAFETY_OR_RISK_STOP`, `PREPARATION_STOPPED`, `RUN_TERMINAL`, `RUN_OUTCOME_UNKNOWN`, `PERSIST_TERMINAL`, or `PERSIST_OUTCOME_UNKNOWN`. These are **specification labels**, not new API/domain enums. The underlying owner reason/status and digests must remain intact. Uncertain run or persist outcomes never trigger automatic reinvocation. A process restart invalidates active process-local cases; terminal RTI-03 readback can investigate persistence uncertainty but does not reconstruct a pre-run case.

A controller-selected Risk Governor must be able to veto before preparation and again at the governed decision/run boundary without bypassing the existing Risk/Capital owner. The exact veto owner, signal source and fail-closed policy remain unselected. A STOP is not permission to relax safety, freshness, identity or source budgets.

## 4. Controller decisions required before implementation

| Decision | Required exact selection | Current disposition |
| --- | --- | --- |
| Discovery | Provider/source owner, event schema, source event identity, observation and receipt clocks, ordering/cursor/continuity and resync rule; explicit read authority | **Unselected.** Selected-mint Solana RPC is not autonomous discovery; DexScreener profiles are unadmitted. |
| Selection | Candidate eligibility, exact pool mapping/tie-break or fail-closed ambiguity rule, policy/version owner and per-cycle cardinality | **Unselected.** Operator's manual candidate/pool selection does not delegate selection authority. |
| Trigger and access | Permissible external trigger, non-browser service principal/credential, mutation permissions, one-cycle claim/duplicate handling, operator override/kill switch | **Unselected.** Existing single-controller bearer cannot be silently reused by a worker. |
| Provider and clocks | Separate bounded unattended Solana/CoinGecko scope, numeric quotas/timeouts/freshness, rate ownership and missing-source STOP | **Unselected.** One explicit operator prepare authority does not extend to repeated calls. |
| Risk and actions | Independent veto policy; exact human-review substitution, OCI run and optional RTI-03 persist permissions; finite terminal projection | **Unselected.** No unattended mutation is authorized. |
| Process and recovery | Single-process lifetime, case TTL/capacity, unknown outcomes and restart handling; any durable cycle ledger only under a separately owned contract | **Unselected.** RTI-03 stores terminal lifecycle, not active case replay. |

**Decision point:** The controller must select an approved discovery source/event and exact candidate/pool rule, then specify trigger/service authority and per-stage mutation permissions. If those cannot be supplied under existing owners, the cycle remains blocked and the missing source/owner requires its own authority gate. A documentation status change cannot satisfy this decision.

## 5. Future acceptance evidence, not an operational experiment

Only after those decisions and separate runtime authorization, deterministic doubles/fixtures should prove: admitted event and identity continuity across P02→P03→RTI-11→P04/P05→Risk/P07; bounded one-shot source counts; duplicate/ordering/ambiguity/freshness STOP; no hidden provider calls; independent veto; exact object/digest lineage; concurrency run-once and persist-once claims; uncertainty after failure; finite process-local expiry; no unauthorized mutation; and exact RTI-03 readback. Tests must make zero uncontrolled live provider requests and no operational paper experiment.

The existing provider-backed controlled-paper smoke remains a **separate** operational gate requiring its own explicit authorization, qualifying single-process host, connected database and intentionally available secrets. This document neither closes P03/P04 phase coverage nor changes G2 **BLOCKED / UNRESOLVED / NOT AUTHORIZED** or G3/G4/P09 **NOT AUTHORIZED**.
