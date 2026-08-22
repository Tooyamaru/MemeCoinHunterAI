# P07-T03 — Paper Position / Exposure State Transition Contract

**Status:** SPECIFICATION CORRECTED — AUDITED PASS — IMPLEMENTATION NOT
AUTHORIZED  
**Phase:** P07 — Paper Trading Engine  
**Task:** P07-T03 — Paper Position / Exposure State Transition Contract  
**Contract:** `p07-t03-v1`  
**Nature:** Immutable, provider-neutral, deterministic paper-state transition
only

## 1. Purpose

P07-T03 defines the bounded transition from one accepted P07-T02
`PaperFillOutcome` and one immutable paper position/exposure state to one
immutable next state.

It records the hypothetical accounting consequence of a paper fill. It does
not execute a trade, authorize capital, persist a record, reconcile against a
venue, or claim that any wallet or on-chain position changed.

The transition is simulation state derivation, not a ledger. A later ledger or
reconciliation boundary may consume the resulting state by identity, but is
not defined or implemented here.

## 2. Architectural position

```text
P07-T01 PaperSimulationInput
        ↓
P07-T02 PaperFillOutcome
        ↓
P07-T03 Paper Position / Exposure State Transition
        ↓
future P07 ledger / reconciliation boundaries
```

T03 consumes exactly one immutable pre-transition state and exactly one
immutable T02 outcome. It produces exactly one immutable transition result.
It owns no state outside the supplied values and the returned value.

## 3. Scope

This specification defines:

- immutable paper position state;
- immutable exposure state;
- deterministic BUY and SELL quantity effects;
- full and partial-fill effects;
- failed, rejected, unavailable, and invalid outcome behavior;
- insufficient-inventory behavior;
- quantity and accounting conservation;
- cost-basis semantics;
- exposure derivation and UNKNOWN preservation;
- timestamp, reference-time, and stale/future rules;
- bounded provenance and canonical deterministic digest;
- validation and fail-closed behavior;
- authority and forbidden-ownership boundaries; and
- focused verification requirements for a later implementation.

This specification does not define:

- a database, durable state store, cache, queue, or migration;
- a paper ledger or journal;
- reconciliation or venue truth;
- a wallet, RPC, DEX, provider, signing, broadcast, or live execution;
- risk or capital authorization;
- P06 decision logic, ranking, optimization, learning, or AI/LLM behavior; or
- a policy for carrying an unfilled remainder after the transition.

## 4. Required input boundary

The eventual implementation must consume:

1. one accepted `PaperFillOutcome` from P07-T02;
2. one immutable `PaperPositionExposureState` representing the state before
   the outcome; and
3. one explicit target asset-identity linkage;
4. one explicit point-in-time valuation context;
5. one explicit accounting context for absolute fee amounts; and
6. one explicitly supplied transition reference time.

The T02 outcome is consumed by identity and verified by its canonical digest.
T03 must not reconstruct an outcome from fields, replace it with a newer
observation, or recompute fill behavior.

The pre-transition state is consumed by identity and verified by its state
digest. T03 must not silently create an initial balance, infer inventory from a
missing position, refresh prices, or recover missing provenance.

The transition reference time is input data. T03 must never read the system
clock.

### 4.1 Boundary-repair inputs

The following are explicit T03 inputs. They are not reconstructed from T02
fields and do not require changing the approved T02 contract:

- `target_asset_identity`: the canonical asset identity of exactly one target
  position. Matching by symbol, display name, provider label, or position
  order is forbidden.
- `valuation_context`: an immutable bounded tuple of valuation observations,
  each containing the exact `asset_identity`, observation ID and digest,
  observed and available timestamps, finite `price`, `price_unit`,
  `valuation_status`, source contract version, and bounded provenance.
- `accounting_context`: an immutable bounded value containing absolute
  quote-denominated `fee_amount` and `priority_fee_amount`, their common
  `fee_unit`, observation identity/digest, accounting contract version, and
  bounded provenance. These are amounts, not rates.

