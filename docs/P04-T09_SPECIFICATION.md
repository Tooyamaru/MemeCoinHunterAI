# P04-T09 — Feature Definition & Calculation Boundary

**Status:** SPECIFICATION READY / IMPLEMENTATION NOT STARTED  
**Phase:** P04 — Market & Signal Intelligence  
**Task:** P04-T09  
**Specification type:** Architecture and implementation specification only  
**Review baseline:** `966ebf4` (the baseline identified by the authoring brief)  
**Provider posture:** Provider-neutral; no external I/O

## 1. Task identity

P04-T09 defines the reusable boundary between accepted point-in-time market
inputs and deterministic feature outputs. It is the first feature-calculation
boundary after the completed P02 market-observation/state/intelligence
contracts and the completed P04 signal-evidence/snapshot contracts.

This document authorizes a narrow implementation proof, not the full P04
feature catalog. No implementation is started or claimed by this document.

## 2. Architectural purpose

The boundary shall make a feature calculation:

- explicit about its definition and version;
- deterministic for the same canonical inputs;
- reproducible from information available at calculation time;
- independent of providers, networks, persistence, prediction, scoring, and
  trading;
- traceable to the accepted evidence and upstream state snapshots it consumed;
- fail-closed when required information is missing, stale, contradictory,
  malformed, or temporally invalid.

The boundary sits conceptually here:

```text
accepted P02 market intelligence observations
    -> feature input validation and canonicalization
    -> deterministic feature calculation
    -> immutable feature result
    -> later point-in-time feature snapshot
```

It does not replace P02 admission, P04 signal-evidence processing, or the
future opportunity/decision boundaries.

## 3. Problem statement

P02-T01 through P02-T09 provide timestamped, quality-aware, provenance-linked
market information and state references. P04-T01 through P04-T07 provide
immutable signal evidence processing and snapshot history. Neither boundary
defines how a numeric market measurement becomes a reusable feature.

Without this boundary, later feature implementations could:

- choose undocumented formulas or units;
- substitute receipt or processing time for observation time;
- mix incompatible market subjects, sources, units, or quote assets;
- use stale or future-dated values;
- silently convert UNKNOWN or malformed input into a number;
- lose the evidence and upstream-state references needed for replay; or
- introduce provider-specific, predictive, scoring, or trading behavior too
  early.

P04-T09 establishes the smallest safe calculation contract before broader
feature work.

## 4. Dependencies

The implementation may consume only already-established local contracts:

1. **P02-T01** data-quality and freshness vocabulary, including
   `DataQuality`, `FreshnessPolicy`, timestamps, and ordering states.
2. **P02-T07** accepted market observation evidence and provenance.
3. **P02-T08** immutable/read-oriented market-state entries and state
   version/digest references.
4. **P02-T09** provider-neutral market-intelligence observations, accepted
   observation results, category contracts, point-in-time fields, and
   upstream state references.
5. **P03** eligibility/safety outputs only as optional gating context; no P03
   value is used in the initial formulas.
6. **P04-T01 through P04-T05** signal evidence contracts only where a future
   adapter needs to carry feature outputs into signal processing. These
   contracts are not numeric inputs to the initial calculations.
7. **P04-T06 and P04-T07** snapshot and history contracts as downstream
   linkage/reference concepts. T09 does not change or require mutation of
   those contracts.
8. Python standard-library numeric, time, immutable-data, and hashing
   facilities already available in the project.

No provider adapter, RPC client, API, database, migration, worker, dependency,
AI service, or network call is a dependency.

## 5. Entry criteria

Implementation of P04-T09 may begin only when all of the following are true:

- P04-T01 through P04-T07 remain complete and closed.
- The implementation is limited to the scope in this document.
- The caller supplies an explicit calculation reference time `T`.
- The caller supplies an explicit freshness policy; no production stale
  threshold is invented by the implementation.
- Every input is an accepted P02-T09 market-intelligence observation whose
  upstream P02-T08 reference is internally consistent.
- The input set identifies one market subject, one source, one price unit, and
  one quote asset.
- The selected feature definition and feature version are known.
- No input requires external I/O or hidden lookup.
- Focused tests described in this document are planned before implementation.

An input that merely has a `PRICE` category but lacks the T09 price profile
metadata is not sufficient for entry.

## 6. Scope

P04-T09 shall implement:

1. A versioned, provider-neutral feature-definition representation.
2. A versioned, immutable feature-calculation result representation.
3. Canonical validation of the narrow price-input profile.
4. Explicit point-in-time and freshness validation.
5. Canonical ordering and duplicate/contradiction checks.
6. Deterministic calculation of:
   - `price_velocity`;
   - `price_acceleration`.
7. Explicit non-success results with reason codes and no feature value.
8. Provenance and upstream snapshot linkage in every result.
9. Canonical representation and digest behavior for reproducibility.
10. Pure/local calculation with no mutation of supplied inputs.
11. Focused tests for all required success and failure paths.

The result is an analytical feature value only. It is not a signal, score,
opportunity, decision, authorization, entry instruction, order, or trade.

## 7. Explicit out-of-scope list

P04-T09 shall not implement:

- transaction-frequency calculation;
- volume, volume acceleration, relative volume, or volume profile;
- buy/sell pressure or flow imbalance;
- liquidity behavior, depth, reserves, pool state, or slippage;
- wallet, holder, funding, social, narrative, or on-chain behavior signals;
- volatility, momentum composites, regime classification, or indicators;
- opportunity scoring, ranking, candidate reduction, or phase detection;
- prediction, machine learning, LLM analysis, or any AI behavior;
- trading logic, entry/exit logic, paper trading, execution, or authorization;
- risk decisions, safety decisions, or a replacement for the Risk Governor;
- provider selection, provider-specific normalization, RPC, DEX, Solana SDK,
  wallet, network, HTTP, filesystem, database, or persistence I/O;
- historical backfill, streaming orchestration, scheduling, retries, or
  source recovery;
- mutation of P02 evidence, P02 state, P04 signal evidence, or P04 snapshots;
- modification of P02/P03/P04 contracts or architecture baseline documents;
- a full P04 feature registry or plugin framework;
- implicit default freshness, unit, quote, or sampling assumptions.

## 8. Initial feature subset

### 8.1 Authorized: price velocity

`price_velocity` is authorized because P02-T09 can represent an accepted
`PRICE` observation with a scalar value, an observation timestamp, a source and
market subject, provenance, and an upstream P02-T08 state reference. T09
narrows that generic representation with explicit numeric, unit, and quote
validation before calculation.

It uses the latest two valid price observations for one subject and one
calculation time.

### 8.2 Authorized: price acceleration

`price_acceleration` is authorized because the same P02-T09 price profile can
provide three ordered price observations and their observation timestamps.
It proves that the same definition/validation/provenance boundary can support
a feature needing more than one interval without introducing a complex feature
family.

It uses the latest three valid price observations for one subject and one
calculation time.

### 8.3 Deferred: transaction frequency

Transaction frequency is **not authorized** in T09. P02-T09 has a
`TRANSACTION_FLOW` category and generic values, but the existing contract does
not define whether a value is a transaction count, event count, window total,
unique transaction count, or a rate; nor does it define the required window
boundaries or deduplication semantics. Counting accepted observations would
measure source-observation frequency, not transaction frequency.

Transaction frequency requires a separately approved input contract that
defines event identity, count semantics, window boundaries, and source
reconciliation. T09 must reject it as unsupported rather than infer any of
those meanings.

### 8.4 Why this is the smallest safe subset

The two authorized features share one simple scalar-price input profile,
require no external data, use explicit timestamps, and have direct
mathematical definitions. They prove both a two-point and a three-point
calculation while keeping the boundary provider-neutral and reproducible.
Transaction frequency and every other proposed family require semantics not
present in the verified upstream contracts.

## 9. Feature mathematical definitions

### 9.1 Notation

For one subject, let the canonical price observations be:

```text
(t0, p0), (t1, p1), (t2, p2)
```

where `t0 < t1 < t2`, each `ti` is the effective observation timestamp in
UTC, and each `pi` is a finite canonical price quantity in the same unit and
quote asset.

Elapsed time is measured in seconds:

```text
Δ01 = seconds(t1 - t0)
Δ12 = seconds(t2 - t1)
Δ02 = seconds(t2 - t0)
```

### 9.2 Price velocity

For the latest two observations:

```text
price_velocity = (p2 - p1) / Δ12
```

The result unit is `price_unit / second`. The feature uses `t1` as the start
of the measured interval and `t2` as the end.

When only two observations are supplied, they are named `(t1, p1)` and
`(t2, p2)` for this formula; no earlier observation is required.

