# P07-T02 — Paper Fill Model / Outcome Contract

**Status:** SPECIFICATION COMPLETE — AUDITED PASS — IMPLEMENTATION AUTHORIZED
**Phase:** P07 — Paper Trading Engine
**Task:** P07-T02 — Deterministic Paper Fill Model / Outcome Contract

## 1. Purpose

P07-T02 defines the immutable, deterministic contract for converting an
approved P07-T01 simulation input into one bounded hypothetical fill outcome.

It models quantity, liquidity, price, fees, spread, slippage, price impact,
quote drift, latency, priority fees, and MEV/adverse-ordering effects only from
supplied evidence or explicitly versioned simulation assumptions.

It does not create live execution capability.

## 2. Architectural position

P06 DecisionIntent
→ P07-T01 PaperSimulationInput
→ P07-T02 Fill Model / Fill Outcome
→ future P07 position / ledger boundaries

P07-T02 is simulation-only.

## 3. Scope

T02 may define:

- BUY and SELL fill evaluation;
- requested, filled, and remaining quantity;
- effective execution price;
- explicit friction components;
- full, partial, failed, rejected, unavailable, and invalid outcomes;
- deterministic canonical representation and digest;
- versioned fill/friction model identity;
- quote drift and execution latency representation;
- fail-closed validation.

T02 does not define paper position mutation, exposure mutation, ledger
persistence, reconciliation, providers, RPC, DEX, wallet, signing,
broadcast, or live execution.

## 4. Required input boundary

T02 consumes only an accepted P07-T01 `PaperSimulationInput` and explicitly
supplied fill-model evidence/configuration already represented by its approved
versioned identities.

It must not fetch, infer, refresh, or reconstruct missing external evidence.

## 5. Fill outcome statuses

The contract must distinguish:

- `FILLED`
- `PARTIALLY_FILLED`
- `FAILED`
- `REJECTED`
- `UNAVAILABLE`
- `INVALID`

`UNAVAILABLE` and `INVALID` are non-success outcomes.

No missing or unknown evidence may silently become a successful fill.

## 6. Quantity semantics

The outcome must preserve:

- requested quantity;
- filled quantity;
- remaining quantity;
- quantity unit;
- deterministic quantity validation.

Required invariants:

- requested quantity > 0;
- filled quantity >= 0;
- remaining quantity >= 0;
- filled quantity + remaining quantity = requested quantity;
- filled quantity cannot exceed available executable liquidity;
- failed, rejected, unavailable, and invalid outcomes cannot report a
  successful positive fill.

Partial fills are first-class outcomes.

## 7. Price semantics

The outcome must preserve:

- reference quote price;
- applicable fill price;
- effective price;
- quote observation timestamp;
- fill/simulation timestamp;
- explicit quote drift.

Price calculations must use only supplied values and the versioned model.

No live quote lookup is permitted.

## 8. Friction semantics

The contract must represent separately:

- fees;
- spread;
- slippage;
- price impact;
- liquidity constraint;
- quote drift;
- observation-to-fill latency;
- priority fees;
- MEV/adverse-ordering effects.

Every applied friction must identify either supplied evidence or a versioned
simulation assumption.

Unknown or unavailable friction must remain explicit and must not become zero
by default.

## 9. Latency and temporal boundary

All timestamps must be explicit and UTC-normalized.

The model must reject future observations relative to the supplied simulation
reference time.

No wall-clock access is permitted.

Latency must be represented as supplied or deterministically derived from
approved timestamps.

Temporal invariants:

- observation time MUST be <= simulation reference time;
- quote observation time MUST be <= simulation reference time;
- fill/simulation time MUST be <= simulation reference time;
- derived latency MUST be non-negative;
- negative latency is INVALID;
- future-data leakage is REJECTED;
- timestamp equality is permitted;
- no timestamp may be obtained from the system clock.

## 9A. Quantity, unit, rounding, and friction precedence

Quantity, price, fee, and friction values MUST use canonical decimal
representations. Binary floating-point values are not permitted in the
deterministic calculation boundary.

The contract MUST define:

- quantity unit;
- price unit;
- fee unit;
- liquidity unit;
- rounding mode;
- maximum permitted decimal precision;
- the exact point at which rounding is applied.

Rounding MUST occur deterministically and MUST NOT be performed implicitly by
serialization.

The friction application order is fixed:

1. reference quote price;
2. spread adjustment;
3. quote-drift adjustment;
4. slippage adjustment;
5. price-impact adjustment;
6. MEV/adverse-ordering adjustment;
7. fee and priority-fee accounting.

Each component MUST be represented separately in the outcome.

The effective price MUST be reproducible from the canonical reference price
and the ordered applied friction components.

