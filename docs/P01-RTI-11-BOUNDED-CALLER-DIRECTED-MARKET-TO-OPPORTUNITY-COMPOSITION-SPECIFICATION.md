# P01-RTI-11 — Bounded Caller-Directed Market-to-Opportunity Composition

**Status:** COMPLETE / CLOSED / CI PASS

**Gate type:** bounded application integration gate

**Verified baseline:** `ad1c081770e01cbec2aca96954abf24444feaf3e`

**Reviewed on:** 2026-09-23

## 1. Repository verification

The verified branch is `docs/p01-rti-11-controller-review`. Its base and
`origin/main` are both `ad1c081770e01cbec2aca96954abf24444feaf3e`; the only
pending changes are governance documentation for this review.

Repository evidence confirms:

- P01-RTI-10 is COMPLETE / CLOSED / CI PASS;
- P04-LME-01 owns the bounded CoinGecko Demo Onchain OHLCV mapping and
  `price-direction-v1` policy;
- P04-LME-02 owns one bounded credential-backed HTTP diagnostic attempt;
- P04-LME-03 owns caller-directed exact-target validation and at-most-once
  delegation to LME-02;
- `produce_canonical_p04_to_p05` is the existing canonical producer through
  P05-T05 and returns `CanonicalP04ToP05Composition`; and
- RTI-03 through RTI-10 remain closed, G2 remains BLOCKED / UNRESOLVED / NOT
  AUTHORIZED, and G3/G4/P09 remain NOT AUTHORIZED.

### Repository-wins reconciliation

The proposed input of only `DerivedEligibilityOutput` is insufficient to prove
token identity: that type contains status, evaluator, evaluation time,
references, version, and reasons, but no `chain_id` or `token_identity`.
`SafetyEvaluationResult` owns those identities. Therefore RTI-11 requires an
canonical paired P03 handoff: the exact P03-T02 `SafetyEvaluationResult`
and the already-derived P03-T03 `DerivedEligibilityOutput`. P03-T02 remains a
non-authoritative evaluation and P03-T03 remains analytical eligibility, not
trading authorization. RTI-11 validates
their structural linkage but never re-runs safety evaluation or eligibility
derivation. This is a specification correction, not a new P03 authority.

No other controlling assumption conflicts with the repository.

## 2. Purpose and terminal boundary

RTI-11 specifies one HTTP-independent application call that:

1. receives an immutable current P02 predecessor, an exact caller-owned pool
   target, the paired authoritative P03 handoff, and explicit time/freshness
   inputs;
2. validates identity and version linkage before any delegated side effect;
3. delegates exactly once to `run_controlled_ohlcv_diagnostic`;
4. continues only when the exact nested success predicate is satisfied;
5. passes the canonical observations and exact `PRICE_DIRECTION_1M` evidence
   to `produce_canonical_p04_to_p05`; and
6. stops at the existing P05-T05 `CanonicalP04ToP05Composition`.

It creates no market, signal, safety, opportunity, economic, execution, or
persistence authority.

## 3. Authoritative dependencies

| Dependency | Authoritative repository owner | Required use |
| --- | --- | --- |
| Current token membership | `P02T07PredecessorContext` over P02-T06 | Exact input; no refresh or discovery |
| P03 identity/evidence evaluation | `SafetyEvaluationResult` / P03-T02 | Identity and provenance half of paired handoff |
| P03 eligibility | `derive_token_eligibility` / P03-T03 | Caller supplies its existing output; RTI-11 does not invoke it |
| Exact pool target | `ExactPoolDiagnosticTarget` / P04-LME-03 | Caller-owned exact value; no selection |
| Source mapping | P04-LME-01 | Nested output only |
| One-shot transport | P04-LME-02 | Reachable only through LME-03, once |
| Controlled orchestration | `run_controlled_ohlcv_diagnostic` / P04-LME-03 | Sole upstream delegate |
| Signal policy | `price-direction-v1` | Exact binding, never “latest” |
| Canonical P04/P05 production | `produce_canonical_p04_to_p05` | Sole downstream delegate |
| Terminal output | `CanonicalP04ToP05Composition` / P05-T05 | Preserved without rewriting |

