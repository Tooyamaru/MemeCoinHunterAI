# P01-PFX-01 — Deterministic Prevalidated Decision/Risk-Capital Prefix Preparation

**Status:** SPECIFICATION COMPLETE / READY FOR CONTROLLER REVIEW

**Implementation:** COMPLETE / CLOSED / CI PASS

**Contract:** `p01-pfx-01-v1`

## 1. Purpose

P01-PFX-01 prepares one exact, validated paper prefix from an already-produced
canonical RTI-11 result through RTI-14 without duplicate owner execution.

```
exact RTI-11 result
    ↓
RTI-12 exactly once
    ↓
RTI-13 exactly once
    ↓
exact PaperRiskCapitalPolicySnapshot constructed once
    ↓
RTI-14 exactly once
    ↓
STOP at exact RTI-14 result
```

It exists so the later OSC-02 suffix can consume one exact prevalidated RTI-14
result without rerunning RTI-12/13/14.

## 2. Exact request inputs

A future immutable `P01Pfx01Request` accepts exactly:

- `invocation_id: str`;
- `rti11_result: P01Rti11CompositionResult`;
- `decision_ruleset: DecisionEvaluationRuleset`;
- `decision_time: datetime`;
- `policy_seed: PaperRiskCapitalPolicySeed`.

No final `PaperRiskCapitalPolicySnapshot` is accepted from the caller because
its decision/context digests do not exist until RTI-13 materializes.

## 3. PaperRiskCapitalPolicySeed

The seed is an application-layer immutable explicit-input record. It is not a
domain authority.

It must carry every policy field that is independent of the exact RTI-13 output:

- `policy_snapshot_id`;
- `risk_governor_version`;
- `capital_authorization_version`;
- `evaluator_version`;
- explicit `paper_lifecycle_id`;
- explicit `paper_portfolio_id`;
- `simulation_reference_time`;
- `policy_cutoff_time`;
- all three max-age values;
- `valid_from`;
- `valid_until`;
- exact canonical `RiskState`;
- exact canonical `PaperCapitalState`;
- exact canonical `PaperExposureState`;
- optional allowed source/provenance text that does not duplicate dynamic
  decision/context identity.

The seed must not contain caller-asserted:

- `decision_intent_digest`;
- `context_digest`;
- candidate/chain/token identity that conflicts with RTI-11/RTI-13;
- P05/P06 contract/evaluator/ruleset references that can be derived exactly
  from the materialized decision.

No defaults are allowed.

## 4. Exact RTI-12 delegation

Only an exact canonical RTI-11 `COMPOSED` result may enter RTI-12.

Invoke
`P05OpportunityContextContinuationService.continue_to_context`
exactly once.

If RTI-11 is not `COMPOSED`, stop before RTI-12.

If RTI-12 returns a canonical non-materialized result, stop before RTI-13.

## 5. Exact RTI-13 delegation

For exact RTI-12 `CONTEXT_MATERIALIZED`, invoke
`OpportunityContextToDecisionContinuationService.continue_to_decision`
exactly once using the exact caller-supplied ruleset and decision time.

If RTI-13 returns a canonical non-materialized decision result, stop before
policy construction and RTI-14.

## 6. Exact policy snapshot materialization

Only after exact RTI-13 `DECISION_MATERIALIZED`:

1. read the exact `DecisionIntent`;
2. derive exact candidate/chain/token scope fields from that decision;
3. bind explicit seed lifecycle/portfolio identity;
4. bind exact `decision_intent_digest` and `context_digest`;
5. derive required P05/P06 provenance from the exact decision and context;
6. bind exact supplied risk/capital/exposure state digests;
7. construct one canonical `PaperRiskCapitalPolicySnapshot` exactly once.

The constructor remains the canonical validation owner.

No policy field may be repaired, recomputed from hidden state, defaulted, or
silently changed.

## 7. Exact RTI-14 delegation

Pass the exact RTI-13 result and exact materialized policy snapshot to
`DecisionToRiskCapitalContinuationService.continue_to_risk_capital` exactly
once.

Preserve the exact RTI-14 result whether the canonical authorization is
`APPROVED` or `REJECTED`.

A canonical Risk/Capital rejection is not a coordinator failure.

## 8. Wrapper outcomes

Proposed exact PFX-01 wrapper outcomes:

- `PREFIX_MATERIALIZED`;
- `UPSTREAM_STOPPED`;
- `OWNER_UNAVAILABLE`.

`PREFIX_MATERIALIZED` means one exact canonical RTI-14 result exists.
It does not mean authorization approval.

## 9. Stop behavior

- RTI-11 non-COMPOSED → `UPSTREAM_STOPPED`, zero RTI-12/13/14 calls.
- RTI-12 non-materialized → `UPSTREAM_STOPPED`, zero RTI-13/14 calls.
- RTI-13 non-materialized → `UPSTREAM_STOPPED`, zero policy/RTI-14 calls.
- policy constructor unexpected failure or invalid return → bounded
  `OWNER_UNAVAILABLE` with finite policy-stage reason.