The caller supplies these values from an approved, point-in-time,
provider-neutral context. T03 validates identity, digest, units, timestamps,
freshness, and provenance; it does not fetch, infer, convert, or replace them.

## 5. Contract identity and top-level result

The eventual immutable value object is named `PaperStateTransitionResult`.
Its canonical top-level fields are:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `contract_version` | canonical text | yes | Must be `p07-t03-v1` |
| `transition_status` | enum | yes | `APPLIED`, `NO_CHANGE`, `REJECTED`, `UNAVAILABLE`, or `INVALID` |
| `transition_reference_time` | UTC timestamp | yes | As-of boundary supplied to T03 |
| `prior_state` | state value | yes | Immutable state before this outcome |
| `outcome_identity` | outcome identity | yes | Verified T02 outcome linkage |
| `next_state` | state value or `null` | yes | New state only when transition is applied |
| `quantity_effect` | bounded effect value | yes | Applied or attempted quantity effect |
| `accounting_effect` | bounded effect value | yes | Applied or attempted cost/proceeds effect |
| `exposure_effect` | bounded effect value | yes | Applied or attempted exposure effect |
| `reason_codes` | sorted tuple of canonical text | yes | Stable bounded status explanations |
| `provenance` | bounded canonical mapping | yes | Source identities and versions |
| `transition_digest` | lowercase SHA-256 text | derived | Digest of all other canonical fields |

`next_state` is `null` for `REJECTED`, `UNAVAILABLE`, and `INVALID`. For
`NO_CHANGE`, it is the same canonical state value as `prior_state`; no new
position quantity or accounting effect is applied. No non-success result may
report a successful state change.

The serialized result must contain no fields outside this specification.
Unknown fields are rejected rather than ignored. `transition_digest` is
derived and cannot override its canonical source fields.

## 6. State model

### 6.1 Paper position state

`PaperPositionState` represents one asset within a bounded portfolio scope.
Its canonical fields are:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `asset_identity` | canonical bounded identity | yes | Chain and asset identity |
| `quantity_unit` | canonical text | yes | Unit for asset quantity |
| `quantity` | finite canonical decimal | yes | Non-negative held quantity |
| `cost_basis_unit` | canonical text | yes | Unit of total carrying cost |
| `total_cost_basis` | finite canonical decimal | yes | Non-negative carrying cost |
| `average_cost` | finite canonical decimal or `null` | yes | Cost per held unit |
| `position_quality` | `PASS`, `UNKNOWN`, or `INVALID` | yes | State quality |
| `position_provenance` | bounded canonical mapping | yes | Source and derivation context |

A zero-quantity position has `total_cost_basis = 0` and
`average_cost = null`. A positive quantity requires a finite, non-negative
total cost basis and has `average_cost = total_cost_basis / quantity`, rounded
under the transition contract's canonical policy. Negative quantity and
negative cost are invalid. T03 does not support short positions, borrowing, or
negative inventory.

The state may represent multiple assets, but the transition must change only
the position matching the T02 outcome's `side` and asset identity. Other
positions are copied canonically and unchanged.

### 6.2 Exposure state

`PaperExposureState` represents informational exposure derived from the
position state and explicitly supplied valuation observations. Its canonical
fields are:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `portfolio_scope` | canonical bounded identity | yes | Scope of the exposure |
| `asset_exposures` | ordered tuple | yes | Per-asset exposure observations |
| `gross_quantity_exposure` | finite canonical decimal or `null` | yes | Quantity aggregate where units agree |
| `gross_notional_exposure` | finite canonical decimal or `null` | yes | Marked notional where valuation is known |
| `valuation_status` | `PASS`, `UNKNOWN`, or `INVALID` | yes | Completeness of valuation |
| `exposure_provenance` | bounded canonical mapping | yes | Price and state provenance |

Each asset exposure preserves asset identity, quantity, valuation price or
`null`, price unit, notional or `null`, valuation timestamp, and quality.
Different asset or quote units must not be added together. When a required
valuation is absent, stale, future, contradictory, or UNKNOWN, the affected
notional remains `null` and the aggregate valuation status is `UNKNOWN`; T03
must not substitute zero or infer a price.