## 4. Single authorized application caller

The future module's single public application service entry point is the only
authorized RTI-11 caller boundary. It may be invoked directly by an explicit
in-process controller/test that supplies every request field. RTI-11 grants no
authority to an API route, CLI, dashboard, worker, scheduler, queue, startup
hook, provider poller, or ambient/global singleton.

No production caller wiring is authorized by this specification. Connecting
any concrete runtime caller requires a separate gate. Dependency injection for
focused tests is not alternate caller authority.

## 5. Exact input contract

The future immutable `P01Rti11CompositionRequest` shall contain:

| Field | Exact type/meaning | Rule |
| --- | --- | --- |
| `candidate_id` | non-empty canonical caller-owned P05 candidate identity | Explicit; never generated from symbol/time |
| `predecessor` | `P02T07PredecessorContext` | Exact current P02 predecessor |
| `target` | `ExactPoolDiagnosticTarget` | Exact caller-selected pool; no lookup |
| `safety_evaluation` | `SafetyEvaluationResult` | Canonical P03-T02 identity/provenance; not trading authority |
| `eligibility` | `DerivedEligibilityOutput` | Already-derived P03-T03 result |
| `reference_time` | timezone-aware `datetime` | Caller-owned point-in-time reference |
| `timeout` | positive bounded `timedelta` | Passed unchanged to LME-03 |
| `max_response_bytes` | integer accepted by `OhlcvRequest` | Passed unchanged to LME-03 |
| `freshness_policy` | explicit `FreshnessPolicy` with `stale_after` | Passed unchanged to both delegates |
| `processing_time` | timezone-aware `datetime` | Explicit feature-processing fact; no default clock |
| `evaluated_at` | timezone-aware `datetime` | Explicit P05 evaluation fact; no default substitution |
| `evaluation_id` | optional non-empty string | Passed unchanged to feature production |
| `analytical_context` | absent or bounded canonical mapping | No secrets, commands, or economic assertions |

The environment and clock accepted by existing LME seams are injected into the
future service constructor/test seam, not stored in the request, result,
canonical payload, or public configuration. They convey no caller authority.

Malformed types, missing explicit fields, naive timestamps, unsupported
versions, identity mismatch, invalid bounds, and non-canonical analytical
context are application validation failures raised before LME-03 is called.

## 6. Identity-linkage rules

All comparisons use exact canonical values; there is no case folding, symbol
fallback, name lookup, alias, discovery, or secondary identity.

| Link | Required invariant | Failure |
| --- | --- | --- |
| Target ↔ predecessor | `predecessor.contains(target.chain_id, target.token_mint)` | Bounded `TOKEN_NOT_CURRENT` is owned by LME-03; RTI-11 must not pre-empt or rewrite it |
| Target composition | `token_mint` equals exactly one of `base_mint`/`quote_mint`; base and quote differ | Validation failure |
| P03 evaluation ↔ target | exact `chain_id` and `token_identity == target.token_mint` | Validation failure |
| P03 pair | eligibility evaluator is `p03-t03-eligibility-derivation`; its `contract_version`, `evaluated_at`, and `evidence_references` exactly equal the supplied evaluation values | Validation failure |
| Eligibility time | `eligibility.evaluated_at <= reference_time` | Validation failure |
| LME request ↔ target | request chain/token/pool/base/quote exactly equal target | Bounded diagnostic non-production if nested output is inconsistent |
| Observations ↔ request | every canonical observation has exact request chain/token/pool market subject and approved provider provenance | Diagnostic non-production |
| Signal ↔ observations | exact same chain/token/source; signal `observed_at` equals latest accepted observation time | Diagnostic non-production |
| P05 producer call | `candidate_id`, chain, token, reference, eligibility, observations, freshness, and explicit times are passed unchanged | Implementation defect; focused test must fail |

RTI-11 does not recompute eligibility to confirm status/reasons. P03-T03 owns
that derivation; the paired handoff and exact evaluator/link fields identify
the authoritative relationship without creating a second evaluator.

