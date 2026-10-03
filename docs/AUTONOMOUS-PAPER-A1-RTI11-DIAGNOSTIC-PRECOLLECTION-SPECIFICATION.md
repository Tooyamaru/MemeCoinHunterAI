# A1 RTI-11 diagnostic precollection and pure replay

Status: FORMAL SPECIFICATION COMPLETE; no implementation in this specification PR.
Contract: `a1-rti11-diagnostic-precollection-replay-v1`.
Controller: attached micro-batch instruction of 2026-10-03 WIB authorizes this
specification, then its offline/injected implementation only after specification
merge and exact post-merge main CI PASS. Stop after implementation merge/main CI.

## 1. Baseline, order and authority

Verified starting main: `3ffde8757bc7fb6883bf108f4c7f3e2f1c2cbb78`.
PR #138/#139 closed; no open competing PR. Main CI #558 / run `37040167787`
SUCCESS, Python 3.13 tests and TypeScript checks/builds PASS. A1/P03 offline
owners and prior v1 contracts remain closed and unchanged in authority.

Required order:

1. Raw A1 discovery/reserves/valuation, raw P03 safety and raw diagnostic facts
   enter the SAME finite pre-T session and whole-cycle ledger.
2. Close permanently, seal with no pending request, freeze one immutable T.
3. Pure A1 replay calls canonical P02 discovery once and retains its actual
   snapshot/predecessor; pure P03 mapping emits evidence for that snapshot.
4. Existing caller evaluates/derives P03 once per candidate; only eligible
   candidates reach the existing canonical pool selection once each.
5. Bind the actual selected pool, predecessor and P03 pair to the original
   RTI-11 request; pure diagnostic replay delegates to existing RTI-11/LME-03,
   candle/PRICE_DIRECTION_1M and P04-to-P05 owners.

No provider request, clock read, credential lookup or provider-capable object
exists in the replay graph. `freeze T -> provider diagnostic` is forbidden.
Risk remains independent, mandatory and higher authority; eligibility and
diagnostic evidence do not grant capital or execution authority.

## 2. Unknown selected pool before T: bounded raw coverage

Canonical pool selection belongs AFTER P03 and T. Precollection must not run
P02, P03, canonical pool selection, scoring or prospective liquidity ranking.
Instead, enumerate the exact candidate-mint/pool incidences from the existing
bounded A1 raw reserve snapshots for the lexical at-most-five raw mints.
For each incidence request the candidate as base, the other reserve as quote.
The entire raw target manifest is deterministic (mint, pool lexical order),
includes original event ID and reserve facts/lineage, and covers every possible
post-T canonical target without claiming a canonical candidate before P02.

Use the existing A1 physical candle receipt only if section 4 equivalence
passes. Otherwise plan one separate `diagnostic` GET for that exact incidence.
No raw target is omitted because it might later be ineligible or lower ranked.
Determine the complete plan before issuing any separate diagnostic request.
If independent requests exceed the caller's cap (at most five), STOP the
collection: no packet, truncation, replacement, provisional ranking, budget
borrowing or post-T lookup. All earlier physical attempts retain their charges.

This conservative coverage may STOP a valid large source universe: five
selected candidates does NOT imply at most five speculative diagnostic targets.
For example, reversed reserve orientations or different timeout/body caps can
require more than five independent requests. No full-cardinality availability
promise or budget increase is made. A one-pool/two-mint universe with matching
limits requires one exact A1 reuse and one independent reversed-target request,
so the bounded contract is feasible within current ceilings. A provider that
cannot supply the required response composition STOPs; synthetic acceptance
does not qualify an operational endpoint or promise reverse-orientation support.

## 3. Request, response and clock identity

Capture explicit diagnostic timeout >0 and <=30 seconds, body cap >0 and
<=1 MiB, common positive finite freshness, existing A1 source-age/skew policy,
collection ID, sanitized provider/endpoint identity and all version pins.
No favorable policy default or threshold is introduced.

| Bound dimension | Exact required value/material |
| --- | --- |
| Endpoint/semantic kind | CoinGecko Demo pool OHLCV, HTTPS GET, `ENDPOINT_VERSION`, canonical adapter and PRICE_DIRECTION_1M policy versions; USD price, never a reserve ratio. |
| Asset/target | solana, exact case-sensitive token mint, pool, ordered base/quote reserve mints, raw reserve slot/state/decoder lineage and source event. |
| Query/window | ordered aggregate=1, limit=3, currency=usd, exact token, include_empty_intervals=false, before_timestamp=C; interval 60s; three contiguous closed candles ending at C-60. |
| Temporal reference | start's UTC minute C captured pre-T; all receipts completed in that minute; final request reference T bound only after freeze, with identical URL/query/C. No provisional canonical T or cross-minute rebasing. |
| Limits/policies | exact timeout and body cap, common freshness and A1 source-age/skew opt-ins/pins; same collection only. |
| Physical lineage | ledger attempt ID, record ID/kind, exact immutable wire request/digest, status, original bytes/SHA-256/length, response resource ID, returned reserve metadata, all source candle timestamps, original start/receipt times. |
| Logical lineage | raw incidence and dependency/reuse link to the original physical record; selected candidate, exact pool/P02/P03 identities and final RTI request digest bound post-T in a separate immutable record. |

