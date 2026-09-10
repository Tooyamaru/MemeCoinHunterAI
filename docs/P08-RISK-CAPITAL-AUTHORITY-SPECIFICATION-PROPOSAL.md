# P08 — Risk/Capital Authority Safe V1 Specification Proposal

**Status:** PROPOSAL / NOT AUTHORIZED  
**Document type:** Documentation-only specification proposal  
**Boundary:** P06 `DecisionIntent` → paper-only Risk/Capital Authority → P07
paper-simulation lifecycle  
**Contract posture:** Deterministic, explainable, risk-first, paper-first, and
provider-neutral  
**Live-trading posture:** No live trading, real orders, settlement, wallet,
signer, provider, or external execution authority

## 1. Purpose and governance status

This proposal defines the Safe V1 contract for the missing independent
Risk/Capital Authority between P06 and P07. It turns one immutable analytical
P06 `DecisionIntent` and one immutable paper-only policy snapshot into one
deterministic authorization result for exactly one P07 paper-simulation
lifecycle.

The proposed authority is not MemeCoinHunterAI’s Decision Engine, a provider
adapter, an exchange integration, or a live-trading risk gate. MemeCoinHunterAI
is not Binance or Polymarket. No provider, venue, chain endpoint, wallet,
signer, broadcast path, settlement endpoint, or live execution system is
selected or implied by this proposal.

This document does not:

- modify P05, P06, P07, G1, G2, G3, G4, P08-T07, P09, or any existing
  specification;
- create or modify source code, tests, dependencies, APIs, workflows,
  persistence, or runtime behavior;
- create a policy snapshot, authorization result, or P07 observation at
  runtime; or
- authorize implementation.

The required governance sequence is:

```text
this proposal
    → formal specification review and audit
    → explicit implementation authorization naming exact files
    → implementation and focused tests
    → separate implementation audit
```

No code or test file may be created from this proposal alone.

## 2. Existing boundary basis

The proposal preserves the following approved ownership:

```text
P05 hard-risk / opportunity context
    → P06 analytical DecisionIntent
    → independent Risk/Capital Authority
    → P07-T01 paper input
    → P07 paper lifecycle
    → P08 non-economic evidence and simulation recognition
```

P05-T03 produces only hard-risk viability:

```text
ELIGIBLE | DISQUALIFIED | INSUFFICIENT_EVIDENCE
```

It does not authorize capital or action. The authority may use the preserved
P05 result through the immutable P06 context, but it must not re-evaluate P05
evidence or replace its result.

P06 produces one immutable analytical `DecisionIntent`. `BUY`, including
`BUY + WAIT`, remains analytical and is not an order, allocation, or execution
instruction. The independent Risk Governor remains higher authority than P06.

P07-T01 already defines an independently supplied
`AuthorizationObservation`. P07 validates and consumes that observation; it
does not create, evaluate, renew, upgrade, or override it. For a scenario that
requires authorization, only a valid `PASS` observation is admissible.

## 3. Safe V1 contract summary

### 3.1 Input

Exactly two immutable values:

1. one validated P06 `DecisionIntent`; and
2. one validated `PaperRiskCapitalPolicySnapshot`.

The evaluator takes no ambient configuration, current time, account state,
provider state, database state, or third input. The policy snapshot contains
the explicit simulation reference time and all paper-only state required for
the decision.

### 3.2 Output

One immutable `PaperRiskCapitalAuthorizationResult` with:

```text
status = APPROVED | REJECTED
authorization_effect = PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
```

`APPROVED` permits only the identity-linked entry of exactly one P07
paper-simulation lifecycle. `REJECTED` permits nothing.

The result is not permission to fill, mutate a paper position, append a
ledger, reconcile, finalize a result, or perform any external action.

### 3.3 Safe V1 admission

Safe V1 admits only:

```text
P06 action       = BUY
P06 entry posture = WAIT
```

This is a paper-simulation admission rule, not an immediate-entry or
execution rule. `BUY + DEFERRED`, `WATCH`, `HOLD`, `TAKE_PROFIT`, `REDUCE`,
`EXIT`, `AVOID`, and `NO_TRADE` are rejected in Safe V1. Supporting another
action or posture requires a versioned contract change and a separate review.

## 4. `PaperRiskCapitalPolicySnapshot` input contract

The policy snapshot is a complete, immutable, point-in-time decision packet.
It contains policy identity, one paper lifecycle scope, paper-only risk and
capital observations, temporal boundaries, and provenance. No field may be
silently defaulted or loaded from ambient state.