## 7. Nested diagnostic success predicate

Success is true only when all conditions hold:

1. outer outcome is `ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED`;
2. outer target and request are present and satisfy the identity rules above;
3. nested `PriceDirectionResult.market.outcome` is exactly
   `OhlcvOutcome.PRODUCED`;
4. nested market provenance is present and binds provider
   `coingecko-onchain-demo`, request, response digest, adapter, and endpoint;
5. the market contains exactly three canonical
   `AcceptedMarketIntelligenceObservation` values, strictly ordered by their
   existing canonical order and all identity-linked to the request;
6. `signal_evidence` is a `SignalEvidenceCollection` containing exactly one
   evidence item;
7. that item has signal type `PRICE_DIRECTION_1M`, source
   `coingecko-onchain-demo`, provenance method/policy `price-direction-v1`,
   the same chain/token, and the latest observation time; and
8. the evidence provenance observation IDs/fingerprints/upstream state digests
   exactly correspond to the three observations.

`DIAGNOSTIC_COMPLETED` alone is never success. Missing or partial observations,
missing signal, wrong policy/type/source, or inconsistent provenance is
`DIAGNOSTIC_NOT_PRODUCED`; the canonical producer is not invoked.

## 8. Time semantics

| Time | Owner/source | Meaning | Required relation/prohibited substitution |
| --- | --- | --- | --- |
| Observation time | Provider fact admitted by P04-LME-01/P02 | One-minute candle interval time | Must remain on each observation; never replace with receipt/evaluation/processing time |
| Cutoff time | Derived by `OhlcvRequest` from caller `reference_time` | UTC floor-to-minute `before_timestamp` | Derive only through existing request; never use current wall clock |
| Receipt time | P04-LME-02 transport clock | Response fully received | Preserve in source provenance; never use as observation or reference time |
| Diagnostic evaluation time | P04-LME-02 injected clock | P02 freshness/admission evaluation | Must be explicit/injected; never substitute processing time |
| Reference time | Caller | Point-in-time request and P04/P05 feature reference | Passed unchanged to LME-03 and canonical producer |
| Processing time | Caller | Explicit P04 feature-processing fact | Passed unchanged; never default to ambient now or receipt time |
| P05 evaluated-at | Caller | P05-T03–T05 evaluation timestamp | Passed unchanged; never default silently to reference time |
| Eligibility evaluated-at | P03-T02/T03 | Time safety evaluation was derived | Must equal paired evaluation timestamp and not exceed reference time |
| Freshness policy | Caller, under existing `FreshnessPolicy` contract | Bounds admission relative to the existing evaluation/reference semantics | Same object/value passed to both existing owners; RTI-11 adds no policy |

Existing lower-level temporal validators remain authoritative. RTI-11 may
check cross-boundary equality/order invariants but must not reinterpret age or
freshness. Repeated calls with identical immutable inputs, injected diagnostic
result, and delegate behavior must yield equivalent results.

## 9. Output and failure semantics

The future immutable `P01Rti11CompositionResult` shall have contract version
`p01-rti-11-v1`, one outcome, canonical reason codes, optional preserved
controlled diagnostic, optional exact composition, and a canonical
`result_digest`. Exactly one of diagnostic/composition is present as allowed
below. It adds no economic label.

| Condition | Outcome/handling | Payload rule |
| --- | --- | --- |
| Full predicate and canonical producer succeeds | `COMPOSED` | Exact `ControlledDiagnosticResult` and exact `CanonicalP04ToP05Composition` preserved |
| LME-03 returns `TOKEN_NOT_CURRENT` | `TOKEN_NOT_CURRENT` | Preserve exact controlled result; no producer call |
| LME-03 returns `INVALID_INPUT`, or completed nested result is not exact success | `DIAGNOSTIC_NOT_PRODUCED` | Preserve bounded outer/nested outcome and reason codes; no producer call |
| Valid request but delegate raises or returns invalid type; canonical producer rejects/raises unexpectedly | `COMPOSITION_UNAVAILABLE` | Safe canonical reason only; no raw exception text/type/traceback |
| Malformed request, identity/config mismatch, unsupported version | raise application validation failure (`ValueError`) | No bounded result and no delegated call |

