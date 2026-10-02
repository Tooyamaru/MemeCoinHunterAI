# A1 P03 safety precollection and exact-predecessor replay

Status: SPECIFICATION COMPLETE / SPECIFICATION-ONLY / IMPLEMENTATION NOT AUTHORIZED.
Contract: `a1-p03-safety-precollection-replay-v1`.
Controller selection: attached continuation of 2026-10-02 WIB. This document
authorizes no source implementation, operational adapter, provider request or
paper experiment. PR landing and CI are separate workflow facts.

## 1. Verified baseline and narrow boundary

Base main: `9136242516449cd26e0e176834d4c7ddc1151f4d`, the actual squash merge
of review PR #136. Its exact head `8057e78953de7bcc9097b091782f4063b5a352bd`
passed CI #549 / run `36974451027`; post-merge main CI #550 / run
`36987290844` SUCCESS on this exact base, Python and TypeScript PASS.
The dependency review is landed in
`POST-A1-OFFLINE-COLLECTION-DEPENDENCY-REVIEW.md`. A1 offline implementation
and closure through PR #134/#135 remain closed.

The gate settles only raw P03 precollection, its necessary shared pre-T
session/ledger/freeze, and pure handoff to the exact A1 P02 predecessor and
existing P03 owners. It preserves the legacy SPL CPMM event universe, lexical
five selection, reserve/valuation arithmetic, source clocks, opt-ins and
LEVEL 1 verification. It does not redesign P03 or add safety domains.

Required order: discovery raw facts and P03 raw facts enter one bounded
pre-T session; admitted collection closes; the ledger seals and final T
becomes immutable; pure A1 replay delegates once to canonical P02 discovery;
P03 replay binds that exact returned predecessor; canonical P03 evaluation
and eligibility remain with their existing owners.

Future diagnostic facts would also have to enter before this same freeze
under a separately authorized contract. This version admits only A1 and P03
stages; a diagnostic stage is not implemented or admitted here. The sequence
`A1 collection -> freeze T -> provider P03 calls` is forbidden. An already
completed v1 packet cannot be extended to add safety facts.

## 2. Ownership and the evidence-only replay seam

| Responsibility | Sole existing owner / required behavior |
| --- | --- |
| A1 raw discovery/reserves/valuation | `core/data/a1_cpmm_sources.py`; unchanged mapper and injected source semantics. |
| Canonical discovery | `BoundedDiscoveryOwner` and P02-T03/T04/T05/T06; one actual materialization, yielding the original `DiscoverySnapshot` and `P02T07PredecessorContext`. |
| Safety fact translation | Reuse the pure `OafSolanaCanonicalComposer._compose_p03` mapping in `backend/application/oaf_solana_upstream_composition.py`, with the exact A1 `P02StateReference`. A narrowly shared pure helper may be extracted later without changing mapping semantics. |
| P03-T01 | `TokenSafetyEvidence`, `SafetyProvenance`, `SafetyEvidenceCollection`; preserve canonical versions and validation. |
| P03-T02 | `evaluate_safety_evidence`; evaluation at T, exactly once per admitted candidate. |
| P03-T03 | `derive_token_eligibility`; consume that exact evaluation once, preserve paired timestamp/references/version. |
| Decision / capital / lifecycle / persistence | P05, independent mandatory Risk Governor, P07 and RTI owners remain unchanged and outside the new source seam. |

The replay source conforms to existing
`SafetySource.evidence_once(candidate, snapshot, reference_time=T)` and returns
only the canonical `SafetyEvidenceCollection`. It must not evaluate or derive
eligibility itself: the existing one-cycle P03 stage already does both.
An offline P03-only acceptance harness may call those two canonical owners
once and STOP at their paired result, without starting pools or RTI-11.

Never call full `OafSolanaCanonicalComposer.compose`: it invokes `_compose_p02`
and would produce a second selected-mint predecessor. Never construct an OAF
default network source, duplicate safety rules, or interpret eligibility as
Risk/Capital approval. No alternate Decision Engine or Risk authority exists.

## 3. Frozen inputs and packet identity

This is an in-memory logical contract, not a public API or durable schema.
Required session inputs are one collection ID, environment, intended mainnet
genesis identity, selected sanitized provider identity, existing `A1Policy`
and `A1OperationalBudget`, explicit finite safety timeout/body cap, explicit
`FreshnessPolicy` with positive finite `stale_after`, and explicit finite
`max_top_holder_fraction` in [0, 1]. No favorable threshold default is allowed.
The holder threshold retains the existing mapper's float comparison semantics.
The same captured freshness policy must be supplied to discovery and P03;
A1's separate source-age/skew policy is also enforced, never loosened.