### 4.1 Top-level fields

The proposed contract version is:

```text
contract_version = p08-risk-capital-policy-v1
```

The snapshot contains exactly these top-level groups:

| Field | Required | Meaning |
|---|---:|---|
| `contract_version` | yes | Exact policy-snapshot contract version. |
| `policy_snapshot_id` | yes | Stable identity for this immutable snapshot. |
| `policy_snapshot_digest` | derived/validated | SHA-256 digest of all other canonical snapshot fields. |
| `risk_governor_version` | yes | Version of the paper-only risk rules represented by the snapshot. |
| `capital_authorization_version` | yes | Version of the paper-only capital rules represented by the snapshot. |
| `evaluator_version` | yes | Version of the future deterministic authority evaluator. |
| `scope_identity` | yes | Exact one-lifecycle paper scope. |
| `decision_intent_digest` | yes | P06 intent digest to which this snapshot applies. |
| `context_digest` | yes | P06 context digest to which this snapshot applies. |
| `simulation_reference_time` | yes | Explicit UTC cutoff for this authorization. |
| `valid_from` | yes | Earliest reference time at which the snapshot is usable. |
| `valid_until` | yes | Latest reference time at which it is usable. |
| `risk_state` | yes | Supplied paper-risk gate state and bounded flags. |
| `paper_capital_state` | yes | Supplied virtual-paper budget and commitment state. |
| `paper_exposure_state` | yes | Supplied virtual-paper exposure state. |
| `provenance` | yes | Bounded provenance for the snapshot and observations. |

Unknown top-level fields are rejected. In particular, the schema has no
`account_balance`, `wallet`, `provider`, `order`, `execution`, `settlement`,
`realized_pnl`, `accounting`, or `classification` field.

### 4.2 Exact one-lifecycle scope

`scope_identity` is an immutable canonical mapping with exactly:

| Field | Meaning |
|---|---|
| `paper_lifecycle_id` | Identity of the one P07 lifecycle that this result may admit. |
| `paper_portfolio_id` | Identity of the virtual paper portfolio or simulation scope. |
| `candidate_id` | P06 candidate identity. |
| `chain_id` | Preserved candidate identity only; no chain is selected or contacted. |
| `token_identity` | Preserved candidate asset identity only. |

`paper_lifecycle_id` is not an order ID, transaction ID, wallet ID, venue ID,
or settlement ID. It is a local paper-lifecycle identity. An approved result
must never be reused for a different lifecycle, candidate, portfolio, chain
identity, or token identity.

The evaluator must verify that all scope values agree with the supplied P06
intent. A mismatch is a rejection and cannot be repaired by choosing one
value over another.

### 4.3 Paper-only risk state

`risk_state` is an immutable mapping with exactly:

| Field | Meaning |
|---|---|
| `status` | `PASS`, `BLOCK`, or `UNKNOWN`. |
| `emergency_stop` | Boolean paper-policy stop; Safe V1 approval requires `false`. |
| `risk_flags` | Sorted tuple of explicit paper-policy flags. |
| `observed_at` | UTC time at which this risk state was observed. |
| `available_at` | UTC time at which it was available to the evaluator. |
| `state_digest` | Digest of the complete risk-state value. |

`PASS` means only that the supplied paper-policy risk state contains no
blocking condition. It does not establish safety, profitability, or external
execution readiness. `BLOCK` and `UNKNOWN` fail closed.

Safe V1 does not calculate correlation, drawdown, market regime, portfolio
optimization, candidate ranking, or a new safety model. Those inputs require
separate immutable contracts and a versioned expansion.

### 4.4 Virtual paper capital state

`paper_capital_state` is an immutable mapping with exactly:

| Field | Meaning |
|---|---|
| `unit` | Canonical simulation-only unit shared by all amounts below. |
| `budget_total` | Total virtual-paper budget for the declared scope. |
| `committed_before` | Virtual-paper amount already committed before this lifecycle. |
| `requested_entry` | Virtual-paper amount requested for this one lifecycle. |
| `max_single_entry` | Maximum permitted virtual-paper amount for one lifecycle. |
| `observed_at` | UTC observation time. |
| `available_at` | UTC availability time. |
| `state_digest` | Digest of the complete capital-state value. |

All amount fields are finite, normalized decimal values in the same
simulation-only `unit`. They must be non-negative, and
`requested_entry` must be greater than zero. No conversion, quote, price,
market value, cash balance, or external numeraire is used.

