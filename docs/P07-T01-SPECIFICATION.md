# P07-T01 — Paper Simulation Input / Execution Context Contract

**Status:** SPECIFICATION PREPARED — IMPLEMENTATION NOT AUTHORIZED PENDING
AUDIT  
**Phase:** P07 — Paper Trading Engine  
**Contract:** `p07-t01-v1`  
**Nature:** Immutable, provider-neutral input boundary only

## 1. Purpose

P07-T01 defines the complete, immutable input envelope for one paper-simulation
attempt. It binds one validated P06 `DecisionIntent` to independently supplied
authorization observations, point-in-time execution observations, a versioned
simulation configuration, an initial paper state, and a deterministic replay
identity.

P07-T01 validates identity and provenance. It does not calculate a fill,
mutate a position, persist a ledger, or authorize execution.

## 2. Architectural position

```text
validated P05-T08 OpportunityContext
              ↓
      P06-T02 DecisionIntent
              ↓
 independent Risk / Capital Authorization observation
              ↓
 P07-T01 PaperSimulationInput / ExecutionContext
              ↓
      future P07 simulation task
```

P07-T01 is an execution-layer input boundary, not an execution authority. A
valid input means only that the supplied material is internally coherent and
safe to consume as simulation context. It does not mean that a trade is
authorized, executable, profitable, or live.

## 3. Scope

This specification defines:

- the exact field groups and identity links for one input;
- immutable provenance linkage to one P06 `DecisionIntent`;
- an independent Risk / Capital Authorization observation;
- the point-in-time execution observation boundary;
- simulation configuration and initial paper-state identities;
- simulation reference-time and replay rules;
- canonical representation and digest requirements;
- validation, UNKNOWN, contradiction, and fail-closed semantics; and
- the focused verification plan for a future implementation.

This specification does not define fill formulas, friction behavior, position
transitions, ledger persistence, or any external integration.

## 4. Contract identity and top-level fields

The eventual immutable value object is named `PaperSimulationInput`. Its
canonical top-level fields are:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `contract_version` | canonical text | yes | P07-T01 contract version; must be `p07-t01-v1` |
| `decision_intent` | identity envelope | yes | Exact validated P06 intent linkage |
| `authorization_observation` | authorization envelope | conditional | Independent supplied authorization observation |
| `execution_observation` | observation envelope | yes | Point-in-time market/execution context |
| `simulation_configuration` | configuration identity | yes | Versioned simulation configuration identity |
| `initial_paper_state` | paper-state identity | yes | Initial position/exposure state identity |
| `simulation_reference_time` | UTC timestamp | yes | The as-of boundary for this simulation |
| `replay_identity` | replay identity | yes | Stable identity for deterministic reruns |
| `input_digest` | lowercase SHA-256 text | derived | Digest of all other canonical fields |

The serialized contract must contain no fields outside this specification.
Unknown fields are rejected rather than ignored. `input_digest` is derived and
must never be accepted as authority over its canonical source fields.

## 5. P06 DecisionIntent identity and provenance linkage

`decision_intent` must contain:

| Field | Type | Required |
|---|---|---:|
| `decision_intent_digest` | lowercase SHA-256 text | yes |
| `context_digest` | lowercase SHA-256 text | yes |
| `candidate_id` | canonical text | yes |
| `chain_id` | canonical text | yes |
| `token_identity` | canonical text | yes |
| `action` | P06 action value | yes |
| `entry_posture` | P06 posture value | yes |
| `decision_time` | UTC timestamp | yes |
| `p06_t01_contract_version` | canonical text | yes |
| `p06_t01_ruleset_version` | canonical text | yes |
| `p06_t01_evaluator_version` | canonical text | yes |
| `p06_t02_ruleset_version` | canonical text or explicit `NOT_APPLICABLE` | yes |
| `p06_t02_evaluator_version` | canonical text or explicit `NOT_APPLICABLE` | yes |

The envelope is a reference to the already validated immutable P06 object, not
a reconstructed substitute. The implementation must validate that the
supplied digest equals the canonical digest of the supplied `DecisionIntent`,
that all duplicated identity values agree with the intent, and that the
version values agree with the intent and its evaluator provenance.

P07-T01 must not reinterpret P06 action, confidence, uncertainty, or entry
posture as an order, quantity, authorization, route, or fill instruction. A
P06 `NO_TRADE`, invalid, or uncertain intent remains exactly that in the
simulation input.

## 6. Independent Risk / Capital Authorization observation

`authorization_observation` is an independent observation supplied by the
Risk / Capital Authorization boundary. P07-T01 neither creates nor evaluates
it. It must contain:

| Field | Type | Required |
|---|---|---:|
| `observation_id` | canonical text | yes |
| `observation_digest` | lowercase SHA-256 text | yes |
| `status` | `PASS`, `FAIL`, `UNKNOWN`, or `NOT_REQUIRED` | yes |
| `scope_identity` | canonical bounded identity | yes |
| `observed_at` | UTC timestamp | yes |
| `valid_from` | UTC timestamp | yes |
| `valid_until` | UTC timestamp or `null` | yes |
| `contract_version` | canonical text | yes |
| `risk_governor_version` | canonical text | yes |
| `capital_authorization_version` | canonical text | yes |
| `reason_codes` | sorted tuple of canonical text | yes |
| `unknown_reasons` | sorted tuple of canonical text | yes |

`NOT_REQUIRED` is permitted only when the approved simulation scenario
explicitly declares that no authorization observation is applicable. It is not
a way to bypass a required authorization boundary. `PASS` must be valid for
the complete simulation scope at `simulation_reference_time`; a historical,
expired, differently scoped, or incomplete PASS is invalid.

`FAIL` and `UNKNOWN` are preserved observations. They cannot be upgraded by
P07-T01. A scenario requiring authorization must fail closed when the status
is `FAIL`, `UNKNOWN`, missing, stale, future, or contradictory.

## 7. Point-in-time execution observation boundary

`execution_observation` is a supplied, bounded, provider-neutral snapshot. It
must contain:

| Field | Type | Required |
|---|---|---:|
| `observation_id` | canonical text | yes |
| `observation_digest` | lowercase SHA-256 text | yes |
| `subject_identity` | canonical bounded identity | yes |
| `observation_time` | UTC timestamp | yes |
| `availability_time` | UTC timestamp | yes |
| `quality` | `PASS`, `FAIL`, `UNKNOWN`, or `INVALID` | yes |
| `market_context_digest` | lowercase SHA-256 text or `null` | yes |
| `quote_context_digest` | lowercase SHA-256 text or `null` | yes |
| `liquidity_context_digest` | lowercase SHA-256 text or `null` | yes |
| `sellability_status` | `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE` | yes |
| `source_contract_version` | canonical text | yes |
| `source_provenance` | bounded canonical mapping | yes |
| `observation_replay_key` | canonical text | yes |

The observation contains evidence and identity, not provider clients or live
fetch instructions. Raw unbounded payloads, opaque objects, callbacks,
network handles, and provider-specific behavior are outside this contract.
The eventual P07 simulation task decides how an approved observation is used;
P07-T01 only establishes whether it is safe to consume.

## 8. Simulation configuration identity

`simulation_configuration` identifies the exact configuration that a future
simulation implementation would consume:

| Field | Type | Required |
|---|---|---:|
| `configuration_id` | canonical text | yes |
| `configuration_digest` | lowercase SHA-256 text | yes |
| `contract_version` | canonical text | yes |
| `simulation_version` | canonical text | yes |
| `fill_model_version` | canonical text | yes |
| `friction_model_version` | canonical text | yes |
| `failure_policy_version` | canonical text | yes |
| `seed_policy_version` | canonical text | yes |
| `configuration_provenance` | bounded canonical mapping | yes |

The identity is mandatory even though P07-T01 does not implement any model.
Configuration material must be versioned and digestible; it must not be
silently defaulted, partially supplied, or changed during replay. The field
versions identify future behavior without authorizing that behavior.

## 9. Initial paper position/exposure state identity

`initial_paper_state` is an immutable as-of identity for the state before the
future simulation task runs:

| Field | Type | Required |
|---|---|---:|
| `state_id` | canonical text | yes |
| `state_digest` | lowercase SHA-256 text | yes |
| `state_version` | canonical text | yes |
| `portfolio_scope` | canonical bounded identity | yes |
| `position_state_digest` | lowercase SHA-256 text | yes |
| `exposure_state_digest` | lowercase SHA-256 text | yes |
| `as_of_time` | UTC timestamp | yes |
| `state_quality` | `PASS`, `FAIL`, `UNKNOWN`, or `INVALID` | yes |
| `state_provenance` | bounded canonical mapping | yes |

This is an input identity, not a mutable position object. P07-T01 must not
open, close, resize, reconcile, or otherwise mutate positions or exposure.
`UNKNOWN` state is preserved and is fail-closed when the approved scenario
requires a known initial state.

## 10. Simulation reference time and replay identity

`simulation_reference_time` is the single as-of boundary for the input. It is
not read from the system clock and must be supplied explicitly.

`replay_identity` must contain:

| Field | Type | Required |
|---|---|---:|
| `replay_id` | canonical text | yes |
| `replay_schema_version` | canonical text | yes |
| `replay_seed_identity` | canonical text | yes |
| `parent_replay_id` | canonical text or `null` | yes |
| `replay_scope` | canonical bounded identity | yes |

Two inputs with identical canonical fields must have identical `input_digest`
and must be eligible for identical replay. A replay identity does not permit
changing any input field. A different scenario, state, observation, or
configuration requires a different canonical digest and must be observable.

## 11. Immutability, identity, and provenance invariants

The eventual implementation must enforce all of the following:

1. Every required nested value is immutable after construction.
2. Every identity digest is computed from the canonical value it identifies.
3. The top-level digest covers every canonical field except itself.
4. P06 identity values are copied by reference/value verification, never
   reconstructed from partial evidence.
5. Authorization, execution observation, configuration, and initial state each
   retain independent identity and provenance.
6. No nested mapping, sequence, decimal, or timestamp can be mutated through a
   returned representation.
7. Provider names or source labels do not grant authority and cannot replace
   contract versions or digests.
8. `UNKNOWN`, `FAIL`, and `INVALID` remain explicit states.
9. The input is not an order, authorization, fill, position, ledger record, or
   live execution request.
10. Canonical equality and digest equality must agree; equivalent values cannot
    produce different digests.

## 12. Canonical representation and deterministic digest

Canonicalization must follow the project’s existing deterministic conventions:

- mappings use sorted string keys;
- tuples and lists are represented as ordered arrays;
- sets are forbidden;
- timestamps are timezone-aware UTC values serialized in one canonical ISO-8601
  form;
- decimal values are finite and serialized as normalized decimal text, never
  binary floating-point text;
- enum values use their explicit wire values;
- nullable fields use `null`, not omitted fields;
- text is non-empty, trimmed, and UTF-8;
- bounded mappings contain only canonical JSON-compatible values;
- unknown fields, non-string keys, NaN, infinity, and opaque objects are
  rejected; and
- SHA-256 is computed over UTF-8 JSON with sorted keys, compact separators, and
  no extra whitespace.

The implementation must expose a canonical representation and a deterministic
digest. It must validate supplied nested digests before accepting the
top-level digest.

## 13. Validation and fail-closed rules

Validation must reject the input with a typed, deterministic failure outcome
for each of these classes:

| Class | Required behavior |
|---|---|
| Missing | Reject absent required fields; do not invent defaults |
| Stale | Reject evidence or authorization outside the approved age/validity window |
| Future | Reject timestamps after the simulation reference time |
| Tampered | Reject digest mismatch or reconstructed value mismatch |
| Unsupported | Reject unknown contract, evaluator, model, enum, or schema versions |
| Non-canonical | Reject non-normalized timestamps, decimals, mappings, sequences, or text |
| Contradictory | Reject disagreeing duplicated identities, statuses, scopes, or times |
| Internally inconsistent | Reject impossible relationships within one envelope |

At minimum, the following temporal relationships must hold:

- `P06 context.reference_time <= decision_time <= simulation_reference_time`;
- `authorization_observation.valid_from <= simulation_reference_time`;
- a `PASS` authorization remains valid through the reference time;
- `execution_observation.observation_time <= availability_time <=
  simulation_reference_time`;
- `initial_paper_state.as_of_time <= simulation_reference_time`; and
- no observation may claim a future event as available at an earlier time.

The contract must fail closed for invalid input. No partial object may be
returned as accepted, and no validator may silently repair, fetch, substitute,
truncate, or reorder semantic evidence. Failure reasons must be stable,
bounded, and suitable for deterministic tests without exposing secrets.

## 14. UNKNOWN handling

UNKNOWN is a first-class observation state, not an exception to be converted
to success. It must preserve its reason codes and provenance.

P07-T01 must:

- accept UNKNOWN only when the field and the scenario permit an unknown state;
- mark the input non-simulatable or invalid when a required known value is
  UNKNOWN;
- never convert UNKNOWN to `PASS`, `FAIL`, `NOT_REQUIRED`, or a numeric value;
- never infer authorization from a missing observation; and
- never infer market availability, sellability, position, or exposure from an
  absent digest.

The exact future simulation outcome for an accepted UNKNOWN-compatible input is
owned by a later P07 task. P07-T01 owns only preservation and boundary
validation.

## 15. Future-data-leakage prevention

All data used to construct the input must be available by its declared
`availability_time`, and that time must not exceed
`simulation_reference_time`. A later ingestion timestamp cannot make an
earlier observation valid if its event data was not then available.

The validator must use only supplied timestamps and approved versioned
freshness policies. It must not call the wall clock, fetch current quotes,
look up current authorization, or resolve missing provenance. Replay must
evaluate the same temporal boundary with the same supplied material.