| Immutable material | Required contents |
| --- | --- |
| Common context | Contract/transport/budget/mapper/source versions, collection ID, environment, sanitized source identity, genesis and program LEVEL 1 evidence, start, planned cutoff, final T, policies, closed stage manifest, sealed whole-cycle ledger and packet digest. |
| A1 stage | Original verification/discovery/reserve envelopes, exact USD responses/reuse lineage and unchanged source mapping material; all belong to this session. |
| Safety manifest | Ordered lexical set of zero to five exact Solana mints and their original A1 source-event IDs, discovery scope digest and raw discovery lineage; not a claimed P02 admission. |
| Per-mint raw facts | Original bytes for three context reads and their block-time dependencies; exact method/params/RPC ID, attempt ID, body/request digests, start/receipt, source slot/time and dependency/reuse links. |
| Post-T discovery binding | Separate immutable binding of packet digest, T, captured discovery arguments, original returned snapshot/candidates, source/receipt identity and complete predecessor identity. Its digest does not mutate the frozen collection. |

Canonical digest material uses deterministic sorted-key compact JSON, finite
values, UTF-8, UTC aware timestamps and SHA-256, following existing A1
canonicalization. Bodies are represented by their SHA-256 and length; raw
bytes are retained privately for replay. Policies, thresholds, versions,
ordered attempts and every dependency link are bound. Never accept an opaque
digest without validating its underlying immutable material. Runtime secret
material is excluded from exported canonical lineage (section 10).

`SolanaMintSnapshot` is a replay-local translation view assembled from those
bytes. Its nested result mappings/lists are not authoritative frozen storage
and must not escape as mutable shared packet state. Published raw tuples,
bytes, bindings and canonical evidence are immutable; replay cannot edit them.

## 4. Bounded precollection membership

Validate the complete existing A1 raw discovery scope before selection: one
finalized block, existing transaction/instruction/event/token bounds, and
legacy SPL semantics. Select exactly the same lexical at-most-five mints
used by A1 and `BoundedDiscoveryOwner`. Preserve the corresponding raw
source-event identity; no browser-selected or additional mint is admitted.
Do not manufacture canonical candidate IDs before the P02 owner returns them.

Precollection is speculative raw sourcing, not canonical discovery. Collect
at most once for each selected mint. An empty valid scope has zero safety
calls and retains the existing empty-discovery STOP outcome.

After T, the sole P02 delegation must admit exactly this selected set. If
final A1/P02 replay rejects a selected mint, becomes invalid/stale, or a
precollected mint is absent from final canonical membership, STOP the whole
handoff and publish no partial safety success. This preserves current
`BoundedDiscoveryOwner` behavior, which rejects an invalid selected snapshot.
Do not continue with a reduced fabricated snapshot, refill from the sixth
token, expand discovery, refund spent calls, or collect again.

A valid canonical P03 INELIGIBLE/UNKNOWN result is different: existing P03
and cycle owners retain that candidate outcome and exclude it from pool
continuation. Other originally admitted candidates may follow existing pure
cycle rules. No replacement candidate or provider lookup follows rejection.

## 5. Minimum raw facts and explicit method profile

All three token reads use the exact selected mint and finalized commitment
on the same verified provider binding. No pagination, account enrichment or
second mint lookup exists. This version uses fresh token reads rather than
silently reusing A1 base64 reserve mint accounts as jsonParsed safety evidence.

| Method | Exact params / minimum raw source facts |
| --- | --- |
| `getAccountInfo` | `[mint, {encoding: jsonParsed, commitment: finalized}]`; non-null parsed mint, exact legacy SPL owner matching A1, context slot, initialized mint/decimals, explicitly present `mintAuthority` and `freezeAuthority` fields with valid null-or-key values. Missing fields are partial evidence and STOP, never inferred disabled authorities. |
| `getTokenLargestAccounts` | `[mint, {commitment: finalized}]`; context slot and complete bounded returned account list, exact unique account addresses, non-negative integer amount strings and matching decimals. Preserve the full returned list and its order; no favorable truncation. At most 20 entries; excess/empty or malformed evidence STOP. |
| `getTokenSupply` | `[mint, {commitment: finalized}]`; context slot, positive integer amount string and decimals matching the mint and holder facts. Preserve supplied fields; UI quantities never replace raw integer amounts. |
| `getBlockTime` | `[exact_context_slot]`; original finite non-negative ledger timestamp for each distinct token-read context slot; null, malformed or unavailable time STOP. Retain exact lookup request/response lineage. |

