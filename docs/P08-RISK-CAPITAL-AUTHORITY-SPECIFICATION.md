# P08 — MemeCoinHunterAI Risk/Capital Authority Specification

**Status:** SPECIFICATION COMPLETE / AWAITING FORMAL AUDIT
**Document type:** Documentation-only Safe V1 specification
**Boundary:** immutable P06 `DecisionIntent` → paper-only Risk/Capital
Authority → P07 paper-simulation lifecycle
**Posture:** deterministic, explainable, risk-first, paper-first, and
provider-neutral
**Implementation status:** NOT AUTHORIZED

## 1. Purpose and governance position

This specification defines the smallest independent Risk/Capital Authority
between P06 analytical decision intent and P07 paper simulation. It is a
paper-lifecycle admission boundary only.

MemeCoinHunterAI is not Binance or Polymarket. This specification does not
select or integrate a provider, exchange, venue, chain endpoint, wallet,
signer, custody system, broadcast path, settlement endpoint, or live-trading
system.

The governed path is:

```text
validated P06 DecisionIntent
        +
immutable PaperRiskCapitalPolicySnapshot
        ↓
deterministic PaperRiskCapitalAuthorizationResult
        ↓
P07 AuthorizationObservation
        ↓
one P07 paper-simulation lifecycle
```

The specification:

- consumes exactly one immutable P06 `DecisionIntent` and one immutable
  `PaperRiskCapitalPolicySnapshot`;
- returns only deterministic `APPROVED` or `REJECTED` paper-lifecycle
  admission;
- admits only the explicitly defined Safe V1 `BUY + WAIT` case;
- never changes, repairs, resizes, reduces, substitutes, or regenerates a
  `DecisionIntent` or any P07 input;
- fails closed for missing, malformed, stale, future, unsupported,
  contradictory, tampered, unavailable, duplicate-conflicting, or
  out-of-policy material;
- has no ambient clock, external I/O, persistence, process-global state, or
  hidden policy default; and
- does not authorize any behavior outside the one identity-linked P07
  paper-simulation lifecycle.

This specification does not authorize implementation. The required sequence is:

```text
specification complete
        → formal specification audit
        → separate limited implementation authorization naming exact files
        → implementation and focused tests
        → separate implementation audit
```

## 2. Existing contract boundaries

### 2.1 P05 hard-risk boundary

P05-T03 owns hard-risk and disqualification evaluation for one normalized
opportunity. Its bounded viability values are:

```text
ELIGIBLE
DISQUALIFIED
INSUFFICIENT_EVIDENCE
```

P05-T03 preserves upstream evidence and provenance and is not a decision,
capital authorization, order, or execution boundary. Safe V1 consumes the
already-materialized P05 result through the complete P06 intent. It does not
re-run safety evaluation, reinterpret evidence, or upgrade uncertainty.

Only P05 hard-risk viability `ELIGIBLE` can satisfy Safe V1. Any other value is
rejected.

### 2.2 P06 analytical `DecisionIntent`

P06 consumes one validated P05-T08 `OpportunityContext` and produces one
immutable analytical `DecisionIntent`. P06 owns:

- analytical action;
- separate entry posture;
- uncertainty and invalidation conditions;
- expected-edge assumptions;
- analytical confidence;
- P05/P06 provenance, versions, canonical representation, and digest; and
- the supplied point-in-time decision time.

P06 does not own capital limits, exposure authorization, portfolio permission,
paper admission, wallet access, execution, signing, broadcast, or settlement.
`BUY + WAIT` remains analytical and is not an order, allocation, or execution
instruction.

Safe V1 consumes the exact validated intent by value and verifies its identity.
It must not reconstruct a substitute intent from duplicated fields.

### 2.3 P07 paper simulation

P07-T01 owns the immutable `PaperSimulationInput` boundary and consumes an
independently supplied `AuthorizationObservation`. P07 does not create,
evaluate, renew, upgrade, or override Risk/Capital Authorization.

P07 owns, after its own input validation:

- hypothetical execution observations and fills;
- paper position and exposure transitions;
- paper ledger entries;
- paper reconciliation;
- the canonical non-economic paper result; and
- local paper-result history.

P07 remains simulation-only. Paper admission, a paper fill, a paper position,
a paper ledger entry, reconciliation, or a finalized paper result is not
external execution truth, settlement, realized P&L, accounting, valuation,
classification, or live authority.

## 3. Safe V1 contract summary

### 3.1 Inputs

The evaluator accepts exactly two immutable values:

1. one validated P06 `DecisionIntent`; and
2. one validated `PaperRiskCapitalPolicySnapshot`.

The evaluator accepts no third value and reads no ambient configuration,
current time, account state, provider state, database state, cache, registry,
filesystem, queue, or process-global state.

