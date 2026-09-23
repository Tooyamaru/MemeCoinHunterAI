# P01-RTI-16 — Deterministic RTI-15-to-Controlled Paper Lifecycle Continuation

**Status:** SPECIFICATION COMPLETE / READY FOR CONTROLLER REVIEW / IMPLEMENTATION NOT AUTHORIZED

**Proposed contract:** `p01-rti-16-v1`

**Boundary:** application-level, one-shot, deterministic, paper-only
composition over existing contracts

## 1. Purpose

P01-RTI-16 defines the missing bounded compatibility composition between the
completed RTI-15 paper-admission continuation and the completed RTI-02
controlled paper lifecycle owner.

It accepts exactly:

1. one canonical `P01Rti15PaperAdmissionContinuationResult`;
2. one explicit canonical `PaperFillInstruction`; and
3. one explicit canonical `PaperLifecycleEvidence`.

For exact `ADMISSION_MATERIALIZED`, it materializes one RTI-01-compatible
`ControlledPaperRunAdmissionResult` solely from already-authoritative nested
artifacts, delegates exactly once to `run_controlled_paper_lifecycle`, preserves
the exact returned `ControlledPaperLifecycleResult`, and stops.

RTI-16 does not run RTI-01, RTI-11, RTI-12, RTI-13, RTI-14, or RTI-15. It does
not rerun P05, P06, Risk/Capital, or P07-T01.

## 2. Existing authority remains unchanged

| Concern | Existing owner | RTI-16 authority |
| --- | --- | --- |
| Market/opportunity composition | RTI-11 and P04/P05 owners | None; consume lineage only |
| Opportunity context | RTI-12 and P05 owners | None; consume lineage only |
| Decision intent | RTI-13 / P06 | None; pass exact object only |
| Paper Risk/Capital authorization | RTI-14 / Risk/Capital Authority | None; pass exact object only |
| P07-T01 admission | RTI-15 / P07-T01 | None; pass exact object only |
| Compatibility envelope shape | Existing RTI-01 result contract | Construct one exact envelope; no upstream evaluation |
| P07-T02–T07 and P08-T01 lifecycle | RTI-02 | Delegate exactly once and preserve result |
| Persistence/publication | RTI-03/04 | No access; prohibited |
| Economic realization/settlement | G2/G3/G4 | Blocked/not authorized |
| Wallet/execution/live trading | P09 and future execution boundaries | Not authorized |

The compatibility envelope is not a new admission decision. It is a bounded
structural carrier required by the existing RTI-02 signature.

## 3. Exact input contract

### 3.1 Upstream result

The first input must be an exact canonical
`P01Rti15PaperAdmissionContinuationResult` with contract
`p01-rti-15-v1`. Reconstruction with the authoritative RTI-15 constructor must
produce an equivalent object and the same result digest.

For `ADMISSION_MATERIALIZED`, it must preserve:

- exact RTI-13/P06 `DecisionIntent` object;
- exact RTI-14 `PaperRiskCapitalAuthorizationResult` object with canonical
  `APPROVED` status and paper-only effect;
- exact RTI-15 `AuthorizationObservation` object;
- exact P07-T01 v2 `PaperSimulationInput` object; and
- exact identity, version, time, authorization, and digest linkage already
  required by RTI-15.

RTI-16 must not infer, clone, repair, upgrade, downgrade, or recalculate these
objects.

### 3.2 Fill instruction

The second input must be the exact existing `PaperFillInstruction` type. It is
caller-owned and supplies only the canonical explicit facts already owned by
RTI-02/P07-T02, including side, quantity and units, liquidity, quote price and
times, friction, optional sell inventory, and quote currency.

RTI-16 must reconstruct or otherwise validate its authoritative canonical
representation before any outcome branch. Its digest is the authoritative
SHA-256 digest of that representation.

### 3.3 Lifecycle evidence

The third input must be the exact existing `PaperLifecycleEvidence` type. It is
caller-owned and supplies only the canonical explicit facts already owned by
RTI-02/P07-T03–T05, including prior state, target identity, valuation and
accounting contexts, lifecycle reference time, ledger stream facts, and the
independent reconciliation expectation.

RTI-16 must reconstruct or otherwise validate its authoritative canonical
representation before any outcome branch. Its digest is the authoritative
SHA-256 digest of that representation.

The caller cannot omit, replace, or request discovery of either explicit
runtime input.