The existing generic A1 RPC allowlist already contains `getAccountInfo` and
`getBlockTime`. The only new method admissions specified are
`getTokenLargestAccounts` and `getTokenSupply`, justified by the existing
top-holder-concentration mapper. They are allowed only in the P03 safety
profile. Existing discovery/verification methods and commitments are unchanged.
Token-2022 remains outside the A1 legacy universe even though the older
selected-mint OAF source accepts it; this gate cannot broaden discovery.

A future explicit `rpc_safety` helper must admit only the four table methods,
validate the exact params/context target, and construct a bounded POST with
scope/kind `safety`. It uses the existing injected transport, same ledger and
strict `RpcEnvelope` parser. Current `A1BoundedTransport.rpc` always builds
scope `solana`: using it unchanged for safety would defeat kind accounting
and is forbidden. Keep its legacy default behavior; do not relabel safety
calls as discovery. No allowlist/helper code is changed by this specification.

Require exact `jsonrpc=2.0`, globally unique positive integer RPC IDs within
the session, matching response ID, valid result and no RPC error. Wrong
method, target, ID, duplicate JSON keys, malformed/non-finite JSON, unexpected
HTTP status, redirect or missing result fail closed under bounded transport.

Within one mint, each distinct context slot needs at most one block-time
lookup. Same-slot dependencies may reference that exact original receipt
without another call; their logical uses remain explicit. No cross-mint,
cross-cycle, module-global or prior-collection safety clock cache is selected.
A mint therefore needs at most three context reads plus three time lookups.

## 6. Exact budget and reservation

| Scope | Maximum RPC | Maximum CoinGecko HTTP | Reserved body-byte maximum |
| --- | ---: | ---: | ---: |
| Existing A1 collection | 16 | 64 | 73,490,432 |
| P03 safety, 5 × (3 + up to 3) | 30 | 0 | 7,864,320 = 30 × 262,144 |
| Existing separate diagnostic reservation, inactive here | 0 | 5 | 5,242,880 |
| Unchanged whole-cycle ceiling | 46 | 69 | 86,597,632 |

Existing caps are sufficient: 16 + 30 = 46 RPC; 64 + 5 = 69 CoinGecko;
115 physical HTTP maximum. A1 plus P03 may consume at most 110 HTTP and
81,354,752 reserved bytes; the five diagnostics are a disclosed reservation,
not five calls executed by this gate. No budget enlargement is required.
Lower caller-selected caps are honored and may STOP before all five mints.

Before every physical call, reserve kind, selected host, total/RPC/host/kind
call counts and the full selected body cap in the same `A1BudgetLedger`.
Safety calls, including time lookups, are kind `safety`, at most 30, with
timeout >0 and <=30 seconds and body cap >0 and <=256 KiB. Timeout must fit
the remaining existing aggregate deadline <=180 seconds; no timeout clipping
that silently changes a captured request. The same-minute cutoff may stop
earlier. Legacy A1 RPC <=10 seconds and all other existing caps remain intact.

One pending request at a time, no concurrent unaccounted calls, zero retry,
redirect, provider switch or hidden lookup. Failed attempts retain their
charges and full reserved cap; no refund or new call after terminal failure.
The selected response cap includes the entire body, not just parsed values;
streaming sentinel-byte overflow STOPs before a usable packet is published.
No safety cap can borrow from a different budget kind or create a new ledger.

## 7. One pre-T session and compatible freeze

Required lifecycle: `CREATED -> COLLECTING -> CLOSED -> SEALED -> FROZEN`;
any failure is terminal `STOPPED`. These are session states, not new cycle
or P03 enums. Collection-only staging facts cannot authorize downstream work.

1. Begin exactly once: capture collection identity/policies/provider binding,
   start and UTC minute cutoff, one ledger, one transport and A1 reuse registry.
2. Verify existing mainnet genesis/program LEVEL 1 before discovery admission.
   Preserve existing discovery/reserve/valuation request order and mappings.