The policy snapshot contains the explicit simulation reference time and all
paper-only risk, capital, exposure, scope, validity, and provenance material
required for this decision.

### 3.2 Output

The evaluator produces one immutable
`PaperRiskCapitalAuthorizationResult` with:

```text
status = APPROVED | REJECTED
authorization_effect = PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
```

`APPROVED` permits only the identity-linked entry of exactly one P07
paper-simulation lifecycle. `REJECTED` permits nothing.

The result does not permit or imply:

- a fill, position transition, ledger append, reconciliation, or result
  finalization;
- a retry, cancellation, repair, reduction, or alternate lifecycle;
- an order, quote, route, price, quantity instruction, or execution request;
- a provider, venue, chain endpoint, wallet, account, signer, custody system,
  transaction, broadcast, or settlement action;
- realized P&L, accounting, cost basis, proceeds, cash, valuation, or
  classification; or
- G1, G2, G3, G4, P08-T07, or P09 authority.

### 3.3 Safe V1 admission

Safe V1 admits exactly:

```text
P06 action       = BUY
P06 entry posture = WAIT
```

This means that a paper lifecycle may be admitted for the identity-linked
simulation. It does not mean immediate entry or execution.

The following are rejected:

```text
BUY + DEFERRED
WATCH
HOLD
TAKE_PROFIT
REDUCE
EXIT
AVOID
NO_TRADE
```

Supporting another action or posture requires a versioned specification change,
formal audit, and separate implementation authorization.

## 4. `PaperRiskCapitalPolicySnapshot`

The policy snapshot is a complete, immutable, point-in-time decision packet.
No required field may be silently defaulted, loaded from ambient configuration,
or replaced by a newer observation.

### 4.1 Contract identity and exact top-level fields

The Safe V1 policy contract version is:

```text
p08-risk-capital-policy-v1
```

The snapshot contains exactly these top-level fields:

| Field | Required | Meaning |
|---|---:|---|
| `contract_version` | yes | Must be `p08-risk-capital-policy-v1`. |
| `policy_snapshot_id` | yes | Stable identity of this immutable snapshot. |
| `policy_snapshot_digest` | derived and verified | SHA-256 digest of all other canonical snapshot fields. |
| `risk_governor_version` | yes | Version of the paper-only risk rules represented by the snapshot. |
| `capital_authorization_version` | yes | Version of the paper-only capital rules represented by the snapshot. |
| `evaluator_version` | yes | Version of the deterministic Safe V1 evaluator. |
| `scope_identity` | yes | Exact one-lifecycle paper scope. |
| `decision_intent_digest` | yes | Digest of the P06 intent to which this snapshot applies. |
| `context_digest` | yes | Digest of the P06 context to which this snapshot applies. |
| `simulation_reference_time` | yes | Caller-supplied UTC cutoff. |
| `valid_from` | yes | Earliest usable reference time. |
| `valid_until` | yes | Latest usable reference time. |
| `risk_state` | yes | Immutable paper-policy risk state. |
| `paper_capital_state` | yes | Immutable virtual-paper budget state. |
| `paper_exposure_state` | yes | Immutable virtual-paper exposure state. |
| `provenance` | yes | Bounded canonical references needed for reproduction. |

Unknown top-level fields are rejected. The schema contains no
`account_balance`, `wallet`, `provider`, `order`, `execution`, `settlement`,
`realized_pnl`, `accounting`, `valuation`, `roi`, `cost_basis`, `numeraire`,
or `classification` field.

### 4.2 Exact one-lifecycle scope

`scope_identity` is a canonical mapping with exactly:

| Field | Meaning |
|---|---|
| `paper_lifecycle_id` | Local identity of the one P07 lifecycle that may be admitted. |
| `paper_portfolio_id` | Identity of the virtual paper portfolio or simulation scope. |
| `candidate_id` | Candidate identity preserved from P06. |
| `chain_id` | Candidate identity preserved from P06; no chain is contacted or selected. |
| `token_identity` | Candidate asset identity preserved from P06. |

`paper_lifecycle_id` is not an order ID, transaction ID, wallet ID, venue ID,
or settlement ID.

The evaluator verifies exact agreement between the scope and the supplied P06
intent/context. A scope mismatch is a rejection. The evaluator must not choose
one conflicting value, repair the mismatch, or reuse an approval for another
lifecycle, candidate, portfolio, chain identity, or token identity.

### 4.3 Paper-only risk state

`risk_state` is a canonical mapping with exactly:

| Field | Meaning |
|---|---|
| `status` | `PASS`, `BLOCK`, or `UNKNOWN`. |
| `emergency_stop` | Boolean paper-policy stop; approval requires `false`. |
| `risk_flags` | Sorted tuple of explicit paper-policy flags. |
| `observed_at` | UTC time at which the risk state was observed. |
| `available_at` | UTC time at which it was available to the evaluator. |
| `state_digest` | Digest of the complete risk-state value. |