Exposure is descriptive paper information only. It is not a risk limit,
capital authorization, portfolio permission, or Risk Governor decision.

### 6.3 Complete paper state

`PaperPositionExposureState` is the immutable aggregate:

| Field | Type | Required |
|---|---|---:|
| `state_id` | canonical text | yes |
| `state_version` | canonical text | yes |
| `portfolio_scope` | canonical bounded identity | yes |
| `positions` | canonical ordered tuple | yes |
| `exposure` | `PaperExposureState` | yes |
| `as_of_time` | UTC timestamp | yes |
| `state_quality` | `PASS`, `UNKNOWN`, or `INVALID` | yes |
| `state_provenance` | bounded canonical mapping | yes |
| `state_digest` | lowercase SHA-256 text | derived |

Positions are uniquely keyed by canonical asset identity and ordered by that
identity in canonical form. Duplicate asset identities are contradictory and
invalid. A state digest covers every canonical state field except itself.

`UNKNOWN` is retained at the state, position, or exposure level. It is never
converted into a known quantity, zero balance, valid valuation, or successful
transition.

## 7. Outcome identity and acceptance

T03 must verify at minimum:

- `outcome_digest` and the T02 canonical representation;
- `contract_version`, fill-model version, and friction-model version;
- side, asset identity, quantity units, and simulation identity;
- `p07_t01_input_digest`, replay identity, and observation identity;
- outcome status and reason codes;
- quantity conservation already required by T02; and
- all timestamps against the transition reference time.

The explicit `target_asset_identity` input must match exactly one prior
position. The T02 outcome has no asset-identity field, so T03 must not claim
that identity was supplied by T02 or derive it from a symbol, display name,
provider label, or position order. Missing, duplicate, or contradictory target
linkage is `INVALID`.

The outcome's `quantity_unit` must match the target position's
`quantity_unit`. A mismatch is `INVALID`.

Only `FILLED` and `PARTIALLY_FILLED` outcomes with positive filled quantity
are eligible to apply a state change. `PARTIALLY_FILLED` applies only its
`filled_quantity`; its remaining quantity is not applied, cancelled, retried,
or carried forward by T03. The remainder remains visible in the T02 outcome.

## 8. Deterministic state transition

For identical canonical prior state, outcome, and transition reference time,
T03 must produce identical canonical result, status, effects, next state, and
digest.

The transition is pure and atomic:

1. validate every input and temporal relationship;
2. classify the outcome;
3. compute effects from the filled quantity only;
4. compute the candidate target position and derived exposure;
5. validate conservation, units, and accounting invariants;
6. return one complete immutable result; or
7. return a non-success result with no applied next-state mutation.

No partial mutation is observable if any step fails. Input state and outcome
objects remain unchanged.

### 8.1 BUY effect

For a valid successful BUY:

- target quantity increases by `filled_quantity`;
- quote-denominated acquisition cost increases by
  `filled_quantity * effective_price` plus applicable quote-denominated fees
  and priority fees;
- prior carrying cost is retained;
- new total cost basis equals prior total cost basis plus acquisition cost;
- new average cost is derived from new total cost basis divided by new quantity;
  and
- the position must remain non-negative and internally consistent.

The T02 `effective_price` is authoritative for trade value. T02
`FrictionComponents.fees` and `FrictionComponents.priority_fees` are not used
as accounting amounts by T03: the approved T02 contract does not specify
whether they are absolute amounts or rates. T03 instead requires the explicit
`accounting_context` in Section 4.1. Missing, UNKNOWN, incompatible, or
contradictory effective price, absolute fee amount, or unit produces
`UNAVAILABLE` or `INVALID` as applicable; T03 does not assume zero cost.

### 8.2 SELL effect

For a valid successful SELL:

- target quantity decreases by `filled_quantity`;
- filled quantity must not exceed prior known inventory;
- the quantity effect is applied only to the filled quantity;
- the cost removed from carrying basis is
  `filled_quantity * prior_average_cost`;