## 16. Authority boundaries

P07-T01:

- MUST NOT create, approve, renew, or modify Risk / Capital Authorization;
- MUST NOT modify the P06 `DecisionIntent` or any P05/P06 contract;
- MUST NOT transform a P06 action into an order or execution permission;
- MUST NOT authorize live or paper execution;
- MUST NOT calculate fills, fees, spread, slippage, impact, latency, or MEV;
- MUST NOT mutate positions, exposure, or state;
- MUST NOT persist a ledger or create durable records;
- MUST NOT call providers, networks, RPC, DEXs, wallets, signing, or broadcast;
- MUST NOT invoke an LLM, AI loop, ranking, learning, P08, or P09; and
- MUST NOT start a workflow, database, migration, queue, cache, or external
  service.

A valid P07-T01 input is necessary context only. It is not permission.

## 17. Versioning and compatibility

`contract_version` is the P07-T01 wire-contract version. Any change to field
meaning, requiredness, canonicalization, validation, identity, or digest
material requires a new version and an explicit migration decision.

P06 versions are recorded as provenance and may not be rewritten by P07.
Simulation model versions are recorded as future behavior identities and must
not be interpreted by this contract. Unsupported versions fail closed.

Backward compatibility must never silently reinterpret an old digest under a
new canonicalization rule. Version-specific validators and explicit replay
migration, if ever approved, are separate future decisions.

## 18. Determinism and replay requirements

For identical canonical input, the eventual implementation must produce:

- identical canonical representation;
- identical nested and top-level digests;
- identical validation result and bounded failure codes;
- identical identity/provenance linkage; and
- no dependency on process order, local timezone, wall-clock time, random
  values, network state, or provider availability.

Any seed identity is input data, not permission to use uncontrolled
randomness. If future simulation requires pseudo-random behavior, the approved
implementation must derive it only from the canonical replay identity and
versioned policy.

## 19. Focused test plan for eventual implementation

Tests must be added only with explicit implementation authorization. The
focused suite must cover:

1. Construction of a valid immutable input with every required field.
2. Exact P06 digest, identity, version, and timestamp linkage.
3. Independent authorization observation in `PASS`, `FAIL`, `UNKNOWN`, and
   `NOT_REQUIRED` states.
4. Execution observation, configuration, and initial-state digest validation.
5. Canonical representation stability across mapping order and equivalent
   decimal/timestamp input.
6. Top-level and nested digest determinism.
7. Immutability of the input and all nested canonical representations.
8. Rejection of missing, stale, future, tampered, unsupported, non-canonical,
   contradictory, and internally inconsistent values.
9. Temporal checks preventing future-data leakage.
10. Preservation and fail-closed handling of UNKNOWN.
11. Rejection of altered P06 intent material and unauthorized substitutions.
12. Identical replay identity producing identical validation and digest.
13. Independence from the system clock and external I/O.
14. Explicit absence of fill calculation, position mutation, persistence,
    provider, wallet, signing, broadcast, and live-execution behavior.

## 20. Entry criteria

Implementation of P07-T01 may begin only after:

- this specification passes the required audit;
- field names, wire values, and version policy are approved;
- P06 linkage and independent authorization semantics are accepted;
- point-in-time and future-data-leakage rules are accepted;
- the focused test plan is accepted; and
- the implementation boundary below receives explicit authorization.

The architecture gate passing authorizes specification work, not runtime
implementation.

## 21. Exit criteria

The P07-T01 specification task is complete when the canonical document is
audited, the project state is synchronized, and no runtime, test, dependency,
database, migration, provider, or future-task files have been added.

The eventual implementation task is complete only when all focused tests pass,
the contract is immutable and deterministic, all fail-closed rules are
verified, and forbidden authority/integration behavior is absent.

## 22. Proposed implementation files (not created by this task)

The following files are proposed only. They must not be created until explicit
implementation authorization:

| File | Proposed responsibility |
|---|---|
| `core/execution/paper_simulation_input.py` | Immutable `PaperSimulationInput` and bounded nested identity envelopes |
| `core/execution/__init__.py` | Export the approved P07-T01 contract and version identifier |
| `tests/test_paper_simulation_input.py` | Focused contract, canonicalization, validation, immutability, and replay tests |

No database, migration, workflow, dependency, provider, network, RPC, DEX,
wallet, signing, broadcast, ledger, position, or future P07 task file is
proposed.

## Governance conclusion

P07 architecture gate: **PASSED**.  
P07-T01 specification: **PREPARED FOR AUDIT**.  
P07-T01 implementation: **NOT AUTHORIZED** pending audit of this
specification and explicit implementation approval.