### 9.3 Price acceleration

For the latest three observations, first calculate adjacent interval
velocities:

```text
v01 = (p1 - p0) / Δ01
v12 = (p2 - p1) / Δ12
```

The interval midpoint for `v01` is `(t0 + t1) / 2`; the interval midpoint for
`v12` is `(t1 + t2) / 2`. Their elapsed midpoint time is `Δ02 / 2`.
Therefore:

```text
price_acceleration = (v12 - v01) / (Δ02 / 2)
                    = 2 * (v12 - v01) / Δ02
```

The result unit is `price_unit / second²`. This definition is explicit for
unequally spaced observations and does not assume a fixed sampling interval.

### 9.4 Arithmetic rules

- `Δ01`, `Δ12`, and `Δ02` must be strictly positive.
- Input prices must be finite numeric values; NaN and infinities are invalid.
- The implementation shall use a documented canonical decimal/rational
  conversion for arithmetic, not an undocumented binary-floating comparison.
- The output value shall use one canonical numeric representation and one
  canonical rounding/precision policy declared by the implementation.
- The implementation shall not silently clamp, round away, absolute-value,
  interpolate, extrapolate, or fill a value.
- Any arithmetic failure produces a non-success result with no numeric value.

## 10. Required input contracts

### 10.1 Accepted upstream record

Each input must be an accepted `AcceptedMarketIntelligenceObservation` or an
equivalent immutable T09 input view that preserves all of its required fields.
The input must include:

- `source_id`;
- `chain_id`;
- `token_identity`;
- `market_subject_id`;
- `intelligence_category = PRICE`;
- a scalar `value`;
- `observation_time`;
- `received_time`;
- `reference_time`;
- `data_age`;
- `observation_id`;
- source/provenance metadata;
- `upstream.state_version`;
- `upstream.state_digest`;
- `upstream.contract_version`;
- `quality = VALID`;
- accepted status.

Rejected P02-T09 results, generic objects, raw provider payloads, and
unvalidated mappings are not accepted as feature inputs.

### 10.2 T09 price profile

The P02-T09 generic `PRICE` representation is eligible only when all of the
following are true:

- the category contract declares a scalar value shape;
- the value is a finite numeric scalar accepted by the declared canonical
  numeric policy;
- `observation_metadata.measurement` is the exact value `"price"`;
- `observation_metadata.unit` is a non-empty canonical price-unit identifier;
- `observation_metadata.quote_asset` is a non-empty canonical quote identifier;
- all records in one calculation have identical unit and quote asset;
- all records have the same `(source_id, chain_id, token_identity,
  market_subject_id)`;
- all records have distinct observation identities;
- all records pass timestamp, quality, provenance, and freshness validation.

T09 may require these metadata fields even though P02-T09 permits generic
metadata. Missing semantic metadata is an explicit unsupported/incomplete
input, never an inferred default.

### 10.3 Calculation context

The caller must supply:

- calculation reference time `T`;
- an explicit `FreshnessPolicy`;
- the feature identifier and feature version;
- the upstream input snapshot/state references;
- a deterministic calculation/evaluation identifier if the surrounding caller
  uses one.

`processing_time` may be recorded for audit but shall not replace `T` or an
observation timestamp in feature arithmetic.

## 11. Point-in-time semantics

A feature calculated at reference time `T` may use only information available
at `T`.

For every input:

```text
observation_time <= T
received_time <= T
```

The effective market fact is `observation_time`. `received_time` is retained
for availability/audit checks and must never be substituted for the event
time. `processing_time` is not an observation time.

An input with `observation_time > T` or `received_time > T` is rejected as
future/unavailable data and cannot contribute to a fallback calculation.
Timestamps equal to `T` are permitted.

## 12. Timestamp rules

- All timestamps must be timezone-aware.
- All timestamps are canonicalized to UTC for comparison and representation.
- `observation_time <= received_time` is required.
- `observation_time <= reference_time` is required.
- `reference_time` must be the explicit reference for the accepted upstream
  observation and must not be synthesized from receipt time.
- Timestamps must be strictly increasing after canonical sorting for every
  interval used by a feature.
- Equal timestamps produce a zero/invalid elapsed interval result; the
  implementation must not choose one record arbitrarily.
- A timestamp with an invalid timezone, impossible relationship, or
  unrepresentable canonical form is invalid input.

## 13. Provenance requirements

Every result, including a non-success result, must preserve:

- feature identifier and feature version;
- calculation reference time `T`;
- input observation IDs;
- input observation timestamps;
- source IDs and market subject identity;
- P02-T09 contract version;
- each upstream P02-T08 state version and digest;
- each upstream P02-T08 contract version;
- price unit and quote asset;
- freshness policy identity/parameters;
- deterministic reason codes;
- an input-set digest and result representation digest.

The successful result must make it possible to identify the exact upstream
evidence and state references from which the value was calculated. A digest
alone is not sufficient if the input references are omitted.

## 14. Freshness requirements

Freshness is evaluated at `T`, not at the time the feature function happens to
run:

```text
data_age_at_T = T - observation_time
```

The supplied `FreshnessPolicy` must be explicit. If `stale_after` is present,
every required input must satisfy:

```text
0 <= data_age_at_T <= stale_after
```

If the policy is absent or cannot be validated, the calculation does not
produce a feature value. No default production threshold is allowed.

## 15. Quality and UNKNOWN handling

The only inputs eligible for a numeric result have `DataQuality.VALID` and
accepted upstream outcomes. `STALE`, `INVALID`, `INCOMPLETE`, `DUPLICATE`,
`OUT_OF_ORDER`, `SOURCE_UNAVAILABLE`, and `CONTRADICTORY` are not valid
numeric inputs.

The result contract shall distinguish at least:

- `CALCULATED` — a valid feature value exists;
- `UNKNOWN` — the value cannot be established because required information is
  missing, stale, unavailable, or contradictory;
- `INVALID` — the request or input violates a structural, numeric, temporal,
  or arithmetic invariant;
- `UNSUPPORTED` — the input category or requested feature is outside T09.

`UNKNOWN` must carry reason codes and a null/no-value field. UNKNOWN must never
be represented as zero, an empty string, a default value, or a valid feature.

## 16. Missing-input behavior

Missing required input produces `UNKNOWN` with an explicit reason:

- fewer than two valid price observations for velocity:
  `INSUFFICIENT_PRICE_OBSERVATIONS`;
- fewer than three valid price observations for acceleration:
  `INSUFFICIENT_PRICE_OBSERVATIONS`;
- absent price unit or quote asset: `MISSING_PRICE_SEMANTICS`;
- absent observation identity or provenance: `MISSING_PROVENANCE`;
- absent upstream state reference: `MISSING_SNAPSHOT_LINK`;
- absent calculation reference time or freshness policy:
  `MISSING_CALCULATION_CONTEXT`.

The implementation must not use a partial subset if the requested formula
requires more observations.

## 17. Stale-input behavior

If any required input is stale at `T`, the result is `UNKNOWN` with
`STALE_INPUT`. The result must preserve the stale input references and the
evaluated age/policy context where available.

The implementation must not:

- drop the stale record and calculate from an older record;
- replace stale observation time with received time;
- use the latest non-stale record as a silent fallback;
- report a stale calculation as valid.

## 18. Contradictory-input behavior

Contradictory input produces `UNKNOWN` with `CONTRADICTORY_INPUT` when the
contradiction is an accepted-data uncertainty, including:

- one observation identity maps to different canonical content;
- the same source/subject/time/unit/quote has different price values;
- upstream identity, provenance, or state digest fields disagree;
- inputs claim incompatible units or quote assets.

No source wins by arrival order. No value is averaged, selected, or silently
discarded. A structural identity or provenance mismatch may instead produce
`INVALID`; the distinction must be deterministic and documented in reason
codes.

## 19. Future-dated/look-ahead protection

Any input with an effective observation time after `T` is rejected with
`FUTURE_OBSERVATION`. Any input received after `T` is rejected with
`NOT_AVAILABLE_AT_REFERENCE_TIME`. The implementation must not calculate from
the remaining inputs after either condition is detected.

Future data must not be hidden by:

- sorting;
- use of received or processing time;
- latest-value selection;
- interpolation or extrapolation;
- a fallback to an earlier feature snapshot.

## 20. Determinism requirements

For the same feature definition version, calculation context, canonical input
set, and freshness policy:

- the result status, reason codes, value, provenance, and digests are identical;
- no wall clock, random value, environment variable, locale, or provider state
  influences the result;
- input list order does not affect a valid result;
- rejected results are deterministic too;
- the same contradictory or duplicate set produces the same reason set;
- no mutation of input objects is observable.