`PASS` means only that the supplied paper-policy risk state contains no
blocking condition. It is not proof of safety, profitability, solvency, or
external execution readiness.

`BLOCK`, `UNKNOWN`, `emergency_stop = true`, missing values, invalid values,
unavailable observations, and digest failures fail closed.

Safe V1 does not calculate correlation, drawdown, market regime, portfolio
optimization, candidate ranking, or a new safety model.

### 4.4 Virtual paper capital state

`paper_capital_state` is a canonical mapping with exactly:

| Field | Meaning |
|---|---|
| `unit` | One canonical simulation-only unit shared by all amounts below. |
| `budget_total` | Total virtual-paper budget for the declared scope. |
| `committed_before` | Virtual-paper amount committed before this lifecycle. |
| `requested_entry` | Virtual-paper amount requested for this lifecycle admission check. |
| `max_single_entry` | Maximum virtual-paper amount permitted for one lifecycle. |
| `observed_at` | UTC observation time. |
| `available_at` | UTC availability time. |
| `state_digest` | Digest of the complete capital-state value. |

All amount fields are finite, normalized, non-negative decimal values in the
same simulation-only unit. `requested_entry` must be greater than zero.

Safe V1 applies exactly these checks:

```text
requested_entry <= max_single_entry
committed_before + requested_entry <= budget_total
```

The values describe virtual paper budget only. They are not an account
balance, cash balance, capital movement, quote, price, order quantity,
numeraire, or economic valuation.

Unknown, unavailable, negative, non-canonical, contradictory, or digest-invalid
values are rejected. Unknown does not become zero.

### 4.5 Virtual paper exposure state

`paper_exposure_state` is a canonical mapping with exactly:

| Field | Meaning |
|---|---|
| `unit` | Must equal the capital-state simulation-only unit. |
| `exposure_before` | Virtual-paper exposure before this lifecycle. |
| `max_total_exposure` | Maximum virtual-paper exposure for the scope. |
| `observed_at` | UTC observation time. |
| `available_at` | UTC availability time. |
| `state_digest` | Digest of the complete exposure-state value. |

Safe V1 applies exactly:

```text
exposure_before + requested_entry <= max_total_exposure
```

Mismatched units, missing values, negative values, future observations, stale
values, contradictory values, and invalid nested digests are rejected.
Exposure is a virtual paper admission limit. It is not a live position,
wallet balance, account permission, or economic valuation.

### 4.6 Policy provenance

`provenance` is a bounded canonical mapping containing only references needed
to reproduce the snapshot, including:

- P05/P06 contract, ruleset, and evaluator versions;
- P06 intent and context digests;
- policy, Risk Governor, capital-authorization, and Safe V1 evaluator versions;
- risk, capital, and exposure state identities and digests; and
- the identity of the caller-supplied immutable observation packet, if present.

Provenance is descriptive data, not an instruction to fetch or refresh
anything. A provider or source label may be retained as non-authoritative
provenance when already supplied, but it does not grant authority or trigger
I/O.

Credentials, secrets, callbacks, opaque objects, executable values, and
unbounded payloads are forbidden.

## 5. Validation and approval predicate

The evaluator validates the complete P06 object and complete policy snapshot
before applying any limit formula.

### 5.1 P06 validation

The supplied `DecisionIntent` must:

1. be the supported immutable P06 contract;
2. have a valid canonical representation and digest;
3. preserve the complete P05 context and provenance;
4. use supported P06 contract, ruleset, and evaluator versions;
5. contain a timezone-aware decision time;
6. have action `BUY`;
7. have entry posture `WAIT`;
8. contain no uncertainty entries;
9. contain no invalidation conditions; and
10. preserve P05 hard-risk viability `ELIGIBLE`.

The authority validates and consumes the materialized upstream result. It does
not re-run P05 or P06. A P06 `NO_TRADE`, uncertainty, invalidation, or
non-eligible P05 state cannot be overridden by policy.

### 5.2 Policy validation

The policy snapshot must:

1. use the supported Safe V1 policy and evaluator versions;
2. verify every nested identity and digest;
3. match the P06 intent and context digests;
4. match candidate, chain, token, portfolio, and lifecycle scope;
5. contain one explicit timezone-aware simulation reference time;
6. satisfy `valid_from <= simulation_reference_time <= valid_until`;
7. have every observation `available_at` at or before the reference time;
8. have `risk_state.status == PASS`;
9. have `risk_state.emergency_stop == false`;
10. contain valid virtual-paper capital and exposure amounts;
11. use one identical unit for capital and exposure; and
12. pass every applicable paper limit formula.