## 4. Version binding

| Contract | Required version | Behavior on mismatch |
| --- | --- | --- |
| RTI-16 wrapper | `p01-rti-16-v1` | Validation failure |
| RTI-15 input | `p01-rti-15-v1` | Validation failure |
| Compatibility admission | `p01-rti-01-v1` | Validation failure |
| P07-T01 input | `p07-t01-v2` | Validation failure through canonical RTI-15/P07 linkage |
| RTI-02 lifecycle result | `p01-rti-02-v1` | Invalid owner result; bounded unavailable result |

There is no latest-version lookup, alias, fallback, conversion, silent upgrade,
or downgrade.

## 5. Validation before branching

The service must validate all three supplied inputs before examining the
upstream outcome. Therefore malformed fill or lifecycle evidence remains a
validation failure even when RTI-15 did not admit the paper run.

The following remain safe standardized `ValueError` failures and must not be
converted into wrapper outcomes:

- unsupported type or contract version;
- malformed or non-canonical input;
- digest tampering;
- decision, authorization, observation, P07 input, asset, state, time, or
  provenance mismatch;
- structural linkage mismatch;
- `ValueError` from the compatibility-envelope constructor; and
- `ValueError` raised by the RTI-02 owner.

No raw nested exception text, Python type, traceback, or object representation
may be exposed by the standardized error message.

## 6. Exact compatibility-envelope rule

Only exact RTI-15 `ADMISSION_MATERIALIZED` may materialize the compatibility
envelope.

The service must call the exact existing `ControlledPaperRunAdmissionResult`
constructor once with:

- outcome `READY_FOR_PAPER_SIMULATION`;
- empty reason codes;
- the exact nested `DecisionIntent` object;
- the exact nested approved `PaperRiskCapitalAuthorizationResult` object;
- the exact nested `PaperSimulationInput` object; and
- contract version `p01-rti-01-v1`.

The resulting envelope must be canonical and must retain exact object identity
for the three nested owner objects. Its canonical digest must be verified. The
service must not call `prepare_controlled_paper_run` or any alias and must not
create an authorization observation or P07 input.

Unexpected envelope-factory exceptions map to
`ADMISSION_ENVELOPE_UNAVAILABLE`. A returned value that is not the exact
canonical envelope above maps to `ADMISSION_ENVELOPE_INVALID_RESULT`.

## 7. Exact lifecycle delegation

After a valid compatibility envelope exists, the service must call the exact
existing `run_controlled_paper_lifecycle` owner once with:

- the exact compatibility envelope;
- the exact caller-supplied `PaperFillInstruction`; and
- the exact caller-supplied `PaperLifecycleEvidence`.

No alias or fallback is permitted. There is no second call, retry, polling,
repair, partial replay, or owner substitution.

The owner return must be an exact canonical `ControlledPaperLifecycleResult`
with contract `p01-rti-02-v1`, exact compatibility-envelope identity/digest,
and a verified result digest. A valid return is preserved as the exact same
object. RTI-16 must not rewrite its outcome, reason codes, artifacts, history,
observation, or digest.

Consequently, `LIFECYCLE_MATERIALIZED` means that the RTI-02 owner produced an
exact canonical result. It does not mean that RTI-02 necessarily produced an
observation. The nested RTI-02 outcomes remain authoritative, including
`OBSERVATION_PRODUCED`, `RECONCILIATION_NOT_MATCHED`, and any other canonical
owner outcome.

An unexpected owner exception maps to `LIFECYCLE_UNAVAILABLE`. A returned value
that is not the exact canonical RTI-02 result maps to
`LIFECYCLE_INVALID_RESULT`. Owner `ValueError` remains the validation failure
defined in section 5.

## 8. Non-admitted upstream handling

Every canonical RTI-15 outcome other than `ADMISSION_MATERIALIZED` returns
`UPSTREAM_NOT_ADMITTED` after all three inputs pass validation.

The result must preserve the exact RTI-15 object, contract version, outcome,
reason codes, and result digest. It must contain no compatibility envelope and
no lifecycle result. Neither the envelope constructor nor RTI-02 may be called.

RTI-16 must not reinterpret `UPSTREAM_NOT_AUTHORIZED` or
`ADMISSION_UNAVAILABLE` as economic, trading, fill, execution, or lifecycle
semantics.