The calculation must be a pure local operation. Re-running it with the same
serialized canonical input produces the same serialized canonical result.

## 21. Canonical representation requirements

The implementation shall define one canonical representation for:

- feature identifier and version;
- subject identity;
- timestamps in UTC ISO-8601 form;
- numeric input values and output value;
- unit and quote identifiers;
- ordered input references;
- freshness policy;
- upstream state references;
- status and sorted unique reason codes.

Canonical input ordering shall be by a stable tuple containing observation
timestamp, observation identity, source/subject identity, and canonical value.
The implementation must validate duplicate and contradiction conditions before
using the order for arithmetic.

Mapping keys must be sorted, sequences must be represented in a fixed order,
and non-finite numeric values must be rejected. The digest must hash only this
canonical representation.

## 22. Versioning requirements

Every feature result must preserve:

- a T09 calculation contract version;
- a feature identifier;
- a feature-definition version;
- the consumed P02-T09 category/contract version;
- the upstream P02-T08 contract version(s).

A change to formula, units, required fields, numeric conversion, rounding,
canonical ordering, freshness semantics, or failure semantics requires a new
feature-definition version. It must not reinterpret an old result in place.

Input contract versions must be compared explicitly. An unsupported version
produces `UNSUPPORTED` or `INVALID` according to the reason category and never
falls through to a presumed compatible behavior.

## 23. Snapshot linkage

T09 does not persist snapshots, but every result must carry an immutable
linkage record containing:

- the calculation reference time `T`;
- the canonical input-set digest;
- every input observation ID;
- every input's upstream P02-T08 state version and digest;
- the P02-T09 contract version;
- the resulting feature representation digest.

When a caller later embeds the feature in a P04-T06/P04-T07 signal snapshot,
the feature linkage must remain an input reference; it must not replace or
rewrite the signal snapshot's own provenance and digest fields.

If a required upstream state reference is missing or mismatched, the feature
result is not calculated. T09 must not manufacture a snapshot ID or claim
historical persistence.

## 24. Error/failure semantics

Expected data conditions must return an immutable non-success result with
status and reason codes; they must not raise an exception as a control-flow
fallback. Examples include missing, stale, future, duplicate, contradictory,
unsupported, and insufficient input.

Programming/type-contract violations that make a result representation
impossible may raise a standard validation error at the boundary, provided
the behavior is deterministic and covered by tests. No exception path may
silently return a numeric feature.

At minimum, reason codes must distinguish:

```text
INVALID_REQUEST
UNSUPPORTED_FEATURE
UNSUPPORTED_CATEGORY
UNSUPPORTED_INPUT_VERSION
MISSING_CALCULATION_CONTEXT
MISSING_PRICE_SEMANTICS
MISSING_SNAPSHOT_LINK
MISSING_PROVENANCE
INSUFFICIENT_PRICE_OBSERVATIONS
STALE_INPUT
FUTURE_OBSERVATION
NOT_AVAILABLE_AT_REFERENCE_TIME
INVALID_TIMESTAMP
INVALID_TIMESTAMP_ORDER
ZERO_ELAPSED_TIME
INVALID_NUMERIC_VALUE
INCOMPATIBLE_PRICE_UNIT
INCOMPATIBLE_QUOTE_ASSET
DUPLICATE_INPUT
CONTRADICTORY_INPUT
UPSTREAM_NOT_ACCEPTED
UPSTREAM_IDENTITY_MISMATCH
ARITHMETIC_FAILURE
```

Reason-code order and deduplication must be canonical.

## 25. Test requirements

Focused tests shall cover, at minimum:

1. deterministic velocity calculation from two valid observations;
2. deterministic acceleration calculation from three valid observations;
3. same inputs producing the same value, status, provenance, and digest;
4. input ordering independence for valid input sets;
5. irregular timestamp intervals using the explicit acceleration formula;
6. timestamp normalization and timestamp relationship validation;
7. point-in-time enforcement at, before, and after `T`;
8. future observation rejection;
9. received-after-`T` rejection without receipt-time substitution;
10. stale-data rejection using an explicit freshness policy;
11. UNKNOWN required-input behavior;
12. missing observation, provenance, unit, quote, and snapshot-link behavior;
13. contradictory identity/content behavior;
14. exact duplicate input behavior;
15. out-of-order input behavior and canonical sorting;
16. equal timestamps and zero elapsed-time behavior;
17. malformed, non-finite, and unsupported numeric values;
18. incompatible units and quote assets;
19. rejected upstream quality/status behavior;
20. provenance preservation for success and failure results;
21. upstream P02-T08 state version/digest preservation;
22. input-set and result digest reproducibility;
23. feature-definition and contract-version preservation;
24. upstream immutability after calculation;
25. no network, provider, database, filesystem, or environment I/O;
26. explicit rejection of transaction frequency and all out-of-scope inputs.