- remaining total cost basis equals prior total cost basis minus removed cost;
- proceeds equal `filled_quantity * effective_price` less the absolute
  quote-denominated fees and priority fees supplied by `accounting_context`;
  and
- when quantity reaches zero, total cost basis is exactly zero and average cost
  is `null`.

T03 reports the realized accounting effect as a bounded paper observation. It
does not define tax, settlement, cash-wallet, realized-profit, or ledger
semantics beyond the explicitly calculated quantity, carrying-cost, and
proceeds fields in this transition.

If the prior position has UNKNOWN quantity or cost basis, a SELL cannot
deterministically reduce it and returns `UNAVAILABLE` without a state change.
T03 must not infer inventory from the requested quantity, liquidity, or
notional.

### 8.3 Partial fills

For `PARTIALLY_FILLED`, the formulas above use only `filled_quantity`. The
unfilled quantity remains outside the next state. It must not be added to,
subtracted from, or represented as a hidden open order.

The transition result preserves requested, filled, and remaining quantities and
identifies that only the filled quantity was applied. The outcome's original
quantity conservation remains observable:

`requested_quantity = filled_quantity + remaining_quantity`.

### 8.4 Failed, rejected, unavailable, and invalid outcomes

| T02 status | T03 behavior |
|---|---|
| `FAILED` | `NO_CHANGE`; preserve prior state; preserve failure reasons |
| `REJECTED` | `NO_CHANGE`; preserve prior state; preserve rejection reasons |
| `UNAVAILABLE` | `UNAVAILABLE`; no next-state change; preserve UNKNOWN/unavailable reasons |
| `INVALID` | `INVALID`; no next-state change; preserve invalidity reasons |

No non-success T02 outcome may increase or decrease a position, alter cost
basis, or create a new exposure. A `NO_CHANGE` result is not a successful fill
and does not authorize retry, cancellation, or execution.

## 9. Inventory and conservation invariants

For an applied BUY:

`next_quantity = prior_quantity + filled_quantity`

For an applied SELL:

`prior_quantity = next_quantity + filled_quantity`

For every applied transition:

- `filled_quantity > 0`;
- `filled_quantity <= requested_quantity`;
- `filled_quantity + remaining_quantity = requested_quantity`;
- quantities use the same canonical unit;
- no quantity is negative;
- no SELL quantity exceeds known prior inventory;
- unrelated positions are unchanged;
- the portfolio scope is unchanged; and
- the next state's provenance links to the exact prior state and outcome.

Accounting must conserve the prior carrying basis except for the explicitly
represented BUY acquisition cost or SELL cost removal. Rounding residuals must
be deterministic, bounded, and included in the accounting effect; they may not
silently disappear.

T03 does not create quote-currency cash balances. Fees and proceeds are
reported in their declared units and remain accounting observations until a
future approved ledger/cash-state contract defines ownership.

## 10. Fee and accounting semantics

The approved T02 contract exposes `FrictionComponents.fees` and
`FrictionComponents.priority_fees`, but does not define either field as an
absolute monetary amount, percentage, basis-point rate, or other accounting
representation. T03 MUST NOT reinterpret either field.

T03 accounting uses only the explicit `accounting_context` input. Its
`fee_amount` and `priority_fee_amount` are absolute amounts in the declared
`fee_unit`, apply to the actual `filled_quantity` only, and must be
independently identified, digestible, point-in-time, and provenance-preserving.
The fee unit must equal the position's `cost_basis_unit` and the outcome's
`fee_unit`; no currency conversion is performed.

For BUY, the accounting cost is:

`filled_quantity * effective_price + fee_amount + priority_fee_amount`

For SELL, the accounting proceeds effect is:

`filled_quantity * effective_price - fee_amount - priority_fee_amount`

These are bounded paper accounting observations only. T03 does not create a
cash balance or settle fees. Unknown, unavailable, stale, future, or
contradictory accounting context produces `UNAVAILABLE` or `INVALID`, never a
zero-fee substitute.

## 11. Cost-basis and rounding policy

All quantity, price, fee, proceeds, cost-basis, and exposure values use finite
`Decimal` values. Binary floating-point values, NaN, infinity, implicit
coercion, and unitless arithmetic are invalid.