The only result outcomes are `COMPOSED`, `TOKEN_NOT_CURRENT`,
`DIAGNOSTIC_NOT_PRODUCED`, and `COMPOSITION_UNAVAILABLE`. There is no
`INVALID_INPUT` RTI-11 outcome because malformed caller input must remain
distinct from a valid request with a bounded upstream failure. There are no
WIN/LOSS, BUY/SELL, PROFIT/ROI, realized, settled, or trading outcomes.

Canonical reason codes are finite constants. Preserved upstream reason codes
remain nested; raw provider bodies and raw exceptions never enter the result.

## 10. Canonicalization and result digest

The wrapper canonical representation shall include only:

- `contract_version`;
- `outcome`;
- sorted/deduplicated RTI-11 reason codes;
- request identity material (`candidate_id`, predecessor state
  version/digest/contract/evaluation ID, exact target reference and identity,
  P03 evaluation digest/reference material, explicit times, freshness material,
  limits, and optional evaluation ID/context);
- the preserved controlled-result canonical material or a stable digest of
  that material; and
- on `COMPOSED`, the existing composition `digest` and its upstream
  provenance digests.

`result_digest` is lowercase SHA-256 of UTF-8 canonical JSON using sorted keys,
compact separators, UTC-normalized timestamps, stable tuple order, exact
decimal/string representations, and no ambient data. It excludes secrets,
environment, callables, exception details, object addresses, wall clock, and
unordered iteration. Identical canonical inputs/results produce the same
digest. A future implementation must reuse existing canonical forms where
available and must not mutate nested domain objects to obtain it.

## 11. Policy and contract-version binding

| Surface | Exact supported binding | Mismatch behavior |
| --- | --- | --- |
| RTI-11 | `p01-rti-11-v1` | Validation failure |
| P02 predecessor | `p02-t06-v1` materializer contract carried by predecessor | Validation failure; no silent version coercion |
| P02 observations | `p02-t07-v1`, `p02-t08-v1`, `p02-t09-v1`, `p02-market-intelligence-v1` as produced by LME-01 | Diagnostic non-production |
| P03 evidence | `p03-t01-v1` provenance through evaluation | Preserve; no recomputation |
| P03 evaluation/eligibility | `p03-t02-v1`; evaluator `p03-t03-eligibility-derivation` | Validation failure |
| LME source | adapter `p04-lme-01-v1`, current bounded endpoint contract, provider `coingecko-onchain-demo` | Diagnostic non-production |
| Signal policy | exactly `price-direction-v1`; signal `PRICE_DIRECTION_1M` | Diagnostic non-production |
| P04 chain | `p04-t01-v1` through `p04-t06-v1`, plus `p04-t09-v1` and `p04-t10-v1` | Existing producer fails closed; map unexpected rejection to unavailable |
| P05 chain | `p05-t01-v1` through `p05-t05-v1` | Existing producer fails closed; map unexpected rejection to unavailable |

RTI-11 never selects “latest,” upgrades, downgrades, aliases, or translates a
version. Adding a version requires a future specification decision.

## 12. Provenance propagation

| Provenance | Input owner | Required downstream preservation |
| --- | --- | --- |
| P02 predecessor | state version, digest, materializer version, evaluation ID | Controlled diagnostic request/admission and wrapper digest |
| Target selection | exact pool identities, reference ID/digest/version | Controlled result and wrapper digest |
| P03 safety | evaluation input digest, references, provenance, time, version | Paired handoff validation; eligibility passed unchanged |
| Provider/source | provider, adapter, endpoint, request, HTTP status, request ID, response digest, raw timestamps | Nested market provenance unchanged; no body/secret |
| Observations | IDs, fingerprints, source, chain/token/pool, times, upstream state references/contracts | Passed unchanged and ordered to canonical producer |
| Signal | evidence reference, source, policy, observation IDs/fingerprints/state digests | Passed unchanged as exact collection |
| P04/P05 | snapshots, upstream representation digests, contract/evaluator versions | Exact `CanonicalP04ToP05Composition` preserved |
| RTI-11 | contract, request identity, outcome/reasons, nested/final digests | Deterministic wrapper result digest only |

