# P01-OAF-01 — Trusted Solana P02/P03 Upstream Source Authority

**Status:** SPECIFICATION COMPLETE / READY FOR CONTROLLER REVIEW  
**Baseline:** `main` at `3717b97d3707d08504172cf5267380c84e9cda94` after PR #72.  
**Scope:** source-selection and owner-composition specification only. No runtime/provider call, OAF route, paper experiment, Hunter Room, wallet, execution, or live trading is authorized by this document.

## 1. Decision

The missing trusted upstream path for one future authenticated OAF prepare is specified as a **bounded Solana JSON-RPC snapshot path**, not browser-authored canonical P02/P03 objects and not the existing DexScreener/GoPlus surfaces.

The controller-selected candidate/token and exact pool remain explicit inputs. Candidate-listing UI data is only a selection hint and remains `NOT_ADMITTED`. Before RTI-11, the server must independently obtain finalized Solana observations for the selected token and pass them through the existing canonical P02 and P03 owners.

The transport endpoint is server configuration (`SOLANA_RPC_URL` or an equivalent existing configuration name selected at implementation). The domain authority is the Solana JSON-RPC response and its finalized ledger context, not a vendor brand. A commercial RPC transport may later be substituted without changing canonical owner semantics if it serves the same documented Solana RPC methods and preserves the required context.

## 2. Why this source is selected

The repository requires original source observation time for favorable P03 evidence; receipt/processing time cannot be substituted. The existing GoPlus adapter is EVM-only and its positive response fields do not establish a Solana source-observation timestamp. The existing DexScreener latest-token route deliberately labels candidates `NOT_ADMITTED` and therefore cannot create current P02 membership.

Standard Solana RPC responses provide ledger context slots for account/token reads. A slot can be anchored to a ledger-derived UTC observation time with `getBlockTime(slot)`. The selected bounded path therefore supplies source-anchored provenance without trusting browser timestamps or fabricating provider event time.

## 3. Bounded P02 current-token predecessor path

For one explicit authenticated prepare and one explicitly selected Solana mint:

1. Call `getAccountInfo(selected_mint, {encoding: "jsonParsed", commitment: "finalized"})` once.
2. Require a non-null account owned by the canonical SPL Token or Token-2022 program and parsed as a mint. Reject wrong identity/program/type.
3. Read the response `context.slot`; call `getBlockTime(slot)` once for that slot. A missing block time is a source-unavailable STOP; HTTP receipt time is not substituted.
4. Map this verified source observation into the existing P02-T03 adapter boundary and P02-T04 discovery observation for the exact selected token. Use the ledger slot as bounded source identity/provenance and the ledger block time as `observation_time`. The facade must not invent a provider event ID; any deterministic fallback identity must be produced under the existing P02 contract.
5. Pass the exact accepted result through P02-T05 and P02-T06 with explicit processing/reference/freshness context. Only an accepted, valid, current, published-as-current result may materialize membership.
6. Derive `P02T07PredecessorContext` from that exact P02-T06 state/version/digest. The facade may not construct membership directly from the selected mint.
7. Verify `predecessor.contains("solana", selected_mint)` before any RTI-11/CoinGecko credential or provider access.

This is **caller-directed verification**, not autonomous token discovery. It does not scan the chain, enumerate mints, poll, subscribe, retry, or choose a token.

## 4. Bounded P03 safety evidence path

P03 remains owner of evidence/evaluation/eligibility. The RPC adapter may only translate source observations into P03-T01 evidence; it cannot decide eligibility.

Minimum source-backed domains for this first bounded paper-preparation path are:

### 4.1 Mint/freeze authority

Use the exact finalized `getAccountInfo` mint snapshot already obtained for P02 when its parsed SPL mint fields contain the required mint/freeze authority facts. Preserve the response slot and its exact `getBlockTime` value as `observed_at`.

Map only facts explicitly present in the parsed source record into `SafetyDomain.MINT_FREEZE_AUTHORITY`. Missing/unsupported fields produce `UNKNOWN`; they are never converted to PASS.

### 4.2 Top-holder concentration

Call `getTokenLargestAccounts(selected_mint, {commitment: "finalized"})` at most once and `getTokenSupply(selected_mint, {commitment: "finalized"})` at most once. Each response must expose a context slot. Resolve each distinct slot through `getBlockTime` at most once per distinct slot.

The evidence mapper may calculate concentration only from exact integer token amounts and exact total supply represented by these source responses. Zero/invalid supply, unavailable block time, identity mismatch, malformed amount, inconsistent decimals, or unsupported source output produces `UNKNOWN`/STOP under existing P03 semantics; never a favorable default.

Map this bounded result only to `SafetyDomain.TOP_HOLDER_CONCENTRATION`.

### 4.3 Domains not established by this source set