Unless a later approved version says otherwise, T03 inherits the T02 numeric
policy:

- rounding mode: `ROUND_HALF_EVEN`;
- maximum decimal places: 18;
- quantum: `1e-18`;
- rounding occurs at explicitly defined calculation boundaries, never
  implicitly during serialization; and
- canonical decimal text is normalized and contains no exponent notation.

The required order is:

1. validate and normalize the prior state and outcome;
2. calculate the filled quantity effect;
3. calculate trade value from filled quantity and effective price;
4. add or subtract explicitly applicable fees and priority fees according to
   side;
5. calculate the new carrying basis and average cost;
6. derive exposure from the resulting state and supplied valuation evidence;
7. apply the defined decimal rounding at each approved boundary; and
8. verify conservation after rounding.

Changing units, formulas, cost-basis method, rounding, or calculation order
requires a new contract version and explicit approval.

## 12. Valuation context and exposure derivation

Exposure is derived from the resulting paper positions and the explicit
`valuation_context` T03 input. The observations originate from an approved
provider-neutral market/valuation boundary outside T03. They are supplied by
identity and digest, not fetched or refreshed by T03.

For a position with known quantity and known applicable valuation price:

`notional = quantity * valuation_price`

The applicable observation must match `target_asset_identity` exactly and
preserve its valuation price, price unit, observation ID/digest, availability
time, timestamp, source contract version, and provenance. Valuation timestamps
must be no later than the transition reference time and must satisfy the
versioned freshness requirement supplied by the approved valuation policy.
T03 does not invent a freshness duration; an absent or unsupported freshness
policy is `UNAVAILABLE`.

If valuation is UNKNOWN or unavailable:

- position quantity may still be updated when the fill transition itself is
  fully deterministic;
- notional for that asset remains `null`;
- `valuation_status` is `UNKNOWN`;
- affected reason codes and provenance are preserved; and
- no zero-value substitution is permitted.

If quantity or state identity is UNKNOWN, the affected position transition is
not deterministic and T03 returns `UNAVAILABLE` rather than producing a
permissive exposure.

Exposure does not evaluate limits, correlations, concentration, theme risk,
capital permission, or risk approval. Those remain outside T03.

## 13. Paper position and exposure state quality

The prior state, target position, valuation observations, and accounting
context must each retain quality, identity, timestamp, and provenance. An
applied transition may produce a known quantity with UNKNOWN notional when
valuation alone is UNKNOWN. It may not produce an applied transition when the
target identity, quantity, cost basis, or accounting amount needed for the
transition is UNKNOWN.

The next state's `as_of_time` is exactly `transition_reference_time`; it is
never taken from the local clock or silently advanced beyond the supplied
boundary. The next exposure is derived from the same state transition and
valuation context, without hidden state.

## 14. Temporal and stale-data rules

`transition_reference_time` is the single as-of boundary for the transition.
The following must hold:

- prior state `as_of_time <= transition_reference_time`;
- T02 outcome quote and fill times, when present, are
  `<= transition_reference_time`;
- the T02 simulation reference time is `<= transition_reference_time` and
  must not be silently moved forward;
- valuation observations used for exposure are available by the reference
  time;
- accounting observations used for fees are available by the reference time;
- no required value is future relative to the reference time;
- no required value is outside the approved freshness window;
- timestamp equality is permitted; and
- no timestamp is read from the wall clock.

Stale, future, unavailable, or contradictory state/outcome/valuation material
produces an explicit non-success result. T03 does not backfill, truncate,
refresh, or choose the newest conflicting value.

## 15. Failure, contradiction, and UNKNOWN semantics

Validation must reject or return a typed deterministic non-success result for:

- missing required fields;
- unsupported contract, state, model, or version identities;
- stale or future timestamps;
- mismatched outcome, prior-state, portfolio, asset, or unit identities;
- digest mismatch or tampered canonical material;
- non-canonical text, mappings, timestamps, decimals, or sequences;
- duplicate positions or contradictory exposure entries;
- negative quantities, costs, prices, or impossible accounting;
- SELL inventory insufficiency;
- UNKNOWN required quantity, cost basis, or identity;
- unavailable effective price or required fee information;
- missing, unsupported, ambiguous, stale, future, or contradictory
  asset-identity linkage;