- RTI-14 unexpected failure or invalid return → bounded
  `OWNER_UNAVAILABLE`.
- canonical RTI-14 result, APPROVED or REJECTED → `PREFIX_MATERIALIZED`.

## 10. Validation failures

Malformed, tampered, unsupported-version, structurally inconsistent, or
identity/time-mismatched explicit material remains standardized `ValueError`.

Examples:

- noncanonical RTI-11;
- noncanonical ruleset;
- naive decision time;
- noncanonical policy seed states;
- lifecycle/portfolio identity malformed;
- policy timing contradictions;
- exact RTI-13 subject not matching RTI-11;
- policy constructor `ValueError`;
- RTI-14 owner `ValueError`.

Raw exception details must not escape.

## 11. Determinism and digest

The future PFX-01 result digest must bind:

- PFX contract and invocation ID;
- wrapper outcome/reasons/terminal stage;
- RTI-11 contract/outcome/result digest;
- decision ruleset digest;
- decision time;
- full canonical policy seed digest;
- RTI-12 contract/outcome/result digest if produced;
- RTI-13 contract/outcome/result digest if produced;
- exact policy snapshot digest if produced;
- RTI-14 contract/outcome/result digest if produced;
- exact authorization status/result digest if present.

Exclude wall clock, environment, object address, callable identity, exception
text, provider state, filesystem state, and mutable shared state.

## 12. Owner cardinality

| Owner | Maximum calls |
| --- | ---: |
| RTI-11 | 0 |
| RTI-12 | 1 |
| RTI-13 | 1 |
| Policy snapshot constructor | 1 |
| RTI-14 | 1 |
| RTI-15 | 0 |
| RTI-16 | 0 |
| OSC-01 | 0 |
| OSC-02 | 0 |
| PFS | 0 |
| OSP / RTI-03 | 0 |

No retry or fallback is permitted.

## 13. Result shape

A future immutable `P01Pfx01Result` should contain:

- exact request;
- wrapper outcome;
- finite reason codes;
- terminal stage;
- optional exact RTI-12 result;
- optional exact RTI-13 result;
- optional exact policy snapshot;
- optional exact RTI-14 result;
- deterministic result digest.

Exact predecessor object identity must be preserved.

## 14. Relationship to OSC-02 and PFS

PFX-01 does not call OSC-02 or PFS.

A later separately governed controlled-input preparation gate may combine:

- exact PFX-01 `PREFIX_MATERIALIZED` RTI-14 result;
- exact PFS products;
- explicit RTI-15 paper inputs;

into one exact `P01Osc02Request`.

That later gate must still stop before executing OSC-02 unless separately
authorized.

## 15. Hard STOP

Stop at exact RTI-14.

Forbidden:

- RTI-15/16;
- OSC-01/02;
- PFS;
- persistence/OSP/RTI-03/04;
- provider/network/polling;
- autonomous candidate/pool selection;
- worker/scheduler/queue;
- API/WebSocket/dashboard;
- wallet/private key/signing;
- RPC/DEX/broadcast;
- execution/live trading;
- economic realization;
- G2/G3/G4/P09.

## 16. Future focused verification

A separately authorized implementation must prove:

1. exact RTI-11 is preserved;
2. RTI-12 runs at most once;
3. RTI-13 runs at most once;
4. policy snapshot is constructed only after exact RTI-13;
5. final policy digests match exact DecisionIntent/context;
6. explicit seed fields are preserved exactly;
7. RTI-14 runs at most once;
8. APPROVED and REJECTED canonical RTI-14 results are both preserved;
9. non-materialized upstream results stop later owners;
10. malformed/tampered material fails before downstream calls;
11. unexpected/invalid owner outputs are bounded without retry;
12. deterministic replay produces identical digests;
13. RTI-15/16, OSC-01/02, PFS, persistence, provider/runtime imports/calls are
    unreachable.

Regression must include RTI-12/13/14, Risk/Capital, OSC-02, and relevant P05/P06
tests.

## 17. Expected implementation scope

Only after separate explicit authorization:

- one thin application module for PFX-01;
- one focused test module;
- minimal application export;
- minimal governance documentation.

No database model, migration, persistence owner, API route, provider adapter,
dependency, secret, worker, scheduler, frontend, wallet, or execution code.

## 18. Exit criterion

Controller-authorized limited implementation passed GitHub Actions #191 and was
squash-merged through PR #61 at
`d96a7a24e4b1a572b0d2453a0aca5fd2d950645b`. The 1684-test Python
suite, whitespace check, TypeScript typechecks, and workspace builds passed.
The exact RTI-14 output remains the hard STOP. No downstream or live authority
is granted by this closure.

`IMPLEMENTATION COMPLETE / CLOSED / CI PASS`