This first path does **not** claim source authority for LP status/concentration, liquidity quality, metadata mutability, funding-wallet relationships, proxy-control patterns, suspicious mutable behavior, or tradability/sellability merely because another vendor may expose similarly named fields.

No browser value and no Birdeye/GoPlus/DexScreener field may silently fill those domains. A later source extension requires a separate bounded authority decision.

Existing P03-T02 and P03-T03 semantics remain unchanged. The exact `SafetyEvaluationResult` and exact paired `DerivedEligibilityOutput` are retained server-side and passed to RTI-11. The facade must not override `UNKNOWN`, conflict, stale, FAIL, or eligibility outcomes.

## 5. P02 reference continuity

Every P03 evidence item that carries a P02 reference must copy the exact P02 state version, state digest, contract version, and actual evaluation ID (when present) from the P02 state created in the same prepare invocation.

Candidate identity, P02 token identity, every P03 evidence token identity, P03 evaluation/eligibility identity, and the RTI-11 exact-pool target token mint must match exactly. Any mismatch stops before RTI-11.

## 6. Time, freshness, and commitment

All source reads in this path use `commitment="finalized"`.

Ledger `context.slot` plus `getBlockTime(slot)` is the source observation anchor. HTTP receipt time may be retained as transport observability but cannot replace `observed_at`, discovery observation time, or safety source time.

The caller supplies explicit processing/reference/evaluation times and freshness policy under existing contracts. Source observations newer than the explicit evaluation/reference boundary, stale under the supplied policy, or missing a ledger time fail closed.

If multiple source reads return different finalized slots, each fact retains its own source slot/time. The facade must not pretend they form an atomic single-slot snapshot. Cross-observation consistency is evaluated under existing P02/P03 rules and explicit reference time.

## 7. Cardinality and transport bounds

One future eligible prepare may perform only this bounded upstream sequence before RTI-11:

- one `getAccountInfo` for the selected mint;
- one `getTokenLargestAccounts` for the selected mint;
- one `getTokenSupply` for the selected mint;
- one `getBlockTime` for each distinct context slot returned by those calls, with duplicate slot lookups reused inside the invocation.

No automatic retry, fallback provider, polling, WebSocket, background refresh, scheduler, worker, token enumeration, recursive history lookup, or follow-up safety enrichment is permitted.

Implementation must set finite timeout and response-size limits, reject redirects where the HTTP client permits it, bound JSON depth/shape, keep RPC credentials/URL server-side, and return a bounded source-unavailable result on transport/authentication/rate-limit/malformed-response failure.

The implementation must not log RPC credentials or expose configured URLs containing credentials in API responses/provenance.

## 8. Relationship to RTI-11

Only after exact P02 predecessor membership and paired P03 outputs exist may OAF call RTI-11 once under the already approved PR #71 contract.

The Solana RPC path is upstream evidence sourcing. It does not replace the existing CoinGecko exact-pool OHLCV diagnostic and does not authorize extra CoinGecko calls.

Review, run, persist, and readback perform **zero** Solana RPC calls. Run continues to use the exact server-held CIP result; persist uses the exact lifecycle result and RTI-03 without rerunning upstream owners.

## 9. Access boundary

The PR #71 fail-closed single-controller bearer-authentication and explicit mutation-authorization decision remains unchanged. Authentication/authorization occurs before source lookup.

An opaque prepared-case handle is not a credential. Provider/RPC configuration is never client supplied for an operational route.

## 10. Implementation acceptance gate

A later P01-OAF-01 implementation may proceed only if focused deterministic tests prove:

- browser data cannot create canonical P02/P03 objects;
- exact token identity is preserved P02 → P03 → RTI-11;
- finalized RPC context slot and block time are retained as source provenance;
- receipt/processing time is never substituted for source observation time;
- P02-T03/T04/T05/T06 are used rather than bypassed;
- P03-T01/T02/T03 are used rather than bypassed;
- missing/malformed/unavailable source facts fail closed;
- cardinality is bounded exactly as above;
- no retry/poll/background source call exists;
- RTI-11 is not called when upstream validation fails;
- review/run/persist make no upstream RPC call;
- all live network behavior is mocked/faked in CI; no operational paper experiment is run by tests.

If existing owner contracts make this mapping impossible without changing their domain semantics, implementation must STOP and return to controller rather than modifying canonical owners merely to make OAF work.

## 11. Governance

This source authority is limited to **read-only Solana evidence for one explicit authenticated paper-case prepare**. It is not G2 realization, execution, settlement, wallet access, signing, broadcasting, or live trading.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**. G3/G4/P09 remain **NOT AUTHORIZED**.

No runtime/provider call is authorized by this specification checkpoint. P01-OAF-01 runtime implementation and any operational paper invocation remain separate authorization gates.