3. Build the bounded raw mint manifest. Collect A1 and P03 facts before close;
   all physical requests and logical safety time dependencies are recorded.
4. Close collection permanently after all admitted stage receipts complete;
   no pending attempt may remain. Read the final injected monotone clock once
   as the candidate T and reject backwards time/deadline/cutoff rollover.
5. Seal the A1 registry and the sole whole-cycle ledger at that same T, then
   freeze it as `completed_at = reference_time = T`. Validate every stage's
   original facts at final T before publishing the frozen packet. A seal or
   final-validation failure is terminal, even if one component already sealed.
6. Release only immutable raw material and pure replay suppliers, with no
   opener, transport, mutable ledger or provider callable in the replay graph.
   All later discovery/P03 work is pure, with evaluation at T and explicit
   processing time >=T. Do not consult wall time, credentials or a live source.

Compatibility is explicit. Current `A1CollectionContext.validate` requires
one record per whole ledger attempt, and `A1CollectionPacket.replay_sources`
requires its A1 envelopes/valuations to cover every record. Simply appending
safety records to a v1 context fails that exact coverage check. Do not forge
a filtered v1 ledger, ignore records, or weaken the closed v1 validator.

The common packet uses this new contract version, retaining separate A1 and
safety stage material plus one global context. Its validator must establish
disjoint complete stage ownership: union of A1 and safety physical receipt
records equals every sealed ledger attempt exactly once. Logical reused time
references do not create physical rows. Every method/body/digest/clock/cap and
kind must match the corresponding attempt; no omitted or extra record passes.

Reuse the current A1 pure validation/mapping/source construction in a narrowly
shared stage helper if needed. Legacy standalone `collect_once` and v1 replay
continue to freeze their A1-only session and reject extra records exactly as
before. The new common entry point coordinates an unsealed A1 stage and P03
stage before one freeze; it never calls completed v1 `collect_once` and then
reopens it. No mapper, valuation registry policy or legacy arithmetic redesign.

## 8. Exact post-T discovery binding and P03 replay

No canonical P02 digest is invented pre-T. A thin in-memory discovery binding
wrapper delegates exactly once to the existing `BoundedDiscoveryOwner` using
the frozen packet's `OfflineA1DiscoverySource`, final T, captured freshness,
explicit processing time and evaluation ID. It validates and retains the
original returned snapshot, registers the immutable binding once and returns
that same object to its caller. It does not reconstruct P02 or rerun it for
safety. This handshake supports the existing cycle's single discovery call;
pre-running discovery and letting the cycle run it again is forbidden.

Before `evidence_once`, validate all of the following, not just matching mint:

- Exact bound packet/session digest, versions, T and selected policy/threshold.
- The supplied snapshot is the original registered canonical snapshot, and
  supplied candidate is its actual member; <=5 candidates and exact manifest
  membership, chain `solana`, case-sensitive mint, candidate ID and event ID.
- A1 mapper version `a1-cpmm-candle-source-v1`, batch version
  `bounded-paper-cycle-source-v1`, exact discovery scope/event/RPC lineage,
  source ID `a1-cpmm-candle-source-v1`, receipt ID and original receipt time.
- Exact predecessor snapshot tuple/membership, state version, state digest,
  materializer contract `p02-t06-v1` and actual evaluation ID, including None
  when applicable. The predecessor comes from that sole delegated owner.
- Each mint's complete immutable safety request/body/receipt/slot/time set,
  all in the same sealed session and matching the source-clock rules below.

Translate the validated bytes into the existing `SolanaMintSnapshot`/
`SolanaRpcObservation` semantics, preserving source ID `solana-json-rpc` and
source version `p01-oaf-01-solana-rpc-v1`; this is a pure view, not a call to
`SolanaJsonRpcSource.snapshot_mint`. Supply one exact copied `P02StateReference`
from the bound predecessor, including evaluation ID, to the shared P03 mapper.
Each returned evidence item's reference must equal all four predecessor
fields, token/chain must match, and canonical P03-T01 version is preserved.

Preserve existing authority PASS/FAIL mapping only from explicit mint/freeze
facts. Preserve existing sum of returned largest-account integer amounts
divided by positive raw supply, its `<= max_top_holder_fraction` comparison,
holder age from the older holder/supply observation, domain/reason codes and
provenance. Invalid supply or sum exceeding supply STOP. Do not change this
to largest-single-account concentration or add a new scoring/Risk rule.
No evidence for other safety domains or economic sellability is fabricated.