- missing, unsupported, stale, future, or contradictory valuation context;
- missing, unsupported, stale, future, or contradictory accounting context;
- unbounded or unsupported provenance; and
- any arithmetic or conservation violation.

Insufficient SELL inventory is `REJECTED` with a stable
`INSUFFICIENT_INVENTORY` reason and no state change. Unknown inventory is
`UNAVAILABLE` with a stable `INVENTORY_UNKNOWN` reason. These states must not
be conflated.

UNKNOWN remains a first-class state. T03 must preserve UNKNOWN reason codes,
source identity, timestamp, and digest. It must never convert UNKNOWN to
PASS, zero, a valid position, a known exposure, or an applied transition.

## 16. Provenance and replay

Every result must preserve enough immutable provenance to reproduce the
transition, including:

- P07-T01 input digest;
- P07-T02 outcome digest and contract/model versions;
- prior state ID, version, and digest;
- portfolio and asset identities;
- replay ID;
- simulation and transition reference times;
- valuation evidence identity and digest, where applicable;
- target asset-identity linkage;
- accounting context identity, fee amounts, units, and digest;
- state and exposure derivation versions; and
- canonical transition representation and digest.

The next state must include a bounded parent-state identity and the exact
outcome identity that produced it. Provenance is descriptive and does not
grant authority.

No hidden mutable state, process order, local timezone, wall clock, random
value, network retry, provider response, filesystem state, database state, or
external service may affect the deterministic result.

## 17. Canonical representation and digest

Canonicalization must follow the established P07 conventions:

- mappings use sorted string keys;
- positions and asset exposures use explicit deterministic ordering;
- tuples/lists use ordered arrays;
- sets are forbidden;
- timestamps are timezone-aware UTC in one microsecond ISO-8601 form ending in
  `Z`;
- decimals are finite normalized decimal text;
- enum values use explicit wire values;
- nullable fields use `null`, not omission;
- text is non-empty, trimmed UTF-8;
- bounded mappings contain only canonical JSON-compatible values;
- unknown fields, non-string keys, floats, NaN, infinity, and opaque objects
  are rejected; and
- SHA-256 is computed over compact UTF-8 JSON with sorted keys and no
  additional whitespace.

The implementation must expose the canonical representation and deterministic
digest. Equivalent canonical values must have equal digests. The supplied
digest, if any, must be verified after canonicalization and cannot be treated
as authoritative when it disagrees.

## 18. Authority boundaries and forbidden ownership

P07-T03 MUST NOT:

- create, approve, renew, evaluate, or modify Risk / Capital Authorization;
- modify a P06 `DecisionIntent` or any P05/P06 contract;
- create an order, quote, route, execution permission, or retry;
- create a live or paper authorization;
- claim wallet, venue, RPC, DEX, or on-chain state;
- call providers, networks, RPC, DEXs, wallets, signing, or broadcast;
- persist a ledger, journal, database record, cache, queue, or migration;
- reconcile paper state with external or on-chain truth;
- define cash settlement, tax, or live realized-profit authority;
- invoke P08, P09, an LLM, an AI loop, ranking, optimization, or learning; or
- mutate input objects or maintain hidden process-global state.

A successful transition is hypothetical state evidence only. It cannot bypass
the Risk Governor, authorize a later transition, or establish live-readiness.

## 19. Proposed implementation boundary

The following files are proposed only and MUST NOT be created by this
specification task:

| File | Proposed responsibility |
|---|---|
| `core/execution/paper_position_exposure_state.py` | Immutable position, exposure, explicit valuation/accounting context, effect, and transition contracts |
| `core/execution/__init__.py` | Export only the explicitly approved T03 contract and version |
| `tests/test_paper_position_exposure_state.py` | Focused transition, accounting, canonicalization, and fail-closed tests |