### 5.3 Approval predicate

The result may be `APPROVED` only when every condition below is true:

```text
valid P06 DecisionIntent
AND valid PaperRiskCapitalPolicySnapshot
AND exact P06/policy identity linkage
AND P05 hard-risk viability = ELIGIBLE
AND P06 action/posture = BUY/WAIT
AND no P06 uncertainty or invalidation
AND risk_state = PASS
AND emergency_stop = false
AND valid paper budget and exposure state
AND requested_entry <= max_single_entry
AND committed_before + requested_entry <= budget_total
AND exposure_before + requested_entry <= max_total_exposure
AND valid temporal cutoff and validity window
AND no contradiction or duplicate identity conflict
```

Every other outcome is `REJECTED`.

Malformed input must fail validation deterministically and can never produce
`APPROVED`. When a rejection result can be represented, its status is
`REJECTED` with the applicable stable reason codes. A validation failure is
never a permissive fallback or an alternate authority path.

## 6. `PaperRiskCapitalAuthorizationResult`

The Safe V1 result and evaluator versions are:

```text
contract_version = p08-risk-capital-authority-v1
evaluator_version = p08-risk-capital-authority-evaluator-v1
```

The immutable result contains exactly:

| Field | Required | Meaning |
|---|---:|---|
| `contract_version` | yes | Must be `p08-risk-capital-authority-v1`. |
| `evaluator_version` | yes | Must be `p08-risk-capital-authority-evaluator-v1`. |
| `status` | yes | `APPROVED` or `REJECTED`. |
| `authorization_effect` | yes | Fixed value `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`. |
| `authorization_id` | derived | Deterministic identity of this lifecycle decision. |
| `paper_lifecycle_id` | yes | Exact one-lifecycle identity. |
| `scope_identity` | yes | Exact supplied paper scope. |
| `decision_intent_digest` | yes | Consumed P06 intent digest. |
| `context_digest` | yes | Consumed P06 context digest. |
| `policy_snapshot_id` | yes | Consumed policy snapshot identity. |
| `policy_snapshot_digest` | yes | Consumed policy snapshot digest. |
| `simulation_reference_time` | yes | Supplied paper cutoff. |
| `valid_from` | yes | Result lower validity bound. |
| `valid_until` | yes | Result upper validity bound. |
| `primary_reason_code` | nullable | Highest-precedence rejection reason; null only for approval. |
| `reason_codes` | yes | Complete bounded, deduplicated reason set. |
| `provenance` | yes | Bounded references to consumed immutable inputs. |
| `result_digest` | derived | SHA-256 digest of every other canonical result field. |

An approved result has:

```text
status = APPROVED
primary_reason_code = null
reason_codes = ()
authorization_effect = PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
```

A rejected result has a non-null `primary_reason_code` and at least one reason
code. Rejection grants no retry, fallback, reduction, repair, substitution,
or alternate authority.

`authorization_id` is derived deterministically from:

```text
contract_version
paper_lifecycle_id
decision_intent_digest
policy_snapshot_digest
simulation_reference_time
```

It is not an order, transaction, wallet, account, venue, execution, or
settlement identity.

## 7. P07 handoff

The result may be represented by the existing P07-T01
`AuthorizationObservation` without changing P07-T01:

| P07 field | Safe V1 value |
|---|---|
| `observation_id` | `authorization_id` |
| `observation_digest` | Digest of the complete canonical observation |
| `status` | `PASS` for `APPROVED`; `FAIL` for `REJECTED` |
| `scope_identity` | Exact Safe V1 scope identity |
| `observed_at` | `simulation_reference_time` |
| `valid_from` | Result `valid_from` |
| `valid_until` | Result `valid_until` |
| `contract_version` | Safe V1 result contract version |
| `risk_governor_version` | Policy snapshot value |
| `capital_authorization_version` | Policy snapshot value |
| `reason_codes` | Result reason codes |
| `unknown_reasons` | Empty for approval; applicable unknown-state reasons for rejection |

This is a value-preserving handoff, not a second authorization. P07-T01 must
still validate the complete P06 digest, complete scope, validity window,
simulation reference time, observation digest, and its other input contracts.

Safe V1 never uses `NOT_REQUIRED` for the required paper-entry path. An absent,
malformed, stale, contradictory, or unknown authorization is not equivalent
to no authorization requirement.

An approved observation admits only the one identity-linked P07 lifecycle. P07
may still reject, fail, or mark its lifecycle unavailable because of its own
execution observation, simulation configuration, initial paper state, replay
identity, fill rules, or reconciliation rules.

## 8. Closed reason vocabulary

The Safe V1 result uses only these reason codes.

### 8.1 Required material, contract, and identity