## 9. Output contract and bounded vocabulary

The future immutable result must contain exactly the information necessary to
preserve the boundary:

- `contract_version`;
- `outcome`;
- finite `reason_codes`;
- exact `upstream_result`;
- exact `fill_instruction`;
- exact `lifecycle_evidence`;
- optional exact `compatibility_admission`;
- optional exact `lifecycle_result`; and
- `result_digest`.

The outcome vocabulary is exactly:

- `LIFECYCLE_MATERIALIZED`;
- `UPSTREAM_NOT_ADMITTED`; and
- `LIFECYCLE_UNAVAILABLE`.

| Condition | Wrapper outcome/behavior | Required bounded reason |
| --- | --- | --- |
| Canonical RTI-02 result returned | `LIFECYCLE_MATERIALIZED` | none |
| Canonical RTI-15 outcome is not admitted | `UPSTREAM_NOT_ADMITTED` | `UPSTREAM_NOT_ADMITTED` |
| Unexpected envelope-factory exception | `LIFECYCLE_UNAVAILABLE` | `ADMISSION_ENVELOPE_UNAVAILABLE` |
| Invalid envelope-factory return | `LIFECYCLE_UNAVAILABLE` | `ADMISSION_ENVELOPE_INVALID_RESULT` |
| Unexpected RTI-02 exception | `LIFECYCLE_UNAVAILABLE` | `LIFECYCLE_UNAVAILABLE` |
| Invalid RTI-02 return | `LIFECYCLE_UNAVAILABLE` | `LIFECYCLE_INVALID_RESULT` |
| Malformed/tampered/version/linkage input or owner `ValueError` | Safe validation exception | none; not a semantic result |

No WIN, LOSS, PROFIT, ROI, BUY, SELL, REALIZED, SETTLED, SUCCESSFUL_TRADE, or
other economic/trading result may be added.

## 10. Deterministic result digest

`result_digest` is lowercase SHA-256 over UTF-8 canonical JSON with sorted
keys, compact separators, and `ensure_ascii=True`. Its material contains only:

- RTI-16 contract version, outcome, and ordered reason codes;
- RTI-15 contract version, outcome, and result digest;
- compatibility admission contract version and digest, or `null`;
- `PaperFillInstruction.digest`;
- `PaperLifecycleEvidence.digest`;
- RTI-02 contract version, outcome, and result digest, or `null`.

The digest must not depend on:

- wall clock or implicit current time;
- environment, configuration lookup, secret, provider, or network;
- callable identity, exception text/type, object address, or traceback;
- filesystem or dictionary iteration order;
- randomness, retry count, polling, process identity, or shared mutable state;
- current market state not explicitly supplied; or
- persistence/database state.

Equivalent canonical inputs and equivalent owner results must yield the same
digest.

## 11. Identity and provenance continuity

| Lineage | Required preservation |
| --- | --- |
| RTI-15 | Exact object, contract, outcome, reasons, and digest |
| Decision | Exact RTI-13/P06 `DecisionIntent` object and digest |
| Authorization | Exact RTI-14 Risk/Capital result, policy lineage, effect, status, and digest |
| P07 admission | Exact RTI-15/P07-T01 observation, input object, identities, times, and digest |
| Fill instruction | Exact caller object and canonical digest |
| Lifecycle evidence | Exact caller object, state/accounting/valuation/reconciliation lineage, and digest |
| Compatibility admission | Exact nested objects and authoritative RTI-01 digest |
| Lifecycle | Exact RTI-02 result, nested artifacts, provenance, reasons, and digest |

No identity, source, timestamp, observation, state, expectation, or provenance
may be synthesized or repaired.

## 12. Time semantics

RTI-16 owns no time. It must preserve without substitution:

- RTI-15/P07 admission reference and observation times;
- fill instruction quote-observation and explicit fill times;
- prior-state and valuation observation times;
- lifecycle reference time; and
- every nested RTI-02 artifact time.

Processing time, wall clock, receipt time, or a new evaluation time cannot be
used in place of any explicit owner/caller time.

## 13. Side-effect and state guarantees

One invocation is pure with respect to external state. It creates at most one
invocation-local compatibility envelope and delegates once to the existing
in-memory lifecycle owner. Any invocation-local history created inside RTI-02
remains owned by RTI-02.