Absent provenance causes validation failure or diagnostic non-production as
specified; RTI-11 must never fabricate, infer, repair, backfill, or overwrite
provenance.

## 13. Authority and ownership matrix

| Concern | Owner | RTI-11 permission |
| --- | --- | --- |
| Application invocation/result wrapper | RTI-11 service | Sole new authority |
| Candidate/predecessor membership | P02 | Validate/pass only |
| Safety evaluation and eligibility | P03-T02/T03 | Validate paired handoff/pass only |
| Pool choice | Explicit caller | Accept exact target; never choose |
| Source, HTTP attempt, mapping | P04-LME-01/02 | Reach only through one LME-03 call |
| Controlled orchestration | P04-LME-03 | Delegate exactly once |
| Signal policy | `price-direction-v1` | Verify/pass only |
| P04/P05 canonical computation | Existing canonical producer/P04/P05 owners | Delegate once/pass result |
| Record/history/context | P05-T06/T07/T08 | Prohibited |
| Decision/paper/economics | P06/RTI/G2 authorities | Prohibited/unreachable |
| Execution/live trading | No RTI-11 owner | Prohibited |

## 14. Dependency/readiness matrix

| Dependency | Ready? | Residual condition fixed by this specification |
| --- | --- | --- |
| P02 predecessor | Yes | Exact immutable input and identity linkage |
| P03 eligibility | Yes, with paired handoff | Evaluation supplies identity missing from eligibility output |
| Exact target | Yes | Caller owns exact choice and reference |
| LME-01–03 | Yes within bounded scope | Exactly one call and exact nested success predicate |
| Canonical P04/P05 producer | Yes | Stop at P05-T05 |
| Runtime caller | No, intentionally | No caller wiring authorized |
| Persistence/publication | Not required/unauthorized | Must remain unreachable |
| Economic/execution authority | Not required/unauthorized | Must remain unreachable |

## 15. No-side-effect and unreachability guarantees

RTI-11 itself performs no I/O. Its only potentially effectful delegation is
one call to P04-LME-03, which may cause the already-bounded single LME-02 HTTP
attempt. The canonical producer is pure. No mutation, write, retry, repair, or
publication is permitted.

| Forbidden surface | Proof obligation |
| --- | --- |
| Retry/polling/provider continuous runtime | LME-03 mock called at most once; no loop/backoff/runtime imports |
| Persistence/repair/publication | No repository/session/model/cache/publisher imports or calls |
| P05-T06/T07/T08 | No record/history/context imports; output type ends at T05 |
| P06 | No decision modules/imports/calls |
| RTI paper lifecycle | No RTI service imports/calls |
| Worker/scheduler/queue | No framework imports, registrations, jobs, or startup hooks |
| HTTP/API/dashboard | No route/schema/frontend files or imports |
| Economic realization/G2 | No realized/settled outcome or economic source |
| Wallet/execution/live trading/G3/G4/P09 | No signing, transaction, broadcast, execution, or downstream imports |

Static import assertions plus call-spy tests must prove these paths are absent.
Repository-wide relevant regressions must confirm existing owners are unchanged.

## 16. Focused test matrix