Safe V1 applies these exact checks:

```text
requested_entry <= max_single_entry
committed_before + requested_entry <= budget_total
```

The values are a virtual paper budget, not an account balance or capital
movement. Unknown, unavailable, negative, non-canonical, or contradictory
values fail closed; unknown does not become zero.

### 4.5 Virtual paper exposure state

`paper_exposure_state` is an immutable mapping with exactly:

| Field | Meaning |
|---|---|
| `unit` | Same canonical simulation-only unit as `paper_capital_state`. |
| `exposure_before` | Virtual-paper exposure before this lifecycle. |
| `max_total_exposure` | Maximum virtual-paper exposure for the declared scope. |
| `observed_at` | UTC observation time. |
| `available_at` | UTC availability time. |
| `state_digest` | Digest of the complete exposure-state value. |

Safe V1 applies:

```text
exposure_before + requested_entry <= max_total_exposure
```

The evaluator must reject mismatched units, negative values, missing values,
future observations, and values whose nested digest does not verify. This is a
paper exposure limit only. It is not a live position, wallet balance, account
permission, or economic valuation.

### 4.6 Provenance

`provenance` is a bounded canonical mapping containing only references needed
to reproduce the snapshot, including:

- the P05/P06 contract and evaluator versions;
- the P06 intent and context digests;
- the policy and evaluator versions;
- risk, capital, and exposure state identities and digests; and
- the identity of the caller-supplied observation packet, if one exists.

Provenance values are references, not instructions to fetch data. Provider
names or source labels may be retained as non-authoritative provenance when
already supplied, but they do not grant authority and must not trigger I/O.
Credentials, secrets, opaque objects, callbacks, and unbounded payloads are
forbidden.

## 5. Input validation and approval predicate

The evaluator must validate the complete P06 object and complete policy
snapshot before applying any policy limit.

### 5.1 P06 validation

The supplied `DecisionIntent` must:

1. be the supported immutable P06 contract;
2. have a valid canonical representation and digest;
3. preserve complete P05 context and provenance;
4. have supported P06 contract, ruleset, and evaluator versions;
5. have a timezone-aware decision time;
6. have action `BUY`;
7. have entry posture `WAIT`;
8. have no uncertainty entries;
9. have no invalidation conditions; and
10. contain a P05 hard-risk result with viability `ELIGIBLE`.

The authority does not re-run P05 or P06. It validates and consumes the
already-materialized upstream result. A P06 `NO_TRADE` or a non-eligible P05
state cannot be overridden by any paper policy.

### 5.2 Policy validation

The policy snapshot must:

1. use the supported Safe V1 contract and evaluator versions;
2. verify every nested identity and digest;
3. match the P06 intent and context digests;
4. match candidate, chain, token, portfolio, and lifecycle scope;
5. contain a single explicit simulation reference time;
6. contain a valid non-empty window with
   `valid_from <= simulation_reference_time <= valid_until`;
7. have all observation availability times at or before the reference time;
8. have `risk_state.status == PASS`;
9. have `risk_state.emergency_stop == false`;
10. contain valid virtual-paper capital and exposure amounts; and
11. pass both exact paper-capital limit formulas.

### 5.3 Approval predicate

The result may be `APPROVED` only if every validation and policy condition
passes:

```text
valid P06 DecisionIntent
AND valid PaperRiskCapitalPolicySnapshot
AND exact P06/policy identity linkage
AND P05 hard-risk viability = ELIGIBLE
AND P06 action/posture = BUY/WAIT
AND no P06 uncertainty or invalidation
AND risk_state = PASS
AND emergency_stop = false
AND valid paper budget
AND requested_entry <= max_single_entry
AND committed_before + requested_entry <= budget_total
AND exposure_before + requested_entry <= max_total_exposure
AND valid temporal cutoff and validity window
AND no contradiction or duplicate conflict
```

Every other outcome is `REJECTED`.

## 6. `PaperRiskCapitalAuthorizationResult` output contract

The proposed result contract and evaluator versions are:

```text
contract_version = p08-risk-capital-authority-v1
evaluator_version = p08-risk-capital-authority-evaluator-v1
```

The immutable result contains exactly:

| Field | Required | Meaning |
|---|---:|---|
| `contract_version` | yes | Result contract version. |
| `evaluator_version` | yes | Deterministic evaluator version. |
| `status` | yes | `APPROVED` or `REJECTED`. |
| `authorization_effect` | yes | Fixed value `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`. |
| `authorization_id` | derived | Stable result identity for this lifecycle decision. |
| `paper_lifecycle_id` | yes | Exact one-lifecycle identity. |
| `scope_identity` | yes | Exact scope accepted or rejected. |
| `decision_intent_digest` | yes | Consumed P06 intent digest. |
| `context_digest` | yes | Consumed P06 context digest. |
| `policy_snapshot_id` | yes | Consumed policy snapshot identity. |
| `policy_snapshot_digest` | yes | Consumed policy snapshot digest. |
| `simulation_reference_time` | yes | Supplied paper cutoff. |
| `valid_from` | yes | Authorization lower validity bound. |
| `valid_until` | yes | Authorization upper validity bound. |
| `primary_reason_code` | nullable | Highest-precedence reason; null only for approval. |
| `reason_codes` | yes | Sorted, deduplicated complete reason set. |
| `provenance` | yes | Bounded references to all consumed inputs. |
| `result_digest` | derived | SHA-256 digest of every other canonical result field. |

An `APPROVED` result has:

```text
primary_reason_code = null
reason_codes = ()
authorization_effect = PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
```

A `REJECTED` result has a non-null `primary_reason_code` and at least one
reason code. Rejection never grants a retry, fallback, reduction, or alternate
authority path.

`authorization_id` is derived deterministically from the contract version,
`paper_lifecycle_id`, `decision_intent_digest`, `policy_snapshot_digest`, and
`simulation_reference_time`. It is not an order, transaction, wallet, or
settlement identity.

## 7. P07 handoff

The approved result may be represented as the already-defined P07
`AuthorizationObservation` without changing P07-T01:

| P07 field | Safe V1 value |
|---|---|
| `observation_id` | `authorization_id` |
| `status` | `PASS` for `APPROVED`, `FAIL` for `REJECTED` |
| `scope_identity` | Exact Safe V1 `scope_identity` |
| `observed_at` | `simulation_reference_time` |
| `valid_from` | Result `valid_from` |
| `valid_until` | Result `valid_until` |
| `contract_version` | Safe V1 result contract version |
| `risk_governor_version` | Policy snapshot value |
| `capital_authorization_version` | Policy snapshot value |
| `reason_codes` | Result `reason_codes` |
| `unknown_reasons` | Empty for Safe V1 `APPROVED`; rejected unknown-state reasons when applicable |

This is a value-preserving handoff, not a second authorization. P07-T01 must
still validate the P06 digest, complete scope, validity window, simulation
reference time, and nested observation digest.

Safe V1 never uses `NOT_REQUIRED` for the paper-entry path. An absent,
malformed, stale, contradictory, or unknown authorization is not equivalent
to no authorization requirement.

An approved observation authorizes only the admission of the one
identity-linked P07 lifecycle. P07 still decides whether its supplied
execution observation, simulation configuration, initial paper state, and
replay identity are valid. P07 may produce a failed, rejected, unavailable, or
invalid paper outcome after authorization.

## 8. Stable reason vocabulary

The Safe V1 result uses only the following reason codes.

### 8.1 Input and identity reasons

- `MISSING_REQUIRED_INPUT`
- `INVALID_INPUT`
- `UNSUPPORTED_VERSION`
- `NON_CANONICAL_INPUT`
- `DIGEST_MISMATCH`
- `PROVENANCE_LINKAGE_FAILURE`
- `SCOPE_MISMATCH`
- `CONTRADICTORY_INPUT`

### 8.2 P05/P06 gate reasons

- `P05_HARD_RISK_NOT_ELIGIBLE`
- `P06_NO_TRADE`
- `P06_UNCERTAIN`
- `P06_INVALIDATED`
- `P06_ACTION_NOT_ALLOWED`
- `P06_ENTRY_POSTURE_NOT_ALLOWED`

### 8.3 Temporal and state reasons

- `REFERENCE_TIME_INVALID`
- `POLICY_NOT_YET_VALID`
- `POLICY_EXPIRED`
- `POLICY_STATE_STALE`
- `POLICY_STATE_FUTURE_DATED`
- `RISK_STATE_BLOCKED`
- `RISK_STATE_UNKNOWN`
- `PAPER_CAPITAL_STATE_UNKNOWN`
- `PAPER_EXPOSURE_STATE_UNKNOWN`
- `PAPER_OBSERVATION_UNAVAILABLE`

### 8.4 Paper-limit reasons