Canonical P03-T02 binds the exact evidence digest and evaluates at T;
P03-T03 consumes that exact result, with evaluator
`p03-t03-eligibility-derivation`, matching time, evidence references and
`p03-t02-v1`. Preserve the pair: eligibility alone carries no chain/token
identity. Per candidate, the source emits evidence once, and the caller's
existing P03 stage evaluates/derives once. Whole replay with identical frozen
inputs in a fresh replay instance must reproduce identical canonical digests.

Existing canonical evidence references do not enumerate all wire receipts
(notably supply and time lookup receipts). The separate immutable binding
therefore links packet digest, all raw dependency digests, predecessor identity
and each produced evidence digest/reference. Do not change canonical P03
provenance semantics to hide that limitation or claim durable audit retention.

## 9. Clock authority and STOP semantics

For every context read, retain its own finalized slot and original
`getBlockTime(slot)` value as source time. Require source time <= that read's
actual receipt <= T, plus a separately retained lookup start/receipt <=T.
Source slots must not precede the verified A1 discovery slot; a same-slot time
must agree with the A1 anchor. Different finalized slots retain their separate
times and are not described as an atomic single-slot snapshot. Contradictory
same-slot times or slot/time ordering against discovery STOP.

All source anchors must be aware UTC, non-future and fresh at final T under
the captured finite freshness policy and applicable A1 source-age policy.
Check holder and supply independently; a fresher read cannot conceal an older
stale dependency. Receipt, processing and evaluation clocks never substitute
for source time. Missing, partial, null or contradictory source/receipt/time
evidence STOPs; do not interpolate time or change T to obtain a favorable age.
Final UTC minute must equal the original planned OHLCV cutoff minute. Crossing
it invalidates the whole packet; no recollection, later cutoff or alternate T.

| Failure | Required terminal behavior / bounded reason category |
| --- | --- |
| Total/RPC/host/safety/byte budget exhausted; remaining deadline insufficient | STOP before next provider invocation; preserve charged attempts, no refund/retry. |
| Unsupported method/params/target/contract or request/response ID mismatch | STOP; reject the request before I/O when detectable pre-call. |
| HTTP/redirect/timeout/body-cap/RPC error, malformed JSON or partial raw data | Abort session; no successful frozen packet or partial safety publication. |
| Missing selected evidence, invalid mint/amount/decimals/account set | STOP; no UNKNOWN-to-PASS default, alternate source or candidate expansion. |
| Missing/stale/future/contradictory clocks or same-minute violation | STOP; preserve original clocks, never reopen ledger or choose another T. |
| Candidate/chain/token/source/predecessor/policy/digest/replay mismatch | Pure replay STOP; no canonical handoff, no recomputation of another P02. |
| Unexpected post-T I/O, second bind/emission, attempted freeze mutation/reopen | Reject before opener/provider access; terminal replay/source STOP. |
| Valid canonical P03 FAIL/UNKNOWN/INELIGIBLE | Preserve canonical result and existing candidate exclusion; never override eligibility or Risk. |

These are contract categories, not additions to the closed cycle outcome enum.
Use bounded safe source errors; the existing caller retains terminal
`OWNER_UNAVAILABLE` (with `SOURCE_UNAVAILABLE` reason) or `INVALID_INPUT`
as applicable. Never return a
success-shaped default, permissive partial tuple or fallback provider result.

## 10. Credential boundary

Credentials must not enter source, tests, docs, PR bodies/comments, logs or
persisted raw wire artifacts. This gate accesses no credential and performs
no operational request. Future credential configuration remains private to
an explicitly authorized transport adapter; no browser-supplied endpoint or
secret becomes source authority.

Exported lineage contains only sanitized provider identity, safe method/params,
request/response digests, caps, timestamps and lineage. Exclude API keys,
bearer tokens, credential-bearing endpoint query/path material and secret
headers. Never log raw endpoint/request repr, provider error text or a generic
dataclass dump. Existing A1 wire objects retain endpoint text in memory;
they are not approved durable audit objects. This contract must not persist
or expose those objects. Any later durable audit must define and verify its
own credential-free projection while retaining verifiable source linkage.
No durable collection audit or extension to RTI-03 storage is implemented here.

## 11. Future implementation acceptance plan

The following are specification cases only: no new acceptance tests or runtime
code have been implemented by this document. Future tests must use fake
injected transport and immutable raw byte fixtures, not synthetic PASS safety
standing in for source-backed replay. No market provider request or real key.