The final-reference materialization is permitted only because collection start
and T share C and the exact final request regenerates the same wire URL/query.
Retain the pre-T wire/key AND final T request; never replace original receipts
or source times. Same URL, body, pool address or opaque digest alone is
insufficient. Revalidate underlying immutable material, including strict parser
identity and all three timestamps, before any canonical diagnostic delegation.

Source times are candle opening times and closed ends, never receipt time.
Require every candle open <= closed end <= original receipt <= T, oldest candle
fresh under the explicit common policy, latest open=C-60, and request start <=
receipt with elapsed <= selected timeout. Missing/stale/future/unaligned time,
wrong/incomplete window, contradictory source/receipt order, T mismatch,
non-monotone clock or minute rollover is terminal STOP. Existing reserve/USD
source-skew validation remains unchanged.

## 4. Exact A1 candle reuse

Reuse RAW candle evidence, never the calculated liquidity or latest-price
projection. Compare full `A1ValuationRequestKey` semantics against the proposed
diagnostic key: collection, endpoint/version, network, token, pool, ordered
base/quote mints, query/window/reference minute, timeout and cap. The common
context supplies the SAME captured policy/freshness/version pins to both uses.
Reparse original bytes for exact returned composition and complete three-candle
coverage, then revalidate at final T under BOTH source and diagnostic clocks.

A1 valuation can consume only the latest close, whereas the diagnostic needs
all three candles; passing A1 valuation alone is not diagnostic equivalence.
No metadata rewriting, reserve-order swapping, reciprocal-price construction,
timeout/cap relaxation or body replacement can turn non-equivalence into reuse.
Any relevant difference requires separate pre-T collection under section 2 or
STOP. Identical raw bodies obtained from different requests remain distinct
physical attempts and lineage. Logical reuse adds a dependency link, no
physical attempt, quota claim or refund. No global/cross-collection cache.

## 5. Shared ledger, packet and freeze compatibility

| Scope | Maximum RPC | Maximum CoinGecko GET | Reserved body bytes |
| --- | ---: | ---: | ---: |
| Existing A1 | 16 | 64 | 73,490,432 |
| Existing P03 | 30 | 0 | 7,864,320 |
| Independent diagnostic precollection | 0 | 5 | 5,242,880 |
| Unchanged whole cycle | 46 | 69 | 86,597,632 |

At most 115 physical HTTP calls, same aggregate <=180-second deadline and
same-minute cutoff, no retries/redirects/provider switching. Reserve full
chosen body cap, kind, host and call counters in the EXISTING ledger before
each physical call; refusals invoke no opener. Failed attempts stay charged.
Lower caller-selected caps remain binding. The existing ledger already admits
`diagnostic`; no new budget kind, independent ledger or ceiling is needed.

New diagnostic common context/packet uses this contract version. Preserve
standalone A1 v1 and common P03 v1 public validators: they still reject extra
diagnostic rows. Narrow pure internal stage helpers may be shared; never forge
filtered ledgers or weaken legacy coverage. One full immutable context proves
global attempt/record equality and reproduces whole-ledger accounting. A1,
P03 and independent-diagnostic physical stages form a disjoint complete union;
reuse links reference A1 receipts and do not own extra physical rows. Every
method/params/host/body/digest/length/clock/timeout/cap/kind must match. No extra,
missing, duplicate, dangling or unaccounted diagnostic record passes.

The service remains CREATED -> COLLECTING -> CLOSED -> SEALED -> FROZEN;
any error is terminal STOPPED. Close only after all admitted A1/P03/diagnostic
receipts complete and no attempt remains pending. One final injected clock
read selects T, registry/ledger seal at that T, then revalidate every source
at T before publishing. No ledger reopen, extension of an old frozen packet,
second collection, changed provider or final-T mutation is possible.

## 6. Exact post-T canonical bindings

Extend the existing exact-discovery wrapper through the new packet's pure
validation; retain the original returned `DiscoverySnapshot`, candidate and
`P02T07PredecessorContext` objects, full predecessor including evaluation ID,
source/receipt, manifest, packet digest, T and discovery arguments. Equal
reconstructed snapshots/candidates/predecessors are rejected.