- `PAPER_UNIT_INVALID`
- `PAPER_ENTRY_AMOUNT_INVALID`
- `PAPER_ENTRY_LIMIT_EXCEEDED`
- `PAPER_BUDGET_EXCEEDED`
- `PAPER_EXPOSURE_LIMIT_EXCEEDED`

### 8.5 Replay and duplicate reasons

- `DUPLICATE_LIFECYCLE_CONFLICT`
- `REPLAY_IDENTITY_CONFLICT`

No provider-specific, venue-specific, wallet-specific, settlement-specific,
accounting-specific, or classification-specific reason is part of Safe V1.

## 9. Reason precedence and aggregation

The evaluator returns all independently observed reason codes in canonical
sorted order, but selects exactly one `primary_reason_code` using this fixed
precedence. Lower-numbered groups always win:

| Precedence | Group | Reason selection |
|---:|---|---|
| 1 | Required material | `MISSING_REQUIRED_INPUT`, then `INVALID_INPUT` |
| 2 | Contract compatibility | `UNSUPPORTED_VERSION`, then `NON_CANONICAL_INPUT` |
| 3 | Integrity | `DIGEST_MISMATCH`, then `PROVENANCE_LINKAGE_FAILURE` |
| 4 | Contradiction/scope | `CONTRADICTORY_INPUT`, then `SCOPE_MISMATCH` |
| 5 | Replay/duplicate | `DUPLICATE_LIFECYCLE_CONFLICT`, then `REPLAY_IDENTITY_CONFLICT` |
| 6 | Temporal validity | `REFERENCE_TIME_INVALID`, `POLICY_NOT_YET_VALID`, `POLICY_EXPIRED`, `POLICY_STATE_STALE`, `POLICY_STATE_FUTURE_DATED` |
| 7 | P05/P06 gate | `P05_HARD_RISK_NOT_ELIGIBLE`, `P06_NO_TRADE`, `P06_UNCERTAIN`, `P06_INVALIDATED`, `P06_ACTION_NOT_ALLOWED`, `P06_ENTRY_POSTURE_NOT_ALLOWED` |
| 8 | Availability/state | `RISK_STATE_BLOCKED`, `RISK_STATE_UNKNOWN`, `PAPER_CAPITAL_STATE_UNKNOWN`, `PAPER_EXPOSURE_STATE_UNKNOWN`, `PAPER_OBSERVATION_UNAVAILABLE` |
| 9 | Numeric/limit policy | `PAPER_UNIT_INVALID`, `PAPER_ENTRY_AMOUNT_INVALID`, `PAPER_ENTRY_LIMIT_EXCEEDED`, `PAPER_BUDGET_EXCEEDED`, `PAPER_EXPOSURE_LIMIT_EXCEEDED` |

Within a group, the listed order is the tie-breaker. `reason_codes` are
deduplicated and sorted by this same contract order, not by discovery order,
mapping order, or runtime timing.

Contract failures must not be demoted to a limit failure. A caller must never
be able to make an invalid or contradictory input appear as a routine
over-limit rejection.

## 10. Canonical identity, provenance, and digest rules

### 10.1 Canonical representation

Both the policy snapshot and result use the project’s existing deterministic
representation rules:

- mappings have sorted string keys;
- fields are explicit and unknown fields are rejected;
- tuples are ordered arrays;
- sets are forbidden;
- text is trimmed, non-empty where required, and UTF-8;
- timestamps are timezone-aware UTC in one canonical ISO-8601 form;
- decimal values are finite normalized decimal text;
- enum values use their explicit wire values;
- nullable values are represented as `null`, never omitted;
- opaque objects, non-string keys, NaN, infinity, and binary floating-point
  values are rejected; and
- SHA-256 is computed over compact UTF-8 JSON with sorted keys.

Equivalent canonical input must produce equal semantic values and equal
digests. Version fields are included in the digest material.

### 10.2 Input identity

The evaluator verifies:

```text
policy_snapshot.decision_intent_digest == DecisionIntent.digest
policy_snapshot.context_digest == DecisionIntent.context_digest
policy_snapshot.scope_identity.candidate_id == DecisionIntent.context.candidate_id
policy_snapshot.scope_identity.chain_id == DecisionIntent.context.chain_id
policy_snapshot.scope_identity.token_identity == DecisionIntent.context.token_identity
```

The complete P06 object remains the source of truth. The evaluator must not
construct a substitute intent from duplicated snapshot fields.

### 10.3 Result identity