```text
MISSING_REQUIRED_INPUT
INVALID_INPUT
UNSUPPORTED_VERSION
NON_CANONICAL_INPUT
DIGEST_MISMATCH
PROVENANCE_LINKAGE_FAILURE
CONTRADICTORY_INPUT
SCOPE_MISMATCH
```

### 8.2 P05/P06 admission

```text
P05_HARD_RISK_NOT_ELIGIBLE
P06_NO_TRADE
P06_UNCERTAIN
P06_INVALIDATED
P06_ACTION_NOT_ALLOWED
P06_ENTRY_POSTURE_NOT_ALLOWED
```

### 8.3 Temporal and state

```text
REFERENCE_TIME_INVALID
POLICY_NOT_YET_VALID
POLICY_EXPIRED
POLICY_STATE_STALE
POLICY_STATE_FUTURE_DATED
RISK_STATE_BLOCKED
RISK_STATE_UNKNOWN
PAPER_CAPITAL_STATE_UNKNOWN
PAPER_EXPOSURE_STATE_UNKNOWN
PAPER_OBSERVATION_UNAVAILABLE
```

### 8.4 Virtual-paper limits

```text
PAPER_UNIT_INVALID
PAPER_ENTRY_AMOUNT_INVALID
PAPER_ENTRY_LIMIT_EXCEEDED
PAPER_BUDGET_EXCEEDED
PAPER_EXPOSURE_LIMIT_EXCEEDED
```

### 8.5 Replay and duplicate identity

```text
DUPLICATE_LIFECYCLE_CONFLICT
REPLAY_IDENTITY_CONFLICT
```

No provider-specific, exchange-specific, venue-specific, wallet-specific,
settlement-specific, accounting-specific, P&L-specific, or
classification-specific reason is part of Safe V1.

## 9. Reason aggregation and primary precedence

The evaluator records all independently established reason codes that are
applicable, removes duplicates after validation, and emits them in the fixed
contract order below. It selects exactly one `primary_reason_code`: the first
applicable code in the lowest-numbered group.

| Precedence | Group and order |
|---:|---|
| 1 | `MISSING_REQUIRED_INPUT`, `INVALID_INPUT` |
| 2 | `UNSUPPORTED_VERSION`, `NON_CANONICAL_INPUT` |
| 3 | `DIGEST_MISMATCH`, `PROVENANCE_LINKAGE_FAILURE` |
| 4 | `CONTRADICTORY_INPUT`, `SCOPE_MISMATCH` |
| 5 | `DUPLICATE_LIFECYCLE_CONFLICT`, `REPLAY_IDENTITY_CONFLICT` |
| 6 | `REFERENCE_TIME_INVALID`, `POLICY_NOT_YET_VALID`, `POLICY_EXPIRED`, `POLICY_STATE_STALE`, `POLICY_STATE_FUTURE_DATED` |
| 7 | `P05_HARD_RISK_NOT_ELIGIBLE`, `P06_NO_TRADE`, `P06_UNCERTAIN`, `P06_INVALIDATED`, `P06_ACTION_NOT_ALLOWED`, `P06_ENTRY_POSTURE_NOT_ALLOWED` |
| 8 | `RISK_STATE_BLOCKED`, `RISK_STATE_UNKNOWN`, `PAPER_CAPITAL_STATE_UNKNOWN`, `PAPER_EXPOSURE_STATE_UNKNOWN`, `PAPER_OBSERVATION_UNAVAILABLE` |
| 9 | `PAPER_UNIT_INVALID`, `PAPER_ENTRY_AMOUNT_INVALID`, `PAPER_ENTRY_LIMIT_EXCEEDED`, `PAPER_BUDGET_EXCEEDED`, `PAPER_EXPOSURE_LIMIT_EXCEEDED` |

Within a group, the listed order is the tie-breaker. `reason_codes` are not
ordered by discovery order, mapping order, exception order, timing, or caller
preference.

Malformed, unsupported, tampered, or contradictory input must never be
demoted to an ordinary limit rejection. No reason code is permission to retry
or bypass the authority.

## 10. Canonical identity, serialization, and digests

### 10.1 Canonical serialization

The policy snapshot, result, and materialized P07 observation use the project's
deterministic representation rules:

- mappings have sorted string keys;
- every allowed field is explicit;
- unknown fields are rejected;
- tuples are serialized as ordered arrays;
- sets are forbidden;
- text is trimmed, non-empty where required, and UTF-8;
- enum values use their explicit wire values;
- timestamps are timezone-aware UTC values in one canonical ISO-8601 form;
- decimal amounts are finite normalized decimal text;
- nullable values are serialized as `null`, never omitted;
- non-string keys, opaque objects, callbacks, NaN, infinity, and binary
  floating-point amount values are rejected; and
