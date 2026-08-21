# P07 — Paper Trading Engine Specification

**Status:** ARCHITECTURE GATE PASSED — P07-T01 SPECIFICATION IN REVIEW —
IMPLEMENTATION NOT AUTHORIZED
**Phase:** P07 — Paper Trading Engine  
**Purpose:** Reproducibly simulate execution consequences without moving real
capital or connecting to live execution infrastructure.

## 1. Purpose

P07 defines the governance boundary for deterministic and reproducible paper
execution. It consumes an analytical P06 decision intent together with
explicitly supplied point-in-time market and simulation context, models
execution frictions and failure, and records simulated outcomes.

P07 is for historical, backtest, shadow, and real-time paper evaluation. It is
not a live-trading system and cannot create authority to trade.

## 2. Scope

P07 may define contracts for:

- paper BUY and SELL simulation;
- execution-friction representation;
- deterministic fill and partial-fill outcomes;
- failed, unavailable, delayed, and invalid simulation outcomes;
- paper positions and exposure observations;
- paper-ledger records;
- reconciliation of paper state against supplied authoritative observations;
- point-in-time provenance and reproducible replay.

Numerical friction formulas, venue behavior, data schemas, persistence choices,
and provider adapters require a later implementation specification. This
document establishes boundaries rather than inventing those details.

## 3. Architectural position

```text
P05-T08 OpportunityContext
        ↓
P06-T02 deterministic evaluation
        ↓
P06 DecisionIntent
        ↓
independent Risk / Capital Authorization
        ↓
P07 Paper Trading Engine
        ↓
paper fills / paper positions / exposure / reconciliation / ledger
        ↓
future P08 outcome learning
```

P07 is in the execution layer but is simulation-only. A paper result is not an
authorization, an order, a quote, a route, or an on-chain state transition.

## 4. Dependencies

P07 depends on:

- the validated, immutable P06 `DecisionIntent`;
- complete P06/P05 provenance and point-in-time references;
- an independently supplied Risk Governor or capital-authorization result
  where the simulation scenario requires authorization;
- supplied market, liquidity, quote, and execution-observation context;
- a versioned paper-simulation configuration;
- an explicitly versioned paper-state input and ledger identity.

P07 does not implement any dependency listed above. In particular, it does not
implement the Risk Governor, P06 evaluation, live data collection, or venue
execution.

## 5. Entry criteria

Implementation may not begin until:

- this specification passes architecture review;
- the P06 input and provenance linkage are agreed;
- the independent risk/authorization input boundary is specified;
- paper-state and ledger identity semantics are specified;
- deterministic simulation and failure rules are versioned;
- the persistence and retention boundary is approved;
- focused, integration, historical-replay, and failure-path verification plans
  are accepted.

No P07 runtime implementation is authorized by this document alone.

## 6. Input contract

The eventual P07 input must contain, by identity rather than reconstruction:

1. one validated P06 `DecisionIntent`;
2. the P06 digest, contract/evaluator/ruleset versions, and decision timestamp;
3. the independently supplied authorization/governance observation, if the
   scenario requires one;
4. one point-in-time market and execution-observation snapshot;
5. one versioned simulation configuration;
6. one initial paper-position and exposure state;
7. an explicit simulation reference time and replay identity.

The input must reject missing, stale, future, tampered, unsupported,
non-canonical, contradictory, or internally inconsistent material. P07 must
not reconstruct missing evidence or silently fetch newer information.

The exact field-level contract remains a later implementation decision.

## 7. Paper execution model

P07 models a hypothetical execution attempt against supplied observations. The
model must identify:

- the intended analytical direction from P06;
- the simulated request quantity and relevant constraints;
- the observation time and simulation time;
- the available liquidity and quote context;
- the configured friction and fill model;
- the resulting fill, partial fill, failure, or unavailable outcome;
- the state transition applied to paper positions and the ledger.

The model must be replayable from its versioned inputs and must not use
uncontrolled wall-clock, network, filesystem, database, provider, wallet, or
chain access.

## 8. BUY simulation boundary

BUY simulation may estimate a hypothetical acquisition using supplied price,
liquidity, quote, latency, fee, spread, slippage, price-impact, priority-fee,
and MEV observations or configured assumptions.

It must report whether the simulated BUY was filled, partially filled,
failed, unavailable, or rejected by the simulation preconditions. A simulated
BUY must never create an authorization or an executable transaction.