Tests must assert that UNKNOWN never has a numeric feature value and that
failure does not mutate any supplied evidence or snapshot object.

## 26. Acceptance criteria

P04-T09 is a PASS only if every criterion below passes:

- [ ] A versioned feature-definition boundary exists for the two authorized
      features only.
- [ ] The input profile accepts only accepted, provenance-linked P02-T09
      scalar price observations with explicit numeric semantics.
- [ ] Price velocity matches the formula in section 9.2.
- [ ] Price acceleration matches the formula in section 9.3, including
      irregular intervals.
- [ ] All required timestamp, freshness, identity, unit, quote, and
      upstream-reference checks are explicit.
- [ ] Future and not-yet-available inputs cannot influence a result.
- [ ] Missing, stale, contradictory, duplicate, malformed, unsupported, and
      insufficient inputs never yield a valid numeric value.
- [ ] UNKNOWN is preserved as a non-success state with deterministic reasons.
- [ ] Results preserve input evidence references, provenance, versions,
      upstream state links, calculation time, and canonical digests.
- [ ] Same canonical inputs produce byte-equivalent canonical results.
- [ ] Reordering valid inputs does not change the result.
- [ ] Inputs, upstream evidence, market state, and signal snapshots are not
      mutated.
- [ ] Transaction frequency is rejected/deferred rather than inferred.
- [ ] The focused test requirements pass.
- [ ] No provider, external I/O, persistence, dependency, workflow, trading,
      scoring, opportunity, predictive, or AI behavior is introduced.
- [ ] No baseline document or `PROJECT_STATE.md` status is changed by the
      implementation.

Any failed criterion is a FAIL; there is no partial implementation claim.

## 27. Architectural invariants

The following invariants are mandatory:

1. Point-in-time information is the only information eligible for calculation.
2. Observation time remains distinct from received and processing time.
3. UNKNOWN never becomes a valid feature through a default or fallback.
4. No silent fallback, interpolation, extrapolation, clamping, averaging, or
   source preference is permitted.
5. Feature results retain enough provenance for deterministic replay.
6. Feature calculation is immutable with respect to all upstream inputs.
7. A feature value has no authorization, trading, or predictive meaning.
8. Provider neutrality is preserved at the calculation boundary.
9. Version changes are explicit and never applied retroactively.
10. External I/O is outside the boundary.
11. The Risk Governor and future Decision Engine remain separate boundaries.
12. A generic upstream category does not grant undocumented measurement
    semantics.

## 28. Explicit non-goals

This specification does not establish that price velocity or acceleration are
profitable, predictive, stable across regimes, suitable for trading, or ready
for opportunity scoring. It does not define thresholds, signals, BUY/SELL
behavior, confidence, expected edge, risk limits, or execution feasibility.

It also does not claim that generic P02-T09 transaction-flow values are
transaction counts. It does not authorize using signal status as a proxy for a
numeric market measurement.

## 29. Future extension boundary

Future features may be added only through a separate reviewed definition that
states:

- the exact upstream input contract and semantic fields;
- the mathematical formula and units;
- the required timestamp/window semantics;
- duplicate, ordering, contradiction, stale, UNKNOWN, and future-data rules;
- the provenance and snapshot linkage carried by the result;
- the versioning and canonical representation;
- focused tests and objective acceptance criteria;
- why the feature does not bypass provider neutrality or downstream
  governance.

Transaction frequency may proceed only after an explicit transaction-event or
transaction-count contract defines identity, deduplication, event time,
windowing, and source reconciliation. Volume, liquidity, flow, wallet, social,
regime, and complex momentum features require their own input contracts and
must not be smuggled into the price profile.

## Governance

This document records:

**SPECIFICATION READY — IMPLEMENTATION NOT STARTED**

P04-T09 is not implemented by creating this document. No production code,
existing tests, dependency files, runtime configuration, workflow, project
state, or architecture baseline document is authorized to change as part of
the specification-only step.