- SHA-256 is computed over compact UTF-8 JSON with sorted keys and no
  additional whitespace.

Equivalent canonical values must have equal semantic representations and equal
digests. Version fields are included in digest material.

### 10.2 Input digests

`policy_snapshot_digest` covers every canonical policy-snapshot field except
itself. Every nested `state_digest` covers the complete canonical state it
identifies. Supplied digests must be verified against the supplied values
before a top-level digest is accepted.

The complete P06 object remains the source of truth. The evaluator verifies:

```text
policy_snapshot.decision_intent_digest == DecisionIntent.digest
policy_snapshot.context_digest == DecisionIntent.context_digest
policy_snapshot.scope_identity.candidate_id == DecisionIntent.candidate_id
policy_snapshot.scope_identity.chain_id == DecisionIntent.chain_id
policy_snapshot.scope_identity.token_identity == DecisionIntent.token_identity
```

The exact P06 context linkage must also agree with the context preserved by the
intent. The evaluator does not construct a substitute intent from snapshot
fields.

### 10.3 Result identity and digest

`authorization_id` is deterministic and lifecycle-specific. `result_digest`
covers every other canonical result field, including:

- status and fixed authority effect;
- lifecycle and scope identity;
- P06 and policy digests;
- policy identity and validity;
- primary and complete reason sets;
- contract and evaluator versions; and
- bounded provenance.

The result digest is an integrity check, not a replacement for or authority
over its source fields.

### 10.4 Null and ordering rules

Required nullable fields are represented explicitly as `null`. A missing
required field and an explicit null are not interchangeable. Ordered tuples
retain their semantic order. Reason collections are deduplicated only after
validating each member, then ordered by the fixed reason precedence. Identity
and mapping order cannot be changed by caller insertion order.

## 11. Temporal cutoff and validity rules

`simulation_reference_time` in the policy snapshot is the only Safe V1 cutoff.
It is supplied data. The evaluator must never call a system clock or derive a
cutoff from process time, local timezone, filesystem time, ingestion order,
network timing, or later-arriving data.

All of the following must hold:

```text
P06 context.reference_time <= DecisionIntent.decision_time
DecisionIntent.decision_time <= simulation_reference_time
valid_from <= simulation_reference_time <= valid_until
risk_state.observed_at <= risk_state.available_at
risk_state.available_at <= simulation_reference_time
paper_capital_state.observed_at <= paper_capital_state.available_at
paper_capital_state.available_at <= simulation_reference_time
paper_exposure_state.observed_at <= paper_exposure_state.available_at
paper_exposure_state.available_at <= simulation_reference_time
```

The evaluator rejects:

- missing or timezone-naive timestamps;
- future-dated values;
- a policy not yet valid at the reference time;
- an expired policy;
- state that became available after the reference time;
- state stale under the explicit policy validity rules; and
- a P06 context or decision that occurs after the reference time.

No timestamp may be silently normalized in a way that changes its instant.
All accepted timestamps are represented in the one canonical UTC form.

## 12. Replay, duplicate, and contradiction rules

The evaluator is stateless. Safe V1 introduces no registry, database, cache,
queue, persistence layer, retention store, or external duplicate lookup.

1. Re-evaluating the same canonical P06 intent, the same canonical policy
   snapshot, the same `paper_lifecycle_id`, and the same reference time is an
   exact replay. It must produce the same status, reason codes,
   `authorization_id`, canonical representation, and result digest.
2. A different policy digest, intent digest, scope, lifecycle identity, or
   reference time produces a different authorization identity. It is never
   silently treated as the same replay.
3. Repeated or conflicting lifecycle identities, digests, scopes, timestamps,
   statuses, or duplicated fields within the two supplied immutable values are
   rejected. The evaluator never resolves a conflict using freshness,
   insertion order, caller preference, or result magnitude.
4. A duplicate or replay conflict explicitly represented in the supplied
   immutable material produces `DUPLICATE_LIFECYCLE_CONFLICT` or
   `REPLAY_IDENTITY_CONFLICT` according to the fixed precedence.
5. In the absence of explicit conflicting material, repeated evaluation is
   stateless replay, not an inferred duplicate failure.
6. An approved result is valid only for its exact lifecycle and scope. It
   cannot be copied to another lifecycle or used as a generic policy token.

Future deduplication, retention, or lifecycle registry behavior requires a
separate specification and authorization.

## 13. Fail-closed requirements

The authority fails closed for every missing, invalid, stale, unsupported,
contradictory, future, unavailable, tampered, duplicate-conflicting, or
out-of-policy condition.

It must not:

- fill missing fields with defaults;
- convert unknown to pass;
- convert unavailable to zero;
- use a failed P05/P06 state as approval;
- refresh a stale snapshot;
- fetch newer data;
- repair a digest or provenance mismatch;
- choose one value from contradictory inputs;
- infer a paper budget from score, confidence, expected edge, or narrative;
- infer exposure from a missing state digest;
- bypass required authorization with `NOT_REQUIRED`;
- reinterpret rejection as a reduced allocation;
- use a fallback policy or second evaluator;
- retry a provider or external endpoint; or
- mutate either input or any P07 value.

No rejection output may be interpreted as permission for another lifecycle, a
different scope, a live action, or a later phase.

## 14. Explicit authority exclusions

### 14.1 No provider or external data

There is no network, provider, exchange, venue, RPC, API, chain, order-book,
quote, liquidity, wallet, custody, or external-account dependency.

P06/P07 identity and provenance labels such as `chain_id`, token identity, and
source labels may be preserved as supplied values. They do not select or
integrate a chain, provider, venue, or data source.

### 14.2 No account, wallet, signer, or custody authority

The authority must not read or write:

- account, bank, or custody balances;
- wallet positions or permissions;
- private keys or seed phrases;
- signer state;
- transaction payloads;
- signing or broadcast state; or
- external capital.

The only amounts in Safe V1 are virtual paper amounts in one declared
simulation-only unit.

### 14.3 No order or execution authority

The result contains no order side, price, route, order quantity, execution
request, quote, transaction, fill, cancellation, retry, or submission
operation.

`requested_entry` is a paper-policy amount used only for virtual limit checks.
It is not an order quantity, not a notional instruction, and not an execution
request.

### 14.4 No economic authority

The authority does not own or produce:

- execution or fill truth;
- settlement or realization;
- realized P&L;
- accounting, cost basis, proceeds, or cash;
- valuation as settlement;
- ROI, numeraire, conversion, or economic result; or
- `WIN`, `LOSS`, `BREAKEVEN`, or another performance classification.

Virtual paper budget and exposure predicates are admission controls only.

## 15. Ownership boundaries

### 15.1 P05

P05 owns normalized opportunity and hard-risk viability. Its
`ELIGIBLE`, `DISQUALIFIED`, and `INSUFFICIENT_EVIDENCE` outcomes remain
authoritative for that boundary. Safe V1 consumes the preserved result and
rejects every non-eligible state.

Safe V1 does not re-run safety evidence, change hard-risk flags, replace P05
provenance, or convert viability into an order or economic result.

### 15.2 P06

P06 owns deterministic analytical evaluation and the immutable
`DecisionIntent`, including action, posture, assumptions, uncertainty,
invalidation, confidence, and upstream provenance.

Safe V1 is independent of P06 and higher authority for paper admission. It
must not mutate, regenerate, rank, compare, or reinterpret the intent.

### 15.3 P07

P07 owns the paper-simulation lifecycle after independently authorized
admission. P07-T01 validates the supplied observation and all other input
material; later P07 boundaries own hypothetical fills, state, ledger,
reconciliation, canonical paper results, and local history.

P07 does not create, evaluate, renew, upgrade, or override Safe V1. P07 may
still reject or fail a lifecycle for its own input, state, observation,
configuration, or replay conditions.

### 15.4 G1

G1 remains a separately governed simulation-only recognition boundary. It may
recognize a complete paper lifecycle under its own approved semantics, but it
does not create Risk/Capital Authorization and cannot turn paper admission or
a paper result into external execution, settlement, or realized economics.

Safe V1 does not create, modify, or substitute for G1.

### 15.5 G2

G2 owns future realization eligibility and the governed distinction between
execution, settlement, and realization. Safe V1 emits no G2 eligibility,
settlement assertion, endpoint selection, or external evidence.

G2 must not infer realization from an approved authorization, paper fill,
paper position, paper ledger, reconciliation, or P07 finalized result.

### 15.6 G3

G3 owns future accounting and canonical economic-result calculation, including
costs, fees, basis, numeraire, conversion, precision, rounding, and realized
P&L. Safe V1 calculates none of these.

### 15.7 G4

G4 owns future performance classification and its approved vocabulary. Safe V1
does not emit, infer, or prepare `WIN`, `LOSS`, `BREAKEVEN`, or any other
classification.

### 15.8 P09

P09 remains the separately governed live execution chain:

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

## 16. Future implementation and focused test paths

The following are paths only. They must not be created from this document.

### 16.1 Proposed implementation path

```text
core/risk/paper_risk_capital_authorization.py
```

The proposed file would contain only the immutable Safe V1 policy snapshot,
immutable authorization result, deterministic pure evaluator, canonicalization
and digest validation, reason precedence, and value-preserving P07 observation
materialization.