`authorization_id` is deterministic and lifecycle-specific. The result digest
covers every other result field, including:

- status and authority effect;
- all lifecycle and scope identity;
- both upstream digests;
- policy identity and validity;
- primary and complete reasons;
- versions; and
- provenance.

The result digest is not accepted as authority over its source fields.

## 11. Cutoff and temporal rules

The policy snapshot’s `simulation_reference_time` is the only Safe V1 cutoff.
It is supplied data, not a call to `datetime.now()` or an equivalent clock.

All of these must hold:

```text
P06 context.reference_time <= P06 decision_time
P06 decision_time <= simulation_reference_time
valid_from <= simulation_reference_time <= valid_until
risk_state.observed_at <= risk_state.available_at
risk_state.available_at <= simulation_reference_time
paper_capital_state.observed_at <= paper_capital_state.available_at
paper_capital_state.available_at <= simulation_reference_time
paper_exposure_state.observed_at <= paper_exposure_state.available_at
paper_exposure_state.available_at <= simulation_reference_time
```

The evaluator must reject:

- missing or timezone-naive timestamps;
- future-dated values;
- a policy not yet valid at the reference time;
- an expired policy;
- state that became available after the reference time;
- an observation that is stale under the explicit policy validity window; and
- a P06 decision or context that occurs after the simulation reference time.

The evaluator must not use ingestion order, local timezone, filesystem time,
process time, network timing, or later-arriving data to change an outcome.

## 12. Replay and duplicate rules

The evaluator is stateless. It does not maintain a registry, database, cache,
queue, or external duplicate store.

Safe V1 defines replay and duplicate behavior from explicit identities:

1. Re-evaluating the same canonical `DecisionIntent`, the same canonical
   policy snapshot, the same `paper_lifecycle_id`, and the same reference time
   is an exact replay. It must produce the same status, reason codes,
   authorization ID, canonical representation, and result digest.
2. A different policy snapshot digest, intent digest, scope, reference time, or
   lifecycle identity produces a different authorization identity. It must not
   be silently treated as the same replay.
3. A caller-supplied indication that the lifecycle is already admitted with a
   different authorization digest is a `DUPLICATE_LIFECYCLE_CONFLICT` or
   `REPLAY_IDENTITY_CONFLICT` rejection. That indication must be part of the
   immutable snapshot if such a registry state is ever included.
4. Repeated IDs within any canonical identity or reason collection are
   rejected where repetition changes semantic identity; reason codes are
   deduplicated only after validation.
5. The evaluator never resolves duplicate or conflicting lifecycle records by
   freshness, insertion order, caller preference, or result magnitude.

No persistence or lifecycle registry is introduced by Safe V1. A future
deduplication or retention authority requires a separate specification.

## 13. Fail-closed behavior

The authority fails closed for every missing, invalid, stale, unsupported,
contradictory, future, unavailable, or out-of-policy condition.

For a validly constructed input pair that fails the approval predicate, the
evaluator returns `REJECTED` with stable reason codes. For a malformed input
that cannot satisfy the result contract, the future implementation must
produce a deterministic validation rejection or a deterministic validation
failure; it must never produce `APPROVED`.

The evaluator must not:

- fill missing fields with defaults;
- convert unknown to pass;
- convert unavailable to zero;
- use a failed P05/P06 state as an approval;
- refresh a stale snapshot;
- fetch newer data;
- repair a digest or provenance mismatch;
- choose one contradictory value;
- infer a paper budget from confidence or score;
- infer exposure from a missing state digest;
- bypass a missing authorization with `NOT_REQUIRED`;
- reinterpret a rejection as a reduced allocation;
- retry a provider or external endpoint; or
- use a second evaluator, hidden configuration, or fallback policy.

No rejection output may be interpreted as permission for a different lifecycle
or a live action.

## 14. Explicit authority exclusions

### 14.1 No provider or external data

The authority has no network, provider, exchange, venue, RPC, API, chain,
order-book, quote, liquidity, wallet, or external account dependency.

P06 and P07 identity fields such as `chain_id`, token identity, and source
provenance may be preserved as supplied values. They do not select a chain,
provider, venue, or data source.

### 14.2 No account, wallet, or signer authority

The authority must not read or write:

- account balances;
- bank or custody balances;
- wallet positions;
- private keys or seed phrases;
- signer state;
- transaction payloads;
- signing or broadcast state; or
- account permissions.

The only amounts in Safe V1 are virtual paper amounts in one declared
simulation-only unit.