There is no database/session/repository access, persistence, publication,
network request, provider call, environment lookup, filesystem access, loop,
sleep, retry, shared cache, service-level history, module/global mutable state,
queue, worker, scheduler, or concrete caller.

## 14. Unreachability matrix

| Boundary | Required proof |
| --- | --- |
| RTI-01 execution | `prepare_controlled_paper_run` is never called |
| RTI-11–RTI-15 execution | No upstream service is called; one supplied RTI-15 result only |
| Duplicate P05/P06/Risk/P07-T01 | No related evaluator, authority, adapter, or constructor call |
| Persistence/publication | No RTI-03/04, repository, session, model, migration, or database import/call |
| Provider/runtime | No network, provider, polling, retry, secret, or concrete caller |
| API/dashboard | No route, HTTP/WebSocket, schema exposure, frontend, or Hunter Room integration |
| Worker/scheduler/queue | No registration, dispatch, background task, cadence, or queue call |
| Wallet/execution | No wallet, signing, RPC, DEX, broadcast, transaction, or live-trading call |
| Economic realization | No settlement, realized P&L, WIN/LOSS, G2/G3/G4, or P09 dependency |

## 15. Focused future test matrix

If implementation is separately authorized, focused tests must prove:

1. exact admitted success builds one compatible envelope and calls RTI-02 once;
2. exact RTI-02 result object and every nested outcome/artifact are preserved;
3. each non-admitted RTI-15 outcome stops before envelope and lifecycle calls;
4. all three inputs are validated before branching;
5. malformed type, tampering, digest, identity, structure, and version fail as
   standardized validation exceptions;
6. envelope constructor receives exact objects and is called exactly once;
7. `prepare_controlled_paper_run` and all upstream evaluators remain unreachable;
8. envelope `ValueError` remains a validation exception;
9. unexpected/invalid envelope results map to their finite bounded reasons;
10. lifecycle owner receives exact envelope and exact explicit caller inputs;
11. lifecycle owner is called exactly once with no alias, fallback, or retry;
12. owner `ValueError` remains a validation exception;
13. unexpected/invalid owner results map to their finite bounded reasons;
14. RTI-02 `OBSERVATION_PRODUCED` is preserved;
15. RTI-02 `RECONCILIATION_NOT_MATCHED` is preserved without reinterpretation;
16. representative other canonical RTI-02 outcomes are preserved;
17. identity, provenance, version, and time continuity hold end to end;
18. repeated equivalent invocations have equivalent canonical output/digest;
19. no wall clock, environment, randomness, or shared mutable state participates;
20. no persistence/publication, provider/network, caller/runtime, worker,
    scheduler, queue, API/dashboard, wallet/execution, economic realization,
    G2/G3/G4, or P09 boundary is reachable.

Relevant regression must include RTI-13 through RTI-15, RTI-01/02, P07-T01
through T07, P08-T01, combined RTI regression, the full Python suite, Python
compilation/static checks, TypeScript typecheck/build, and whitespace checks.

## 16. Expected future implementation scope

If and only if separately authorized, the expected implementation shape is:

- one thin module under `backend/application/`;
- one focused test module;
- one minimal application export if required; and
- minimal governance/state/changelog updates.

No database model, migration, repository/session, dependency, route, API
schema, configuration, secret, worker, scheduler, queue, frontend, wallet, or
execution file is expected.

## 17. Acceptance criteria

The future implementation may close only when:

- the three exact input contracts and all version/identity links are validated;
- non-admitted upstream results stop before any lifecycle work;
- admitted input creates exactly one exact compatible envelope without upstream
  recomputation;
- RTI-02 is called exactly once and its exact result is preserved;
- wrapper digest/provenance are deterministic and canonical;
- validation and bounded-unavailable failures remain distinct and safe;
- all focused, regression, full-suite, build, and CI checks pass; and
- forbidden boundaries remain unreachable.

## 18. Authorization boundary and STOP

This document authorizes no implementation. It does not authorize creation of
the future module or tests, nor any source/runtime change.

The hard terminal boundary is the exact `ControlledPaperLifecycleResult`.
Persistence/publication, RTI-03/04, provider/network/polling, a concrete runtime
caller, worker/scheduler/queue, API/dashboard, wallet/signing/RPC/DEX,
execution/live trading, economic realization, G2/G3/G4, and P09 remain outside
scope and unauthorized.

**SPECIFICATION READY FOR CONTROLLER REVIEW**