| Area | Required focused assertions |
| --- | --- |
| Valid composition | One exact LME-03 call; one exact canonical-producer call; `COMPOSED`; exact nested objects and digest |
| Caller ownership | No ambient/global input; all facts supplied explicitly |
| P03 pair | Correct pair accepted; wrong token/chain/evaluator/time/references/version rejected before delegation; no P03 evaluator called |
| Identity | Candidate, predecessor, target, request, observation, signal, and P05 call linkage; mismatch fails closed |
| Nested success | Every success-predicate clause; completed-but-non-produced/partial/wrong signal prevents producer call |
| Outcomes | Exact four-state vocabulary; no economic/trading words or semantics |
| Validation distinction | Malformed input raises validation failure; valid upstream failures return bounded result |
| Bounded failures | Token-not-current, every representative OHLCV non-produced outcome, invalid delegate type, unexpected exceptions, and producer rejection |
| Safe failures | No raw exception/provider body/credential in result or digest |
| Time | Observation/cutoff/receipt/evaluation/reference/processing/P05/eligibility times remain distinct and correctly propagated |
| Versions | Exact table bindings; every unsupported/mismatched representative fails closed; no latest fallback |
| Provenance | Target/P02/P03/provider/observation/signal/P04/P05 lineage preserved; absent/mismatch never fabricated |
| Ordering | Three canonical observations passed unchanged in existing order |
| Determinism | Repeated identical injected calls yield equivalent output and `result_digest`; no wall-clock/random/order dependency |
| No side effects | No mutation; at most one diagnostic call; no retry or second provider call |
| Unreachability | No DB/publication/T06–T08/P06/RTI/worker/scheduler/queue/API/dashboard/wallet/execution/G2/G3/G4/P09 invocation |

Deep P02 admission, source parsing, transport, signal derivation, P03 safety,
P04 normalization/features, and P05 scoring mechanics remain owned by their
existing suites and must not be duplicated wholesale.

## 17. Regression and acceptance requirements

If implementation is separately authorized, run:

1. the focused RTI-11 module;
2. P04-LME-01, LME-02, and LME-03 regressions unchanged;
3. P03-T02/T03 and canonical evidence producer/P04-to-P05 regressions;
4. combined relevant P02–P05 integration regression;
5. the full required Python regression and repository whitespace/static checks;
6. TypeScript/build checks only as required by repository CI; and
7. `git diff --check` and scope review.

Acceptance requires every locked contract above, no existing behavior change,
no forbidden import/call/file, deterministic result canonicalization, and a
diff confined to the separately authorized file scope. Any need for a route,
runtime caller, model/migration, persistence, retry, provider loop, P05-T06–08,
P06, RTI, or economic/execution authority is a stop condition.

## 18. Expected future implementation scope

Only after separate explicit implementation authorization, the expected
maximum change is:

- `backend/application/market_to_opportunity_composition.py` — one thin service,
  request/result types, bounded validation/delegation;
- `tests/test_market_to_opportunity_composition.py` — one focused module;
- `backend/application/__init__.py` — minimal export only if convention needs it;
- `PROJECT_STATE.md`, `docs/CHANGELOG.md`, and this specification for closure.

No database model, migration, repository, session, dependency, configuration,
secret, route, public schema, or deployment file is expected.

## 19. Forbidden scope

Forbidden are P05-T06 record, P05-T07 history, P05-T08 context, P06 decision,
RTI paper lifecycle, persistence, cache, publication, HTTP/API, dashboard,
provider discovery/polling/runtime, retry, worker, scheduler, queue, auth,
wallet, signing, broadcast, execution, live trading, realization/settlement,
G2, G3, G4, P09, new economic semantics, and changes to existing P02/P03/P04/
P05 or RTI-03–10 behavior.

## 20. Open questions

No blocking contract question remains for controller review. The controller
may choose implementation names, but must not weaken these locks. A future
implementation authorization should explicitly confirm:

1. the paired P03 handoff correction;
2. the four-state result vocabulary plus raised validation failures;
3. explicit `processing_time` and `evaluated_at` rather than defaults;
4. deterministic wrapper `result_digest`; and
5. no concrete runtime caller wiring.

## 21. Controller recommendation and authorization boundary

Approve this document as the final P01-RTI-11 specification. The dependency
owners are ready, the residual identity/time/failure/provenance contracts are
now locked, and a future implementation can remain one thin, testable
application boundary with small code blast radius.

The controller subsequently authorized limited implementation of this exact
specification. That authorization covers only the thin application service,
focused tests, minimal export, governance documentation, and normal GitHub
delivery. It does not authorize a concrete runtime caller, provider runtime,
publishing, persistence, downstream decision/paper/economic flow, or any other
scope excluded above. Any implementation expansion still requires a separate
controller decision.

`SPECIFICATION READY FOR CONTROLLER REVIEW`