### 14.3 No order or execution authority

The result contains no order side, price, route, quantity instruction,
execution request, transaction, fill, cancellation, retry, or submission
operation. `requested_entry` is a paper-policy amount used only for virtual
limit checks; it is not an order quantity or execution instruction.

### 14.4 No economic authority

The authority does not own or produce:

- execution or fill truth;
- settlement;
- realized P&L;
- accounting or cost basis;
- proceeds or cash;
- valuation as settlement;
- economic result; or
- performance classification.

Virtual paper budget and exposure predicates are admission controls, not
economic accounting.

## 15. Ownership boundaries

### 15.1 P05

P05 owns normalized opportunity and hard-risk viability. Its
`ELIGIBLE`, `DISQUALIFIED`, and `INSUFFICIENT_EVIDENCE` results remain
authoritative for that boundary. Safe V1 consumes the preserved P05 result
through P06 and must reject any non-eligible state.

Safe V1 must not re-run safety evidence, change hard-risk flags, or convert
P05 viability into an order or economic result.

### 15.2 P06

P06 owns deterministic analytical decision evaluation and the immutable
`DecisionIntent`. It owns action, entry posture, assumptions, uncertainty,
invalidation, confidence, and P05 provenance.

Safe V1 is independent of P06 and higher authority for paper admission. It
must not mutate, regenerate, rank, compare, or reinterpret the intent.

### 15.3 P07

P07 owns the paper-simulation lifecycle after admission:

- P07-T01 input validation;
- hypothetical fills and friction;
- paper position/exposure transitions;
- paper ledger records;
- paper reconciliation;
- canonical non-economic paper result; and
- local paper-result history.

Safe V1 supplies the independent authorization observation. P07 does not
create, evaluate, renew, upgrade, or override it. P07 may still reject or fail
the paper lifecycle for its own input, state, observation, configuration, or
replay conditions.

### 15.4 G1

G1 owns its separately governed simulation-only recognition and finality
semantics. A paper authorization or P07 paper result does not establish
external execution, settlement, realized value, or economic truth.

Safe V1 does not create, modify, or substitute for G1.

### 15.5 G2

G2 owns future realization eligibility and the governed distinction between
execution, settlement, and realization. Safe V1 emits no G2 eligibility,
settlement assertion, or external evidence.

G2 must not infer realization from an approved authorization, a paper fill,
paper position, paper ledger, reconciliation, or P07 finalized result.

### 15.6 G3

G3 owns future accounting and canonical economic-result calculation, including
costs, fees, basis, numeraire, conversion, precision, rounding, and realized
P&L. Safe V1 does not calculate any of these.

### 15.7 G4

G4 owns future performance classification and its approved vocabulary. Safe V1
does not emit or infer `WIN`, `LOSS`, `BREAKEVEN`, or any other classification.

### 15.8 P09

P09 is the separately governed live execution chain:

```text
DecisionIntent
    → live Risk/Capital Authorization
    → Execution Request
    → isolated Signing
    → Broadcast
    → Reconciliation
    → Journal
```

Safe V1 is not the P09 risk gate. A P07 `PASS` observation must never be
reused as P09 permission. No Safe V1 result activates, unlocks, or satisfies
any P09 gate.

## 16. Future implementation and test paths

These paths are proposals only. They must not be created until the separate
authorization gate in Section 17 passes.

### 16.1 Proposed implementation paths

```text
core/risk/paper_risk_capital_authorization.py
```

Proposed responsibility:

- immutable `PaperRiskCapitalPolicySnapshot`;
- immutable `PaperRiskCapitalAuthorizationResult`;
- deterministic pure evaluator;
- canonicalization, nested digest validation, reason precedence, and P07
  observation materialization by value.

An export change to `core/risk/__init__.py` is not assumed. It may be included
only if the implementation authorization names it explicitly.

No API route, worker, database, migration, cache, persistence layer,
provider adapter, wallet module, signer module, execution module, G1–G4
module, P08-T07 module, or P09 module is in scope.

### 16.2 Proposed focused test path

```text
tests/test_paper_risk_capital_authorization.py
```

The focused suite must prove:

1. valid immutable `BUY + WAIT` approval for one exact lifecycle;
2. P05 hard-risk, P06 `NO_TRADE`, uncertainty, invalidation, action, and
   posture rejection;
3. missing, invalid, non-canonical, unsupported, tampered, stale, future,
   unavailable, and contradictory snapshot rejection;