No ledger, reconciliation, persistence, database, migration, workflow,
provider, network, RPC, DEX, wallet, signing, broadcast, P08, P09, or other
implementation file is proposed.

## 20. Focused verification requirements

Tests may be created only after explicit implementation authorization. The
focused suite must verify:

1. immutable valid initial state and nested values;
2. valid BUY full-fill quantity and cost-basis transition;
3. valid SELL full-fill quantity, cost removal, and proceeds effect;
4. partial BUY and SELL applying only `filled_quantity`;
5. requested/filled/remaining quantity conservation;
6. zero-position and average-cost invariants;
7. fee and priority-fee unit handling;
8. deterministic rounding and accounting residual behavior;
9. failed, rejected, unavailable, and invalid outcome behavior;
10. insufficient inventory versus UNKNOWN inventory distinction;
11. preservation of unrelated positions and portfolio scope;
12. exposure derivation with known valuation;
13. UNKNOWN valuation preservation without zero substitution;
14. stale, future, missing, unsupported, tampered, non-canonical, and
    contradictory input;
15. identity and digest linkage to the exact T02 outcome and prior state;
16. canonical representation stability across mapping order;
17. deterministic digest and replay stability;
18. state and outcome immutability;
19. no wall-clock dependency or external I/O; and
20. absence of ledger, reconciliation, authorization, wallet, provider, RPC,
    DEX, signing, broadcast, and live-execution behavior.
21. explicit target asset identity rather than symbol/display-name matching;
22. explicit valuation observations, freshness, and UNKNOWN notional;
23. absolute fee accounting context without reinterpretation of T02 friction
    fields.

Verification must remain targeted to the explicitly approved T03
implementation boundary.

## 21. Entry criteria and authorization gate

Implementation may begin only after all of the following are separately
accepted:

- this specification passes architecture and contract audit;
- state and exposure field semantics are approved;
- BUY, SELL, partial-fill, and failure semantics are approved;
- inventory and quantity conservation are approved;
- cost-basis, proceeds, units, and rounding rules are approved;
- UNKNOWN, stale, future, and contradiction behavior is approved;
- provenance, canonicalization, and digest rules are approved;
- the focused verification plan is approved; and
- the exact proposed implementation files receive explicit written
  implementation authorization.

This specification does not authorize implementation. In particular, the
proposed files in Section 19 MUST remain absent until that gate is satisfied.

## 22. Audit record

The specification was internally audited against:

- the P07 master boundary: T03 consumes paper outcomes and produces
  simulation-only state; it does not define ledger or reconciliation;
- P07-T01: input, initial-state identity, reference-time, UNKNOWN,
  provenance, immutability, and canonical digest rules remain aligned;
- P07-T02: only accepted immutable fill outcomes are consumed, T02 quantity
  conservation and friction/accounting inputs are preserved, and T02 remains
  free of position mutation;
- boundary repair: T02 lacks asset identity, valuation context, and explicit
  fee semantics, so T03 now requires each as an explicit input rather than
  modifying or reinterpreting T02;
- Risk / Capital Authorization: no authority is created, evaluated, renewed,
  or overridden;
- P08/P09: no learning or live execution ownership is introduced;
- deterministic/fail-closed requirements: no clocks or external I/O, explicit
  failure statuses, stable reasons, no permissive UNKNOWN conversion; and
- ledger/reconciliation boundaries: no persistence, append/journal semantics,
  external truth, or disagreement resolution is assigned to T03.

Audit result: **PASS**. The three previously identified contract gaps are
explicitly represented as T03 input dependencies. No T02 modification or
implicit fee, asset, or valuation inference is required.

## 23. Governance conclusion

P07-T03 specification: **CORRECTED / COMPLETE / AUDITED PASS**.
P07-T03 implementation: **NOT AUTHORIZED**.

The next recommended step is an explicit human/architecture review of this
document. Only after approval may a separate implementation task authorize the
three proposed files and their focused tests. No implementation, test,
dependency, persistence, ledger, reconciliation, provider, wallet, RPC, DEX,
signing, broadcast, P08, P09, or live-execution work is authorized by this
document.