## 9. SELL simulation boundary

SELL simulation may estimate a hypothetical disposal using the supplied paper
position, price, liquidity, quote, sellability, latency, fee, spread, slippage,
price-impact, priority-fee, and MEV observations or configured assumptions.

It must explicitly handle insufficient paper inventory, unavailable
sellability, stale quotes, failed fills, partial fills, and contradictory
state. A SELL result remains a paper outcome and never becomes a live exit
instruction.

## 10. Execution-friction model

The P07 model must represent, without assuming perfect fills:

- fees;
- spread;
- slippage;
- price impact;
- available liquidity;
- quote drift;
- observation-to-fill latency;
- priority fees; and
- MEV or adverse-ordering effects.

Each friction must be attributable to either supplied evidence or a versioned
simulation assumption. Unknown or unavailable friction information must remain
visible and cannot silently become zero.

Specific formulas, units, rounding rules, and precedence are intentionally
left for the implementation contract.

## 11. Fill model

The fill model must be explicit, versioned, and reproducible. It must define
how supplied quantity, available liquidity, price, fees, and friction produce
filled quantity, remaining quantity, effective price, and outcome status.

The model must distinguish:

- fully filled;
- partially filled;
- failed;
- rejected by simulation preconditions;
- unavailable/indeterminate; and
- invalid or contradictory input.

It must not model an unobserved fill as successful merely because a P06 intent
exists.

## 12. Partial-fill semantics

Partial fills must be represented as first-class outcomes. The contract must
preserve filled quantity, unfilled quantity, applied friction, timestamps,
and the resulting paper position and ledger effects.

Unfilled remainder behavior—cancelled, left open in simulation, or expired—
must be chosen by a later versioned simulation configuration. It must never be
implicitly treated as filled.

## 13. Failure semantics

P07 must fail closed for invalid, stale, future, incomplete, unsupported,
tampered, contradictory, or unavailable required input. Outcomes must remain
observable and distinguish at least simulation rejection, execution failure,
data unavailability, and reconciliation disagreement.

Failure must not create a successful fill, a position increase, an
authorization, or a permissive fallback. Where a deterministic simulation
cannot be completed, the result must be an explicit non-success outcome.

## 14. Latency and quote-drift representation

The input must preserve observation time, simulation reference time, quote
time, and any configured or observed execution latency. Quote drift must be
represented as an explicit difference between the applicable quote observation
and the simulated fill observation.

P07 must not read future observations relative to the simulation reference
time. Numerical latency budgets are not set here; they require later
benchmarks.

## 15. Position-state boundary

P07 may maintain a paper position state derived only from accepted simulated
outcomes. The state must preserve asset identity, quantity, cost basis or
equivalent accounting context, timestamps, provenance, and contract versions
needed for replay.

Paper position state is not authoritative on-chain state. P07 must not claim
that a paper position exists on a wallet or venue.

## 16. Exposure representation

P07 may report simulated exposure observations derived from paper positions,
prices, and the approved simulation configuration. Exposure is informational
for paper evaluation and is not capital authorization, portfolio permission,
or a Risk Governor decision.

Portfolio limits and correlated/theme/ecosystem risk authority remain owned by
the independent Risk Governor. P07 may record a supplied block or reduction,
but cannot create, relax, or override one.

## 17. Reconciliation boundary

P07 reconciliation compares paper state and ledger state with explicitly
supplied observations or replay expectations. It must identify missing,
duplicated, delayed, partial, failed, contradictory, and unexpected simulated
events.

Reconciliation cannot claim on-chain truth. Actual on-chain state remains the
authority in future live boundaries. A disagreement must remain visible and
must fail closed for any dependent paper transition until resolved by the
governed contract.

## 18. Paper-ledger boundary

The paper ledger must be append-oriented and auditable. Each entry must link
the simulated outcome to the P06 intent digest, simulation configuration,
market/execution snapshot, paper-state version, timestamps, and resulting
position-state digest.

Ledger entries record hypothetical outcomes only. They are not orders,
transactions, settlements, capital movements, or journaled live executions.
Retention, storage technology, and compaction require a later persistence
specification.

## 19. Provenance and reproducibility

Every result must preserve enough immutable provenance to reproduce the
simulation:

- P06/P05 source identities and digests;
- simulation input and configuration versions;
- market, quote, liquidity, and friction evidence references;
- paper-state and ledger identities;
- reference, observation, and simulation timestamps;
- evaluator/fill-model versions; and
- the canonical result representation and deterministic digest.

No result may depend on hidden mutable state or uncontrolled future data.

## 20. Deterministic versus non-deterministic behavior

The core paper simulation must be deterministic for identical canonical inputs,
configuration, and versions. Any later stochastic or probabilistic scenario
analysis must be explicitly isolated, seeded, versioned, and labelled as
non-deterministic; it cannot silently affect the deterministic result.

Provider responses, live clock reads, random seeds, network retries, and
external mutable state are not permitted in the deterministic core.

## 21. Fail-closed behavior

P07 must produce an explicit non-success or invalid result when required
evidence, authorization observation, quote, liquidity, sellability, timing,
friction, or state information is missing, stale, future, contradictory, or
unreliable.

It must preserve UNKNOWN and invalidated states. It must never convert
UNKNOWN to PASS, unavailable execution information to success, or a P06
analytical action into execution permission.

## 22. Forbidden ownership

P07 must not own or implement:

- Risk Governor authority or capital authorization;
- strategy ranking, optimization, learning, or model promotion;
- wallets, private keys, signing, or key custody;
- RPC, DEX, Jupiter, Jito, venue, or provider integrations;
- transaction construction, submission, broadcast, or live reconciliation;
- real-money trading or autonomous capital movement;
- LLM trading or an autonomous AI loop; or
- P06 decision authority.

P07 cannot bypass risk, create authorization from a paper fill, or change a
P06 `DecisionIntent`.

## 23. Persistence boundary

P07 may eventually persist paper inputs, outputs, positions, reconciliation
reports, and ledger entries through an explicitly approved persistence
contract. Persistence must preserve immutability, provenance, retention,
replay identity, and auditability.

This specification authorizes no tables, migrations, database dependency,
queue, cache, or external storage. In-memory versus durable storage remains a
separate design decision.

## 24. Testing requirements

Later implementation verification must include focused tests for:

- valid BUY and SELL simulation;
- fees, spread, slippage, price impact, liquidity, quote drift, latency,
  priority fees, and MEV effects;
- full fills, partial fills, failed fills, and unavailable inputs;
- stale, future, tampered, contradictory, unsupported, and incomplete input;
- paper position and exposure transitions;
- duplicate, delayed, missing, unexpected, and conflicting reconciliation
  events;
- append-only ledger provenance and deterministic digest;
- identical input producing identical output;
- rejection of future-data leakage and uncontrolled clocks;
- separation from risk authorization and live execution;
- safe absence of external providers, wallets, RPC, DEX, signing, and
  broadcast behavior; and
- historical replay, real-time paper, and failure-path behavior.

Verification must remain targeted to the approved implementation scope.

## 25. Exit criteria

P07 implementation may be considered complete only when:

- the field-level contracts and versions are separately approved;
- deterministic replay produces identical results;
- friction and partial/failure semantics are evidenced by tests;
- paper state, exposure, reconciliation, and ledger provenance are complete;
- fail-closed and authority-separation tests pass;
- no live execution capability or forbidden integration exists; and
- documentation, project state, and verification evidence are synchronized.

Passing tests alone does not authorize real-money execution or P09 work.

## 26. Explicit non-scope

P07 does not implement or authorize:

- Risk Governor or capital authorization;
- live execution, real-money trading, wallets, private keys, signing,
  broadcast, RPC, DEX, Jupiter, Jito, or venue integration;
- transaction construction or submission;
- autonomous trading, LLM trading, strategy optimization, learning, or
  promotion;
- P08 outcome learning;
- P09 execution work;
- database migrations, provider dependencies, or production workflows; or
- changes to completed P05/P06 contracts.

## 27. Future transition boundary toward P08/P09

P07 outputs may later become inputs to:

- **P08:** read-only outcome and performance learning after sufficient
  immutable paper outcomes exist; or
- **P09:** separately authorized provider-agnostic execution after paper
  evidence, risk controls, pre-flight, signing, and go-live gates pass.

Neither transition is automatic. Paper outcomes do not authorize capital,
promote a strategy, or establish live execution readiness by themselves.

## Governance conclusion

P07 architecture gate is **PASSED**. P07-T01 is the first implementation
boundary under audit; no P07 runtime implementation is authorized until its
specification is audited and explicitly approved.