4. exact P06/context/scope/lifecycle identity linkage;
5. virtual budget, single-entry, and exposure formulas at below, equal, and
   above limits;
6. risk `BLOCK`, risk `UNKNOWN`, emergency stop, and unknown paper state;
7. stable primary reason precedence and canonical reason ordering;
8. nested immutability, canonicalization, and digest determinism;
9. replay identity stability and duplicate/conflicting-lifecycle behavior;
10. absence of ambient clock, provider, network, account, wallet, signer,
    order, execution, settlement, accounting, P&L, classification, and P09
    behavior; and
11. exact `APPROVED` → P07 `PASS` and `REJECTED` → P07 `FAIL` mapping without
    changing P07-T01.

Existing P05, P06, and P07 tests remain unchanged regression coverage.
Integration composition tests, persistence tests, provider tests, and live
execution tests are outside Safe V1.

## 17. Separate authorization gate before code creation

No implementation or test file may be created until all gates pass:

### Gate 1 — Specification approval

The project owner must approve:

- the exact Safe V1 input fields;
- the exact virtual-paper units and formulas;
- `BUY + WAIT` as the only admitted P06 action/posture;
- the output fields and versions;
- reason vocabulary and precedence;
- cutoff, validity, replay, and duplicate rules;
- P07 handoff semantics; and
- the complete forbidden-authority list.

### Gate 2 — Formal boundary audit

The approved specification must be audited against:

- P05 hard-risk and provenance ownership;
- P06 `DecisionIntent` immutability and non-authority;
- P07-T01 authorization observation and temporal validation;
- P07 paper-only ownership;
- G1 simulation-only recognition;
- blocked G2 and unauthorized G3/G4;
- P09 live-execution separation; and
- the no-provider/no-wallet/no-account constraint.

### Gate 3 — Explicit implementation authorization

A separate authorization must name the exact allowed files. The default
candidate is only:

```text
core/risk/paper_risk_capital_authorization.py
tests/test_paper_risk_capital_authorization.py
```

Any export, documentation, fixture, integration, or P07 change requires
explicit addition to that authorization. The specification proposal itself
does not authorize those changes.

### Gate 4 — Implementation audit

After implementation and focused tests, a separate audit must verify:

- deterministic replay;
- immutable inputs and outputs;
- fail-closed behavior;
- no hidden clock or external I/O;
- no forbidden fields or side effects;
- exact P07 handoff; and
- no expansion into P09 or G1–G4.

Passing tests alone does not authorize live execution or any later phase.

## 18. Safe V1 acceptance criteria

The future implementation is acceptable only if:

1. it accepts exactly one validated P06 intent and one validated immutable
   paper policy snapshot;
2. it produces only `APPROVED` or `REJECTED`;
3. `APPROVED` is possible only for one exact `BUY + WAIT` lifecycle scope;
4. all virtual-paper limits and risk gates are explicit and reproducible;
5. every non-approval condition fails closed;
6. input and output canonical representations and SHA-256 digests are stable;
7. reason-code aggregation and primary-reason precedence are deterministic;
8. identical inputs replay identically without a clock or external state;
9. duplicate and contradiction behavior does not use hidden persistence;
10. the P07 mapping is value-preserving and cannot use `NOT_REQUIRED` as a
    required-entry bypass;
11. no provider, account, wallet, signer, real order, execution, settlement,
    P&L, accounting, or classification authority exists; and
12. the exact future implementation and test paths were separately authorized
    before creation.

## 19. Final proposal decision

Safe V1 is recommended as a narrow, pure, provider-neutral paper admission
authority:

```text
P06 DecisionIntent
    +
PaperRiskCapitalPolicySnapshot
    ↓
PaperRiskCapitalAuthorizationResult
    status = APPROVED | REJECTED
    effect = PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
    ↓
one P07 AuthorizationObservation
    ↓
one P07 paper-simulation lifecycle
```

It is deterministic, explainable, immutable, point-in-time, and fail closed.
It does not use an ambient clock, provider data, account balances, wallets,
signers, real orders, execution, settlement, realized P&L, accounting, or
classification. It does not replace P05, P06, P07, G1, G2, G3, G4, P08-T07,
or P09.

**Current governance state:**

```text
proposal                         = documentation only
formal specification approval    = required
implementation authorization     = not granted
runtime authorization result     = not produced
P07 paper entry                  = not enabled by this document
G1/G2/G3/G4                      = unchanged and separately governed
P09                              = NOT AUTHORIZED
```