| Case | Required proof |
| --- | --- |
| Complete 1/5-mint raw replay | Three reads and <=3 time lookups per mint; exact A1 source facts, canonical evidence/evaluation/eligibility and deterministic replay digests. |
| Zero/six/oversized candidates | Empty scope has zero safety calls; sixth/extra manifest member and pre-truncation malformed scope rejected; no replacement expansion. |
| Exact predecessor | Spy one canonical P02 delegation; retain original snapshot; full OAF composer and second P02 call fail if reached. Reject same mint with different state version/digest/evaluation ID, source receipt or T. |
| Identity and source lineage | Alter chain, mint case, candidate/event ID, RPC target/ID/body, source version, receipt or dependency digest; every mismatch rejects before handoff. |
| Finite common accounting | 5 × 6 safety attempts maximum, all kind safety in the same ledger; exhausted/lower call/host/byte/time cap prevents opener call; failed charges remain. |
| Block-time dependencies | Same-slot reuse within a mint preserves original request/body/receipt lineage; no cross-mint/global cache or fabricated response; all physical lookups counted. |
| Freeze and v1 compatibility | One close/seal/T, no pending request; union of stage records equals ledger exactly; unknown/extra/missing stage record rejected; existing standalone v1 remains unchanged. |
| No-network replay | Remove transport/opener references and make HTTP/socket/DNS/default Solana/OAF source access fail; P02/P03 replay still succeeds, zero post-T I/O. |
| No reopening/mutation | Second collection, bind, emission or seal; ledger reopen and changed frozen raw/body/policy/T fail. Separate fresh replay instance preserves original packet. |
| Later discovery rejection | Final stale/invalid/rejected or absent precollected mint stops the complete handoff, no partial tuple, refund, second mint set or provider call. |
| Canonical safety rejection | Authority present or concentration beyond policy preserves FAIL/INELIGIBLE; missing domains are not fabricated; candidate cannot reach pool via bypass. |
| Clock failures | Missing/null/partial block time, source after receipt/T, stale holder or supply, contradictory slot/time, backwards receipt and UTC-minute rollover all STOP. |
| Malformed/partial data | Missing authority keys, wrong legacy program, malformed/zero supply, duplicate/extra/empty holder list, inconsistent decimals or sum > supply; no favorable default. |
| Transport/method denial | Unsupported method/commitment/params, duplicate/wrong ID, RPC/HTTP error, redirect, timeout and 256 KiB +1 body fail; no automatic retry. |
| Ownership / Risk | Exactly one P03-T02 and T03 call per admitted candidate, paired identity/provenance continuity; no duplicated P05/Risk/lifecycle/persistence logic or live authority. |
| Credential projection | Only clearly fake transport fixtures; no real secret, unsafe endpoint/header/error text in lineage/logs/dumps; no durable audit write. |

Future implementation must pass these focused cases and relevant existing A1,
Solana/P03/one-cycle regressions. Python/TypeScript CI for this docs-only PR
verifies the unchanged repository baseline, not these unimplemented cases.

## 12. Stop and authority preserved

After this specification PR merges and its new main Python/TypeScript CI
passes, STOP. A new explicit controller authorization is required before any
runtime/source implementation. No operational adapter, actual provider call,
diagnostic precollection/RTI-11 replay implementation, durable audit, selected
account quota/latency measurement, database/runtime qualification, provider
smoke/cycle, scheduler or continuous autonomous hunting is bundled here.

No wallet, signing, broadcast, DEX execution, settlement or live-money authority.
Real-money autonomous trading remains DISABLED; user funds remain a hard
security boundary. Risk Governor remains independent, mandatory and higher
authority than AI/Decision Engine, with no bypass path. LEVEL 2 binary/source
equivalence remains NOT VERIFIED. P03/P04 overall and historical progress
percentages remain unchanged. G2 BLOCKED / UNRESOLVED / NOT AUTHORIZED;
G3/G4/P09 NOT AUTHORIZED. MASTER_BLUEPRINT is unchanged.

AMT (Amati -> Modifikasi -> Terapkan) policy is unchanged: no external project
or tool integrated; Skills remain a potential concept, Code Graph/RAG a
potential read-only development aid, Prime Agent a design reference only,
Firecrawl/OmniRoute deferred. This specification is the final authorized
deliverable, not an implementation permission.