An evidence-only P03 wrapper retains each actual emitted collection. The
existing caller invokes canonical evaluation/eligibility exactly once and
registers those original objects for the diagnostic handoff. Validate their
canonical contracts, token, T, input evidence digest, references and discovery
lineage. Do not recompute P03 or reconstruct equal evaluation/eligibility.

A thin pool binding delegates ONCE to `BoundedPoolCandidateOwner.select` per
eligible candidate, retains its actual full canonical observations and selected
object, and binds source/version/reference, exact reserve orientation,
liquidity USD metric, selected evidence/digest, raw reserve/valuation lineage
and selection policy (highest exact liquidity then lexical pool address).
It neither duplicates ranking nor calls pool source/selection a second time.

An explicit thin market replay wrapper registers the caller's actual
`P01Rti11CompositionRequest` using those exact objects and its original target.
Require candidate, selected target reference ID/digest/version, ordered mints,
pool source, metric/evidence, exact P02 predecessor and exact registered P03
pair, T/freshness/limits, evaluation ID/processing/evaluation clocks to agree.
The existing cycle may have one narrow registration hook after its canonical
P03/pool owners return; no automatic provider or paper action is added.

Compose accepts only that original once-registered request. The injected pure
diagnostic callback validates its canonical `OhlcvRequest` equals the frozen
fact's FINAL-T request, and predecessor is the bound original. It uses only
the original response bytes/receipts and delegates to existing
`derive_price_direction`, RTI-11/LME-03 and P04/P05 composition. No duplicate
parser/policy/scoring algorithm. Keep an immutable replay-lineage record bound
to the canonical request/result digests and physical/reuse dependency. The
returned result retains the exact caller request. New binding errors or
diagnostic non-production STOP the new replay graph; no permissive fallback.

## 7. Failures and security

Terminal STOP: wrong chain/token/candidate/pool/reserves, predecessor or P03
object mismatch, unregistered/equal-copy request, target/selection evidence
mismatch, request/body/digest/receipt mismatch, invalid reuse, policy/version
mismatch, malformed/duplicate-key/non-finite/incomplete response, wrong
interval/closed minute/window, stale/future/missing source clock, contradictory
receipt, cutoff/T mismatch, timeout/body overflow/budget exhaustion, ledger
coverage error, replay mismatch, repeated owner call or post-T I/O attempt.
No packet/partial success on failed collection; no downstream paper authority
on failed replay. Preserve existing empty discovery and ineligible outcomes.

Only sanitized origin-only RPC identity and fixed public CoinGecko request
semantics enter packets/digests/records. Credential-bearing path/query/userinfo
or header material is excluded/refused by the offline contract. No credential
in bodies, logs, docs, tests, lineage or PR text. Raw success bodies are private
bytes; no credential API, environment lookup or operational adapter is added.

## 8. Offline implementation acceptance and stop

Future focused tests must cover common A1+P03+diagnostic session/one final T;
exact A1 reuse and each non-equivalence dimension; separate pre-T collection;
large target coverage STOP without ranking/truncation/budget increase; exact
pool source/metric/evidence/reserve and original P02/P03 object binding;
original request equality and reconstruction rejection; source/receipt clock
separation, stale/future/wrong-window/interval/rollover rejection; immutable
packets and recomputed-digest tampering; all physical attempts charged,
failed charges, exact global/stage/reuse coverage, no ledger reopening/retry;
zero network/clock/environment after T; canonical owner call counts;
autonomous one-cycle canonical paper persist/readback and independent Risk
veto; existing A1/P03/P02/RTI-11/LME/P04/P05/Risk/paper regressions intact.

Implementation files may add `core/data/a1_rti11_collection.py`, focused unit
and integration tests, narrow internal stage helpers in existing A1/P03
collection modules, and the explicit canonical cycle binding hook. State and
changelog record actual evidence. No dependency/workflow/blueprint redesign.

Specification PR contains only this document, PROJECT_STATE and CHANGELOG.
Require exact-head Python/TypeScript CI, bounded audit, merge and exact main
CI PASS BEFORE a fresh implementation branch. Implementation then requires
focused tests, relevant regressions, PR, exact-head CI, audit, merge and exact
main CI PASS; STOP without another closure/review/successor PR.

No operational endpoint qualification, real provider execution, quota/latency
measurement, durable collection audit, runtime/database qualification,
provider-backed smoke, scheduler, continuous hunting, wallet/signing/broadcast,
DEX execution/settlement/live money, external integration or LEVEL 2 claim.
P03/P04 overall and historical progress unchanged; MASTER_BLUEPRINT unchanged.
G2 BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 NOT AUTHORIZED.