An export change, fixture, API route, worker, database, migration, cache,
persistence layer, provider adapter, wallet module, signer module, execution
module, G1–G4 module, P08-T07 module, or P09 module is not in scope unless a
later authorization names it explicitly.

### 16.2 Proposed focused test path

```text
tests/test_paper_risk_capital_authorization.py
```

The future focused suite must prove:

1. valid immutable `BUY + WAIT` approval for one exact lifecycle;
2. P05 non-eligible, P06 `NO_TRADE`, uncertainty, invalidation, action, and
   posture rejection;
3. missing, malformed, non-canonical, unsupported, tampered, stale, future,
   unavailable, and contradictory input rejection;
4. exact P06/context/candidate/chain/token/portfolio/lifecycle linkage;
5. virtual budget, single-entry, and exposure formulas below, at, and above
   their limits;
6. blocked risk, unknown risk, emergency stop, and unknown paper-state
   behavior;
7. stable primary-reason precedence and canonical reason ordering;
8. nested immutability, canonicalization, and digest determinism;
9. replay identity stability and duplicate/conflicting-identity behavior;
10. explicit reference-time behavior with no ambient clock;
11. exact `APPROVED` → P07 `PASS` and `REJECTED` → P07 `FAIL` mapping;
12. rejection of `NOT_REQUIRED` as a required-entry bypass; and
13. absence of provider, account, wallet, signer, order, execution, settlement,
    accounting, realized P&L, classification, G1–G4, and P09 behavior.

Existing P05, P06, and P07 tests remain regression coverage and must not be
modified by Safe V1 unless a separately approved contract change names those
files.

## 17. Separate authorization gates

No implementation or test file may be created until all of these gates pass.

### Gate 1 — Specification approval

The project owner must approve:

- the exact two-input contract and every required field;
- virtual-paper units and the exact limit formulas;
- `BUY + WAIT` as the only admitted action/posture;
- result fields and contract/evaluator versions;
- reason vocabulary and primary precedence;
- cutoff, validity, replay, duplicate, and contradiction rules;
- P07 handoff semantics; and
- the complete forbidden-authority list.

### Gate 2 — Formal boundary audit

The completed specification must be audited against:

- P05 hard-risk and provenance ownership;
- P06 `DecisionIntent` immutability and non-authority;
- P07-T01 authorization observation and temporal validation;
- P07 paper-only ownership;
- G1 simulation-only recognition;
- blocked G2 and unauthorized G3/G4;
- P09 live-execution separation; and
- the no-provider, no-wallet, no-account constraint.

### Gate 3 — Limited implementation authorization

A separate authorization must name the exact allowed files. The default
candidate is only:

```text
core/risk/paper_risk_capital_authorization.py
tests/test_paper_risk_capital_authorization.py
```

Any export, fixture, documentation, integration, P07, G1–G4, or P09 change
requires explicit addition to that authorization.

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

Future implementation is acceptable only if:

1. it accepts exactly one validated P06 intent and one validated immutable
   paper policy snapshot;
2. it produces only `APPROVED` or `REJECTED` admission;
3. `APPROVED` is possible only for one exact `BUY + WAIT` lifecycle scope;
4. virtual-paper risk, budget, entry, and exposure checks are explicit and
   reproducible;
5. every non-approval condition fails closed;
6. input, output, and P07 observation canonical representations and SHA-256
   digests are stable;
7. reason aggregation and primary-reason precedence are deterministic;
8. identical canonical inputs replay identically without a clock or external
   state;
9. duplicate and contradiction behavior uses no hidden persistence;
10. the P07 mapping is value-preserving and cannot use `NOT_REQUIRED` as a
    required-entry bypass;
11. no provider, account, wallet, signer, real order, execution, settlement,
    P&L, accounting, valuation, ROI, or classification authority exists; and
12. the exact implementation and test paths were separately authorized before
    creation.

## 19. Final governance decision

The Safe V1 Risk/Capital Authority is specified as:

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

It is deterministic, immutable, explainable, point-in-time, provider-neutral,
paper-first, and fail closed. It does not use an ambient clock, provider data,
account balances, wallets, signers, real orders, execution, settlement,
realized P&L, accounting, valuation, ROI, cost basis, numeraire, or
classification.

It does not replace P05, P06, P07, G1, G2, G3, G4, P08-T07, or P09.

```text
Risk/Capital Authority specification = COMPLETE / AWAITING FORMAL AUDIT
Risk/Capital Authority implementation = NOT AUTHORIZED
G2/G3/G4/P09 = NOT AUTHORIZED
paper entry approval = not produced by runtime
```

No source code, tests, dependencies, APIs, workflows, providers, wallets,
signers, broadcast paths, settlement endpoints, live-trading capability,
G1–G4 behavior, P08-T07 behavior, P09 behavior, or runtime authorization is
created or enabled by this specification.