If a required friction component is UNKNOWN or UNAVAILABLE and the approved
configuration does not explicitly define a deterministic substitute, the
result MUST be `UNAVAILABLE` rather than silently assuming zero.

Liquidity determines executable quantity only. Liquidity MUST NOT silently
change the requested quantity.

For executable liquidity L and requested quantity Q:

- Q <= L permits a full fill, subject to other validation;
- 0 < L < Q permits a partial fill;
- L <= 0 permits no positive fill and results in a non-success outcome;
- filled quantity MUST never exceed L;
- remaining quantity MUST equal Q - filled quantity.

The exact numeric formulas and rounding behavior are part of the versioned
fill/friction model identity. Changing them requires a new model version.

## 10. BUY boundary

BUY evaluation may produce a hypothetical fill using supplied price,
liquidity, quantity, and friction inputs.

A successful BUY outcome remains hypothetical and cannot create authorization,
an order, a transaction, or live capital movement.

## 11. SELL boundary

SELL evaluation may produce a hypothetical disposal using supplied paper-state
context and execution observations.

Insufficient inventory, unavailable sellability, stale/contradictory inputs,
and insufficient liquidity must fail closed.

T02 does not mutate the supplied paper state.

## 12. Partial-fill semantics

A partial fill must preserve:

- requested quantity;
- filled quantity;
- remaining quantity;
- effective price;
- applied friction;
- timestamps;
- model/configuration identity;
- deterministic provenance.

Treatment of the remaining quantity (cancelled, open, expired, etc.) is a
later versioned policy and must not be inferred by T02.

## 13. Failure semantics

Invalid, stale, future, incomplete, contradictory, unsupported, tampered, or
unavailable required inputs must produce explicit non-success outcomes or be
rejected before evaluation.

Failure must never increase paper position, create authorization, or trigger
live execution.

## 14. Determinism

Identical canonical inputs, configuration, and model versions must produce:

- identical outcome;
- identical canonical representation;
- identical digest;
- identical friction representation;
- identical provenance linkage.

No random values, provider state, retries, filesystem state, database state,
network access, or uncontrolled clock may affect the result.

## 15. Canonical identity and provenance

The outcome must preserve:

- P07-T01 input digest;
- fill-model version;
- friction-model version;
- simulation configuration identity;
- replay identity;
- relevant observation identities/digests;
- timestamps;
- canonical outcome representation;
- deterministic outcome digest.

Changing field meaning, requiredness, units, rounding, formulas, or
canonicalization requires a new contract/model version.

## 16. Authority boundaries

P07-T02 MUST NOT:

- create or modify Risk/Capital Authorization;
- modify P06 DecisionIntent;
- create an order or execution permission;
- mutate paper positions or exposure;
- persist a ledger;
- reconcile state;
- call providers, RPC, DEXs, wallets, signing, or broadcast;
- invoke P08 or P09;
- use LLM/AI loops, ranking, optimization, or learning;
- introduce databases, queues, caches, migrations, or external services.

A fill outcome is evidence of a hypothetical simulation only.

## 17. Focused test plan

Tests must cover:

1. valid BUY fill;
2. valid SELL fill;
3. full fill;
4. partial fill;
5. failed fill;
6. rejected preconditions;
7. unavailable input;
8. invalid/contradictory input;
9. quantity conservation;
10. liquidity limits;
11. fees and spread;
12. slippage and price impact;
13. quote drift;
14. latency;
15. priority fees;
16. MEV/adverse-ordering effects;
17. unknown friction not becoming zero;
18. future-data rejection;
19. stale-data rejection;
20. deterministic canonicalization;
21. deterministic digest;
22. replay identity stability;
23. immutability;
24. absence of external I/O;
25. absence of position/ledger/live-execution mutation.

## 18. Entry criteria

Implementation may begin only after:

- this specification is audited and approved;
- field-level semantics are accepted;
- units and rounding policy are accepted;
- friction precedence is accepted;
- outcome status semantics are accepted;
- deterministic replay requirements are accepted;
- implementation files receive explicit authorization.

This specification itself does not grant implementation authorization.

## 19. Exit criteria

T02 specification is complete when the document is audited, project state is
synchronized, and no runtime implementation is created by the specification
task.

T02 implementation is complete only when all approved focused tests pass and
all authority, determinism, provenance, and fail-closed requirements are
verified.

## 20. Proposed implementation files

Only after explicit authorization:

- `core/execution/paper_fill_outcome.py`
- `tests/test_paper_fill_outcome.py`

No other implementation files are authorized by this specification.

## 21. Governance conclusion

P07-T02 specification has passed audit.
Implementation is AUTHORIZED only for the explicitly approved files below.

P07-T02 must remain deterministic, provider-neutral, simulation-only,
fail-closed, immutable, and independent from position mutation, ledger,
reconciliation, Risk/Capital Authorization, and live execution.
