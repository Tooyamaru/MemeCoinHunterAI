# P08 — P07 Risk/Capital Admission Contract Specification

**Status:** SPECIFICATION CORRECTED / AWAITING FORMAL RE-AUDIT
**Project:** MemeCoinHunterAI  
**Phase:** P08 — Outcome Learning  
**Boundary:** P06 `DecisionIntent` → Safe V1 Risk/Capital → P07-T01  
**Nature:** Immutable, deterministic, provider-neutral, paper-only admission
contract

## 1. Purpose

This specification closes blocker B-01 from the
`P08-PAPER-LIFECYCLE-END-TO-END-READINESS-REAUDIT`.

P07-T01 currently permits a structurally valid generic `PASS`
`AuthorizationObservation` without a `RiskCapitalAuthorizationReference`.
The linked path is present and G1 already rejects missing or inconsistent
Risk/Capital evidence before recognition, but the direct P07 admission boundary
is weaker than the approved paper-entry requirement.

This specification establishes the final Safe V1 P07 admission contract:

1. new P07-T01 admissions use `p07-t01-v2`;
2. every new Risk/Capital-gated v2 admission contains one immutable,
   canonical `RiskCapitalAuthorizationReference`;
3. the reference preserves the exact Risk/Capital authorization identity and
   result digest;
4. the reference links to the exact same P06 `DecisionIntent` identity and
   context digest;
5. generic `PASS` without the reference is insufficient;
6. `p07-t01-v1` is legacy/read-only evidence only and cannot become
   G1-recognized;
7. no automatic migration, inference, reconstruction, or substitution is
   allowed; and
8. the P07, P08, and G1 boundaries remain simulation-only and paper-only.

This is a contract specification. It does not authorize runtime or test
changes. A separate formal audit and limited implementation authorization are
required.

## 2. Scope and current gap

### 2.1 In scope

This specification governs only the identity and admission linkage between:

```text
validated P06 DecisionIntent
        ↓
approved Safe V1 Risk/Capital result
        ↓
P07-T01 PaperSimulationInput
        ↓
P07-T02 through P07-T07 paper lifecycle
        ↓
G1 simulation-only recognition
```

It defines:

- the exact v2 P07-T01 input fields;
- the exact reference fields and types;
- P06 → Risk/Capital → P07 identity and provenance invariants;
- canonical representation and digest rules;
- immutable propagation into P07 result and history;
- G1 recognition and legacy refusal;
- duplicate, replay, contradiction, stale, future, unsupported, and tampered
  behavior;
- a closed admission reason vocabulary and precedence;
- future implementation and focused-test scope; and
- the governance gates before implementation.

### 2.2 Current gap

The existing implementation already provides:

- frozen `RiskCapitalAuthorizationReference`;
- recursively immutable scope material;
- authorization identity and result digest;
- P06 intent and context digests;
- lifecycle and scope identity;
- authority, Risk Governor, capital, evaluator, and effect versions;
- reference digest verification;
- `AuthorizationObservation.from_risk_capital_result()` handoff; and
- G1 validation of the actual Risk/Capital result and its reference.

The remaining gap is limited to requiredness:

- `AuthorizationObservation.authorization_reference` is optional;
- P07 validates the reference only when supplied; and
- a generic `PASS` observation without the reference remains constructible.

The v2 contract makes the linked reference mandatory for a new
Risk/Capital-gated paper-entry admission without changing the Risk/Capital
evaluator or granting P07 an authorization role.

## 3. Contract identity and version policy

### 3.1 Contract versions

The new wire contract is:

```text
p07-t01-v2
```

The consumed Safe V1 Risk/Capital result remains:

```text
contract_version  = p08-risk-capital-authority-v1
evaluator_version = p08-risk-capital-authority-evaluator-v1
```

The required effect remains exactly:

```text
PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
```

The P07-T01 v2 contract changes requiredness and digest material. It must not
reinterpret a v1 digest under v2 rules.

The reference does not introduce a second authorization evaluator. Its
`contract_version` field identifies the Risk/Capital authority contract,
`p08-risk-capital-authority-v1`; its `evaluator_version` identifies the
Risk/Capital evaluator. The enclosing P07-T01 v2 contract identifies the
reference-required admission schema.

The exact supported-version matrix for this linked path is:

| Boundary | Supported version | Compatibility rule |
|---|---|---|
| P07-T01 new required-entry input | `p07-t01-v2` | Requires one valid reference for `PASS`. |
| P07-T01 legacy input | `p07-t01-v1` | Legacy/read-only evidence only; never a current admission. |
| P07-T02 | `p07-t02-v1` | Preserves the v2 T01 input identity; no v2 reinterpretation. |
| P07-T03 | `p07-t03-v1` | Preserves the v2 T01 input identity through predecessor links. |
| P07-T04 | `p07-t04-v1` | Preserves the v2 T01 input identity through ledger provenance. |
| P07-T05 | `p07-t05-v1` | Preserves the v2 T01 input identity through reconciliation provenance. |
| P07-T06 | `p07-t06-v1` | Preserves the v2 T01 input digest; it does not re-evaluate Risk/Capital. |
| P07-T07 | `p07-t07-v1` | Stores only validated T06 results and transitively protects the v2 input digest. |
| G1 current-recognition path | `p07-t01-v2` plus the P07-T02 through T07 versions above | A v1 T01 artifact is unsupported legacy evidence. |

The matrix describes the future v2 recognition path. It does not change the
current v1 runtime or authorize implementation. Until a separate
implementation authorization passes, the current source remains a v1
implementation and no v2 artifact can be produced by runtime.

### 3.2 Version compatibility

Any change to a field's:

- meaning;
- requiredness;
- canonical representation;
- validation rule;
- identity derivation; or
- digest coverage

requires a new contract version and an explicit compatibility decision.

Unsupported versions fail closed. A version that looks compatible by name,
field overlap, or result status is not substituted.

### 3.3 Legacy v1

`p07-t01-v1` artifacts are legacy/read-only evidence. They may be:

- parsed by version-specific legacy readers;
- retained for historical evidence;
- inspected for audit; and
- used by explicitly versioned legacy reporting.

They may not be:

- accepted as a new v2 admission;
- upgraded by adding a reference after the fact;
- migrated by copying fields from an observation or digest;
- inferred to contain Risk/Capital approval;
- reconstructed from a P06 intent or a lifecycle ID;
- substituted with a new authorization or policy;
- merged with a v2 input; or
- recognized by G1 as the current Safe V1 chain.

The exact G1 refusal for a v1 artifact presented to the current recognition
path is:

```text
recognition_state = NOT_RECOGNIZED
finality_state    = NOT_APPLICABLE
reason_code       = UNSUPPORTED_VERSION
```

The exact G1 refusal for a v2 artifact whose required reference is missing or
does not match the actual Risk/Capital result is:

```text
recognition_state = NOT_RECOGNIZED
finality_state    = NOT_APPLICABLE
reason_code       = INVALID_IDENTITY_LINK
```

For the current recognition contract, the missing-reference case has one
canonical mapping, regardless of which internal validator observes it first:

```text
v2 PASS with no authorization_reference
    → recognition_state = NOT_RECOGNIZED
    → finality_state    = NOT_APPLICABLE
    → reason_code       = MISSING_REQUIRED_INPUT
```

`INVALID_IDENTITY_LINK` is reserved for a present reference or supplied
authorization material whose identity linkage is wrong. The G1 precedence
checks `MISSING_REQUIRED_INPUT` before `INVALID_IDENTITY_LINK`.

Direct P07-T01 v2 admission rejects a missing required reference with
`MISSING_REQUIRED_INPUT` before a simulation lifecycle can begin.

No automatic migration exists. Any future migration would require a separate
specification, explicit source-evidence rules, a new versioned canonical
format, focused tests, implementation authorization, and an independent
audit.

## 4. Exact v2 `PaperSimulationInput` contract

The immutable value object remains `PaperSimulationInput`. Its v2 canonical
top-level fields are exactly:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `contract_version` | canonical text | yes | Must be `p07-t01-v2`. |
| `decision_intent` | `P06DecisionIntentIdentity` | yes | Exact validated P06 identity envelope. |
| `authorization_observation` | `AuthorizationObservation` | yes for a v2 required-entry admission | Exact Risk/Capital handoff observation. |
| `execution_observation` | execution observation identity | yes | Point-in-time provider-neutral execution context. |
| `simulation_configuration` | configuration identity | yes | Versioned simulation configuration identity. |
| `initial_paper_state` | paper-state identity | yes | Initial paper position/exposure identity. |
| `simulation_reference_time` | timezone-aware UTC timestamp | yes | Explicit simulation cutoff. |
| `replay_identity` | replay identity | yes | Stable deterministic replay identity. |
| `input_digest` | lowercase SHA-256 text | derived | Digest of every other canonical field. |

The serialized v2 input contains no fields outside this table and the exact
nested contracts defined below. Unknown fields are rejected. `input_digest` is
derived and never overrides its canonical source fields.

The v2 required-entry path does not use a missing authorization observation or
an observation with `NOT_REQUIRED`. `NOT_REQUIRED` remains available only for a
separately approved scenario that explicitly declares that no authorization
observation applies; that scenario is not the Safe V1 paper-entry path.

### 4.1 P06 decision identity envelope

`decision_intent` contains exactly these semantic fields:

| Field | Type | Required |
|---|---|---:|
| `decision_intent_digest` | lowercase SHA-256 text | yes |
| `context_digest` | lowercase SHA-256 text | yes |
| `candidate_id` | canonical text | yes |
| `chain_id` | canonical text | yes |
| `token_identity` | canonical text | yes |
| `action` | P06 action value | yes |
| `entry_posture` | P06 posture value | yes |
| `decision_time` | timezone-aware UTC timestamp | yes |
| `p06_t01_contract_version` | canonical text | yes |
| `p06_t01_ruleset_version` | canonical text | yes |
| `p06_t01_evaluator_version` | canonical text | yes |
| `p06_t02_ruleset_version` | canonical text or `NOT_APPLICABLE` | yes |
| `p06_t02_evaluator_version` | canonical text or `NOT_APPLICABLE` | yes |

The envelope is a verified identity projection of the supplied immutable P06
`DecisionIntent`. It is not reconstructed from partial fields.

The validator must confirm:

- `decision_intent_digest` equals the supplied P06 intent digest;
- `context_digest` equals the supplied P06 context digest;
- candidate, chain, token, action, posture, and decision time agree;
- every P06 version agrees with the P06 object; and
- the P06 object is itself canonical, immutable, and supported.

P07 does not reinterpret P06 action, confidence, uncertainty, or posture as an
order, quantity, authorization, route, or fill instruction.

### 4.2 Authorization observation envelope

The authorization observation retains the existing semantic fields:

| Field | Type | Required |
|---|---|---:|
| `observation_id` | canonical text | yes |
| `observation_digest` | lowercase SHA-256 text | derived and verified |
| `status` | `PASS`, `FAIL`, `UNKNOWN`, or `NOT_REQUIRED` | yes |
| `scope_identity` | bounded canonical mapping | yes |
| `observed_at` | timezone-aware UTC timestamp | yes |
| `valid_from` | timezone-aware UTC timestamp | yes |
| `valid_until` | timezone-aware UTC timestamp or `null` | yes |
| `contract_version` | canonical text | yes |
| `risk_governor_version` | canonical text | yes |
| `capital_authorization_version` | canonical text | yes |
| `reason_codes` | sorted tuple of canonical text | yes |
| `unknown_reasons` | sorted tuple of canonical text | yes |
| `authorization_reference` | `RiskCapitalAuthorizationReference` or `null` | required for v2 `PASS` admission |

For a new v2 Safe V1 paper-entry admission:

```text
status == PASS
authorization_reference != null
valid_until != null
valid_from <= simulation_reference_time <= valid_until
reason_codes == ()
unknown_reasons == ()
```

`PASS` without the reference is not a valid admission. It is not equivalent to
an approved Risk/Capital result.

`FAIL` and `UNKNOWN` remain explicit observations and cannot be upgraded.
`NOT_REQUIRED` is not valid for the required Safe V1 paper-entry path.

The observation digest covers every observation field, including the complete
canonical reference representation. Removing, replacing, or changing the
reference changes the observation digest.

### 4.3 Execution, configuration, state, time, and replay envelopes

The following nested contracts remain inherited from P07-T01 v1 without
semantic relaxation:

- `execution_observation` retains observation identity, subject identity,
  observation and availability times, quality, context digests, sellability,
  source contract, bounded provenance, and replay key;
- `simulation_configuration` retains configuration identity and all model,
  friction, failure, and seed policy version identities;
- `initial_paper_state` retains state identity, portfolio scope, position and
  exposure digests, as-of time, quality, and bounded provenance;
- `simulation_reference_time` is explicit, timezone-aware UTC, and never read
  from the system clock; and
- `replay_identity` retains replay ID, schema version, seed identity, optional
  parent replay ID, and bounded replay scope.

No v2 admission may silently default, omit, fetch, or reconstruct any inherited
field.

## 5. Exact `RiskCapitalAuthorizationReference`

### 5.1 Semantic fields

The immutable reference contains exactly these fields:

| Field | Type | Required | Canonical/null policy | Meaning |
|---|---|---:|---|---|
| `authorization_id` | lowercase SHA-256 text | yes | Non-null; exactly 64 lowercase hexadecimal characters. | Exact Risk/Capital authorization identity. |
| `authorization_digest` | lowercase SHA-256 text | yes | Non-null; exactly 64 lowercase hexadecimal characters. | Exact digest of the complete Risk/Capital result. |
| `decision_intent_digest` | lowercase SHA-256 text | yes | Non-null; exactly 64 lowercase hexadecimal characters. | Exact P06 `DecisionIntent` digest. |
| `context_digest` | lowercase SHA-256 text | yes | Non-null; exactly 64 lowercase hexadecimal characters. | Exact P06 context digest. |
| `paper_lifecycle_id` | canonical text | yes | Non-null; trimmed, non-empty, bounded UTF-8 text. | Exact paper lifecycle identity. |
| `scope_identity` | bounded canonical mapping | yes | Non-null; exact five-key mapping in Section 5.2; no nullable members. | Exact Risk/Capital scope. |
| `contract_version` | canonical text | yes | Non-null; exactly `p08-risk-capital-authority-v1`. | Safe V1 Risk/Capital authority contract version. |
| `risk_governor_version` | canonical text | yes | Non-null; trimmed, non-empty, bounded UTF-8 text. | Exact Risk Governor version. |
| `capital_authorization_version` | canonical text | yes | Non-null; trimmed, non-empty, bounded UTF-8 text. | Exact capital-authorization version. |
| `authorization_effect` | canonical text | yes | Non-null; exactly `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`. | Fixed paper-only effect. |
| `evaluator_version` | canonical text | yes | Non-null; exactly `p08-risk-capital-authority-evaluator-v1`. | Safe V1 evaluator version. |
| `reference_digest` | lowercase SHA-256 text | derived and verified | Non-null after derivation; exactly 64 lowercase hexadecimal characters. | Digest of every other reference field. |

No additional semantic fields are permitted. In particular, the reference
contains no provider, wallet, account, key, signer, order, transaction,
settlement, accounting, valuation, realized P&L, ROI, or classification field.

This twelve-field schema is the one canonical P07/G1 reference schema. It
matches the current P07 field names and types and does not introduce a second
reference-schema version. The complete Risk/Capital result remains the source
for required linked provenance that is intentionally not duplicated in this
bounded reference:

| Result-only linked provenance | Type | Required/null policy |
|---|---|---|
| `policy_snapshot_id` | canonical text | Required and non-null in the complete result. |
| `policy_snapshot_digest` | lowercase SHA-256 text | Derived, verified, required, and non-null in the complete result. |
| `simulation_reference_time` | timezone-aware UTC timestamp | Required and non-null in the complete result. |
| `valid_from` | timezone-aware UTC timestamp | Required and non-null in the complete result. |
| `valid_until` | timezone-aware UTC timestamp | Required and non-null for an approved result. |

These result-only fields are verified against the supplied P07
`simulation_reference_time` and observation validity fields. They are not
reconstructed from the reference and are not nullable substitutes for missing
reference fields. The complete result and the observation must be supplied to
G1; the reference alone never proves those result-only fields.

The reference is created by the value-preserving handoff from the actual
immutable Risk/Capital result. Its construction must preserve:

```text
result.authorization_id              → reference.authorization_id
result.digest                        → reference.authorization_digest
result.decision_intent_digest        → reference.decision_intent_digest
result.context_digest                → reference.context_digest
result.paper_lifecycle_id            → reference.paper_lifecycle_id
result.scope_identity                → reference.scope_identity
result.contract_version              → reference.contract_version
result.provenance.risk_governor_version
                                     → reference.risk_governor_version
result.provenance.capital_authorization_version
                                     → reference.capital_authorization_version
result.authorization_effect          → reference.authorization_effect
result.evaluator_version             → reference.evaluator_version
```

A raw generic status, an observation ID, or an independently typed digest pair
does not prove an approval. Where the complete Risk/Capital result is
available, the validator must compare every copied field and both digests. G1
must continue to receive and independently validate the complete result.

### 5.2 Scope identity

`scope_identity` contains exactly:

| Field | Type | Required |
|---|---|---:|
| `paper_lifecycle_id` | canonical text | yes |
| `paper_portfolio_id` | canonical text | yes |
| `candidate_id` | canonical text | yes |
| `chain_id` | canonical text | yes |
| `token_identity` | canonical text | yes |

The reference must satisfy:

```text
reference.paper_lifecycle_id
    == reference.scope_identity["paper_lifecycle_id"]
reference.scope_identity
    == Risk/Capital result.scope_identity
reference.scope_identity
    == P06-derived P07 admission scope
```

`chain_id` and `token_identity` are identity values only. They do not cause
chain, provider, RPC, DEX, wallet, or network access.

### 5.3 Reference invariants

The reference is valid only when:

1. every digest is exactly 64 lowercase hexadecimal characters;
2. every text field is non-empty, bounded, and canonical;
3. every nested mapping is recursively immutable and contains only allowed
   fields;
4. `contract_version` and `evaluator_version` are supported exactly;
5. `authorization_effect` is exactly
   `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`;
6. `reference_digest` equals the SHA-256 digest of the complete canonical
   reference excluding only `reference_digest`;
7. `authorization_id` equals the Risk/Capital result's authorization ID;
8. `authorization_digest` equals the Risk/Capital result's result digest;
9. both P06 digests equal the supplied immutable P06 intent and context;
10. lifecycle and scope values agree across P06, Risk/Capital, and P07;
11. authority and evaluator versions agree across the handoff;
12. the referenced result has `status == APPROVED`; and
13. where the complete result is supplied, its policy identity, policy digest,
    simulation reference time, and validity bounds are present, canonical,
    digest-valid, and agree with the P07 observation;
14. the approval is valid at the explicit P07 simulation reference time.

P07 validates the reference and its duplicated identity links. P07 does not
re-evaluate Risk/Capital predicates. G1 validates the complete authorization
result and the reference independently before recognition.

## 6. P06 → Risk/Capital → P07 linkage invariants

A v2 required-entry admission is valid only when the following graph is exact:

```text
P06 DecisionIntent
  intent.digest
        ==
Risk/Capital result.decision_intent_digest
        ==
reference.decision_intent_digest
        ==
P07 decision_intent.decision_intent_digest

P06 context.digest
        ==
Risk/Capital result.context_digest
        ==
reference.context_digest
        ==
P07 decision_intent.context_digest

Risk/Capital result.authorization_id
        ==
reference.authorization_id
        ==
P07 authorization_observation.observation_id

Risk/Capital result.digest
        ==
reference.authorization_digest

Risk/Capital result.scope_identity
        ==
reference.scope_identity
        ==
P07 authorization_observation.scope_identity
```

The following values must also agree:

- paper lifecycle identity;
- candidate identity;
- chain identity;
- token identity;
- paper portfolio identity;
- Risk Governor version;
- capital-authorization version;
- Risk/Capital contract version;
- Risk/Capital evaluator version; and
- fixed authorization effect.

The following complete-result fields are also required for the linked path but
are not duplicated in the twelve-field reference:

```text
Risk/Capital result.policy_snapshot_id
Risk/Capital result.policy_snapshot_digest
Risk/Capital result.simulation_reference_time
Risk/Capital result.valid_from
Risk/Capital result.valid_until
```

They must be copied or verified from the actual immutable result and compared
to the P07 observation and input cutoff. A missing or contradictory result-only
field fails closed; P07 and G1 must not infer it from an ID, digest, label, or
timestamp.

The P07 observation is a value-preserving handoff, not a new approval. P07
must not accept an observation whose ID, digest, status, scope, validity,
version, reason, or reference differs from the actual Risk/Capital result.

P06 remains analytical intent, not authorization or an order. Risk/Capital
remains the sole Safe V1 admission authority. P07 remains the owner of
paper-simulation input and later paper artifacts.

## 7. Admission states and temporal rules

### 7.1 Approved admission

A new v2 Safe V1 paper-entry admission requires all of:

```text
contract_version == p07-t01-v2
P06 DecisionIntent is valid and supported
authorization_observation.status == PASS
authorization_reference is present and valid
Risk/Capital result.status == APPROVED
P06/Risk/Capital/P07 identity links match exactly
reference_digest and observation_digest validate
simulation_reference_time is explicit UTC
reference validity covers simulation_reference_time
all other P07 envelopes are valid and available
```

The resulting input is paper-simulation context only. It is not permission to
execute, submit, sign, broadcast, settle, account, or trade.

### 7.2 Rejected and unknown observations

`FAIL` and `UNKNOWN` are preserved. They cannot be upgraded to `PASS`,
`APPROVED`, or `NOT_REQUIRED` by P07 or G1.

For a required Safe V1 paper-entry scenario:

- missing observation fails closed;
- `NOT_REQUIRED` fails closed;
- `FAIL` fails closed;
- `UNKNOWN` fails closed;
- an expired `PASS` fails closed;
- a future-dated `PASS` fails closed; and
- a contradictory `PASS` fails closed.

### 7.3 Cutoff and validity

All temporal decisions use supplied values only:

```text
P06 context.reference_time
    <= P06 decision_time
    <= P07 simulation_reference_time

authorization_observation.observed_at
    <= P07 simulation_reference_time

authorization.valid_from
    <= P07 simulation_reference_time
    <= authorization.valid_until

execution.observation_time
    <= execution.availability_time
    <= P07 simulation_reference_time

initial_paper_state.as_of_time
    <= P07 simulation_reference_time
```

The sole P07 cutoff source is
`PaperSimulationInput.simulation_reference_time`. Every timestamp above must be
timezone-aware, normalized to UTC, and compared as an instant. A future
authorization is any supplied `observed_at` or `valid_from` strictly greater
than the cutoff. It fails with `AUTHORIZATION_FUTURE_DATED`. An authorization
is stale when `valid_until` is strictly less than the cutoff. It fails with
`AUTHORIZATION_STALE`. The equality boundaries are valid:
`observed_at == cutoff`, `valid_from == cutoff`, and `valid_until == cutoff`
are not future or stale.

Missing, malformed, naive, offset-invalid, or otherwise non-canonical cutoff
material fails with `REFERENCE_TIME_INVALID` under the fixed precedence.
Missing or malformed authorization validity fields use the applicable missing,
invalid, or non-canonical category before temporal classification. No wall-clock
call, external lookup, or freshness inference is permitted.

## 8. Canonical serialization and digest rules

### 8.1 Canonical representation

The v2 input, observation, reference, and inherited nested envelopes use the
project's canonical representation:

- mappings use sorted string keys;
- tuples and lists use fixed ordered arrays;
- sets are forbidden;
- enum values use explicit wire strings;
- timestamps are timezone-aware and serialized as canonical UTC ISO-8601
  values;
- decimal values are finite normalized decimal text;
- binary floating-point values are rejected;
- NaN and infinity are rejected;
- text is trimmed, non-empty, bounded UTF-8 text;
- nullable fields use explicit `null`, never omission;
- unknown fields are rejected;
- non-string mapping keys are rejected;
- opaque objects, callbacks, handles, and executable values are rejected; and
- SHA-256 is computed over compact UTF-8 JSON with sorted keys and no
  insignificant whitespace.

Equivalent mapping order, equivalent normalized decimal text, equivalent UTC
timestamps, and equivalent Unicode normalization must produce identical
canonical representations and digests.

There is no absent-versus-null equivalence. Every allowed nullable field is
present as either its canonical value or explicit `null`.

### 8.2 Digest coverage

Digest coverage is:

```text
reference_digest
    = SHA-256(canonical reference excluding reference_digest)

observation_digest
    = SHA-256(canonical observation excluding observation_digest,
              including complete reference or explicit null)

input_digest
    = SHA-256(canonical P07-T01 input excluding input_digest,
              including complete observation and reference)
```

Nested digests must be recomputed and verified before a parent digest is
accepted. A supplied digest never overrides its source representation.

Changing any of the following changes the relevant digest:

- P06 intent or context identity;
- Risk/Capital authorization identity or result digest;
- lifecycle or scope;
- authority, evaluator, Risk Governor, or capital version;
- authorization effect;
- observation status or validity;
- reference canonical fields;
- execution observation;
- simulation configuration;
- initial paper state;
- simulation cutoff; or
- replay identity.

### 8.3 Immutability

The outer input, observation, reference, nested mappings, sequences, timestamps,
and canonical representations are recursively immutable after construction.

Caller mutation attempts must not alter:

- reference identity;
- observation identity;
- P07 input identity;
- nested provenance;
- P07 result identity;
- history ordering or digest; or
- G1 recognition result.

## 9. Provenance propagation

### 9.1 P07-T01

P07-T01 must retain the complete linked provenance:

```text
P06 decision_intent_digest
P06 context_digest
P06 candidate/chain/token identity
Risk/Capital authorization_id
Risk/Capital authorization_digest
Risk/Capital paper_lifecycle_id
Risk/Capital scope_identity
Risk/Capital contract_version
Risk/Capital evaluator_version
Risk Governor version
capital-authorization version
authorization_effect
reference_digest
observation_digest
input_digest
```

The twelve reference fields above are the complete reference-carried
provenance. The following result-only fields are required linked provenance and
must remain available through the separately supplied complete Risk/Capital
result and its value-preserving observation handoff:

```text
policy_snapshot_id
policy_snapshot_digest
simulation_reference_time
valid_from
valid_until
```

P07-T01 retains the reference-carried fields in the observation and input
digests. It retains the result-only fields by requiring the linked handoff to
validate them before admission; it does not copy them into the reference or
reconstruct them later. P07-T06 preserves the T01 input digest, and P07-T07
preserves the T06 result and its input digest, so the complete v2 linkage is
protected transitively without changing the v1 T06/T07 field contracts.

No link is reconstructed from a partial field. No link is dropped because a
generic observation also contains a matching label.

### 9.2 P07-T02 through P07-T06

The P07-T01 `input_digest` remains the predecessor identity for the later
paper lifecycle:

```text
T01 input_digest
   → T02 fill/outcome provenance
   → T03 transition provenance
   → T04 ledger provenance
   → T05 reconciliation provenance
   → T06 PaperSimulationResult.input_digest
```

P07-T06 remains `p07-t06-v1`, immutable and non-economic. It preserves the
input, fill, transition, ledger, reconciliation, status, quantities, paper
state, provenance, and result digest. It does not recreate or re-evaluate the
Risk/Capital authorization.

### 9.3 P07-T07 history

P07-T07 remains `p07-t07-v1`, immutable and local. It stores only an actual
validated T06 result and retains the T06 `input_digest`, which transitively
protects the P07 reference.

History ordering is canonical, not insertion-based. Existing repeated-input
rules remain:

- exact repeated accepted input produces
  `SIMULATION_INPUT_ALREADY_STORED`;
- a different result for an existing input digest produces
  `CONTRADICTORY_SIMULATION_INPUT`;
- neither rejection mutates the accepted history.

No history operation infers, repairs, migrates, or substitutes Risk/Capital
evidence.

### 9.4 G1

G1 recognition requires the complete current linked chain:

```text
actual APPROVED Risk/Capital result
  + exact immutable reference
  + exact P06-linked p07-t01-v2 input
  + valid T02 through T06 chain
  + valid p07-t07-v1 history
  + complete P08 predecessor chain
  → possible G1 recognition
```

G1 must validate the actual Risk/Capital result independently of the reference.
The reference alone is not a substitute for the result at G1.

Legacy v1 and generic PASS material cannot produce:

```text
RECOGNIZED / FINAL / RECOGNIZED_COMPLETE
```

No G1 result means settled, realized, accounted, valued, profitable, loss,
win, breakeven, or live.

## 10. Duplicate, replay, and contradiction rules

The contract is stateless. It introduces no registry, cache, database,
filesystem lookup, queue, or external duplicate service.

### 10.1 Equivalent replay

Identical canonical v2 input produces identical:

- canonical representation;
- nested reference and observation digests;
- top-level input digest;
- validation result;
- failure reason;
- identity links; and
- provenance.

Replay identity is input data, not permission to change any field.

### 10.2 Duplicate evidence

The validator rejects:

- multiple reference representations for one observation that differ in any
  field;
- two authorizations for one lifecycle with conflicting IDs or digests;
- a repeated input with a changed authorization reference;
- a duplicate reference presented under a changed P06 identity;
- a reference with a duplicate lifecycle but different policy/result identity;
  and
- a legacy v1 artifact presented as a v2 admission.

### 10.3 Contradictory evidence

The validator rejects contradictions among:

- P06 intent and context digests;
- P06 candidate, chain, token, or decision values;
- authorization ID and observation ID;
- authorization digest and reference digest;
- lifecycle and scope identity;
- authority, evaluator, Risk Governor, or capital versions;
- authorization effect;
- status, reason, and unknown-reason fields;
- validity timestamps and simulation cutoff; and
- supplied actual authorization result and reference.

Caller order, insertion order, retrieval order, freshness preference, numeric
magnitude, and status labels never resolve a contradiction.

## 11. Closed admission reason vocabulary and precedence

### 11.1 P07-T01 v2 admission vocabulary

The bounded P07-T01 v2 admission vocabulary is:

```text
INVALID_TYPE
MISSING_REQUIRED_INPUT
INVALID_INPUT
UNSUPPORTED_VERSION
NON_CANONICAL_INPUT
DIGEST_MISMATCH
PROVENANCE_LINKAGE_FAILURE
CONTRADICTORY_INPUT
SCOPE_MISMATCH
REFERENCE_TIME_INVALID
AUTHORIZATION_NOT_APPROVED
AUTHORIZATION_STALE
AUTHORIZATION_FUTURE_DATED
DUPLICATE_LIFECYCLE_CONFLICT
REPLAY_IDENTITY_CONFLICT
```

`INVALID_TYPE` is used for a value outside the contract's immutable type
boundary. `MISSING_REQUIRED_INPUT` is used for absent v2 admission material,
including a missing required reference. `INVALID_INPUT` is used for an
explicitly invalid state that is not more specifically classified.

The existing Safe V1 Risk/Capital reason vocabulary remains authoritative for
the Risk/Capital evaluator itself. P07 does not rename or reinterpret those
reasons.

The existing P07-T07 history vocabulary remains authoritative for history
outcomes, including `SIMULATION_INPUT_ALREADY_STORED` and
`CONTRADICTORY_SIMULATION_INPUT`.

### 11.2 P07 admission precedence

Exactly one P07 admission reason is selected. When multiple failures apply, the
first applicable category wins:

1. `INVALID_TYPE`
2. `MISSING_REQUIRED_INPUT`
3. `INVALID_INPUT`
4. `UNSUPPORTED_VERSION`
5. `NON_CANONICAL_INPUT`
6. `DIGEST_MISMATCH`
7. `PROVENANCE_LINKAGE_FAILURE`
8. `CONTRADICTORY_INPUT`
9. `SCOPE_MISMATCH`
10. `REFERENCE_TIME_INVALID`
11. `AUTHORIZATION_NOT_APPROVED`
12. `AUTHORIZATION_STALE`
13. `AUTHORIZATION_FUTURE_DATED`
14. `DUPLICATE_LIFECYCLE_CONFLICT`
15. `REPLAY_IDENTITY_CONFLICT`

Within one category, fields are checked in fixed contract order. No reason is
selected by caller order, object insertion order, wall-clock time, or external
state.

### 11.3 G1 mapping

G1 retains its existing closed reason vocabulary and precedence:

```text
INVALID_TYPE
MISSING_REQUIRED_INPUT
UNSUPPORTED_VERSION
INVALID_CANONICAL_REPRESENTATION
DIGEST_FAILURE
INVALID_IDENTITY_LINK
INVALID_LIFECYCLE
PROVENANCE_FAILURE
CONTRADICTORY_INPUT
STALE_INPUT
UNKNOWN_INPUT
UNAVAILABLE_INPUT
INCOMPLETE_INPUT
PARTIAL_INPUT
UNFILLED_INPUT
FAILED_INPUT
NON_FINAL_INPUT
UNSUPPORTED_SIMULATION_STATE
UNRESOLVED_CORRECTION
UNRESOLVED_SUPERSESSION
DETERMINISM_FAILURE
```

For this contract:

- legacy `p07-t01-v1` in the current recognition path maps to
  `UNSUPPORTED_VERSION`;
- v2 missing reference always maps to `MISSING_REQUIRED_INPUT`, before
  `INVALID_IDENTITY_LINK`, regardless of which internal validator notices it;
- v2 reference/result/P06 mismatch maps to `INVALID_IDENTITY_LINK`;
- reference or result digest tampering maps to `DIGEST_FAILURE`;
- contradictory lifecycle/history material maps to
  `CONTRADICTORY_INPUT`; and
- stale or future-inconsistent linked material maps to `STALE_INPUT`.

G1 emits exactly one reason and never repairs, filters, downgrades, or
substitutes failed evidence.

## 12. Fail-closed behavior matrix

| Condition | Direct v2 P07 admission | G1 current-recognition path |
|---|---|---|
| Missing authorization observation | `MISSING_REQUIRED_INPUT` | `MISSING_REQUIRED_INPUT` |
| Generic `PASS` without reference | `MISSING_REQUIRED_INPUT` | `MISSING_REQUIRED_INPUT` |
| Missing actual Risk/Capital result | P07 may validate only the bounded handoff; no approval is implied | `MISSING_REQUIRED_INPUT` |
| Reference ID differs from observation ID | `PROVENANCE_LINKAGE_FAILURE` | `INVALID_IDENTITY_LINK` |
| Reference P06 digest differs | `PROVENANCE_LINKAGE_FAILURE` | `INVALID_IDENTITY_LINK` |
| Reference scope/lifecycle differs | `SCOPE_MISMATCH` | `INVALID_IDENTITY_LINK` |
| Reference digest tampered | `DIGEST_MISMATCH` | `DIGEST_FAILURE` |
| Authorization result digest differs | `DIGEST_MISMATCH` | `DIGEST_FAILURE` |
| `FAIL`, `UNKNOWN`, or required-path `NOT_REQUIRED` | `AUTHORIZATION_NOT_APPROVED` | `FAILED_INPUT`, `UNKNOWN_INPUT`, or `INVALID_IDENTITY_LINK` by predecessor state |
| Expired approval | `AUTHORIZATION_STALE` | `STALE_INPUT` |
| Future-dated approval or observation | `AUTHORIZATION_FUTURE_DATED` | `STALE_INPUT` |
| Unsupported v2/reference version | `UNSUPPORTED_VERSION` | `UNSUPPORTED_VERSION` |
| Legacy v1 artifact | legacy reader only | `NOT_RECOGNIZED / NOT_APPLICABLE / UNSUPPORTED_VERSION` |
| Duplicate or contradictory lifecycle | duplicate/contradiction reason by precedence | `CONTRADICTORY_INPUT` |

No fail-closed condition returns a valid admission. No rejected or legacy
artifact is upgraded by later evidence.

## 13. Authority boundaries and explicit non-goals

### 13.1 Ownership

- **P05:** opportunity context and hard-risk viability.
- **P06:** analytical `DecisionIntent`; not authorization and not an order.
- **Risk/Capital Safe V1:** deterministic approval or rejection of one
  identity-linked paper lifecycle entry.
- **P07-T01:** validates and preserves the exact Risk/Capital handoff and paper
  simulation input; it does not create or evaluate Risk/Capital authorization.
- **P07-T02 through T07:** paper observation, fill, state transition, ledger,
  reconciliation, canonical non-economic result, and local history.
- **P08-T01 through T06:** read-only outcome-learning predecessor boundaries.
- **G1:** simulation-only recognition and simulation finality.
- **G2/G3/G4/P09:** separately governed and not authorized.

### 13.2 Prohibited behavior

This specification does not authorize:

- providers, exchanges, venues, RPC, networks, DEXs, or external APIs;
- wallets, custody, accounts, keys, seed phrases, or signers;
- signing, broadcast, live orders, execution, retries, or settlement;
- accounting, valuation, realized P&L, ROI, cost basis, or classification;
- G2 realization authority;
- G3 accounting authority;
- G4 performance classification;
- P09 live execution;
- database, migration, cache, registry, queue, or persistence behavior;
- wall-clock or external-state lookup;
- automatic legacy migration, inference, reconstruction, or substitution; or
- a new P07 simulation engine.

A valid v2 input is necessary paper-simulation context only. It is not
permission to execute anything.

## 14. Future implementation and focused-test scope

No implementation is authorized by this specification. After formal audit, a
separate limited implementation authorization may name only these existing
eight files:

### 14.1 Source files

1. `core/execution/paper_simulation_input.py`
2. `core/execution/paper_simulation_result.py`
3. `core/execution/paper_simulation_result_history.py`
4. `core/learning/g1_simulation_only_economic_authority.py`

### 14.2 Focused test files

5. `tests/test_paper_simulation_input.py`
6. `tests/test_paper_simulation_result.py`
7. `tests/test_paper_simulation_result_history.py`
8. `tests/test_g1_simulation_only_economic_authority.py`

No other source or test file is in the future implementation scope. The
Risk/Capital implementation and its focused tests remain separately governed
and are not changed by this P07 admission correction.

### 14.3 Required future tests

The authorized future focused suite must cover:

1. valid v2 construction from an actual approved Risk/Capital result;
2. exact reference field preservation and recursive immutability;
3. exact P06 intent and context digest linkage;
4. exact authorization ID, result digest, lifecycle, scope, and version
   linkage;
5. generic `PASS` without a reference fails at P07 admission;
6. missing observation and required-path `NOT_REQUIRED` fail closed;
7. `FAIL` and `UNKNOWN` cannot be upgraded;
8. mismatched P06, scope, lifecycle, ID, version, effect, or digest fails
   closed;
9. reference, observation, nested, and top-level digest tampering fails closed;
10. unsupported versions fail closed;
11. stale, expired, future-dated, and impossible timestamp relationships fail
    closed;
12. canonical key ordering, Unicode normalization, UTC timestamp,
    normalized-decimal, explicit-null, float rejection, and digest stability;
13. equivalent v2 replay produces identical validation and digests;
14. duplicate and contradictory references select the fixed reason;
15. P07-T06 preserves the v2 input digest and linked provenance;
16. P07-T07 preserves identity, rejects duplicate input, and rejects
    contradictory repeated input;
17. legacy v1 remains readable only as legacy evidence and is refused by G1
    with `NOT_RECOGNIZED / NOT_APPLICABLE / UNSUPPORTED_VERSION`;
18. v2 missing or mismatched reference is refused by G1 and cannot recognize;
19. the real opportunity/risk → P06 → Risk/Capital → P07 → P07 result/history
    → P08 → G1 composition remains recognized only when fully linked; and
20. no test introduces provider, wallet, signer, live execution, settlement,
    accounting, realized P&L, classification, G2, G3, G4, or P09 behavior.

## 15. Separate governance gates

The following gates are separate:

### Gate 1 — Specification audit

The formal audit must verify:

- exact v2 field names and requiredness;
- exact reference fields and types;
- P06/Risk/Capital/P07 linkage;
- legacy v1 refusal;
- canonicalization, null, ordering, and digest coverage;
- immutability and replay;
- duplicate and contradiction behavior;
- stale, future, unsupported, and tampered behavior;
- reason vocabulary and precedence;
- P07-T06/T07/G1 propagation; and
- continued paper-only boundaries.

### Gate 2 — Limited implementation authorization

Only after Gate 1 passes may a separate authorization name the eight files in
Section 14 and permit the v2 requiredness/linkage correction. That authorization
must prohibit source, test, dependency, environment, provider, wallet, live,
economic, G2, G3, G4, and P09 expansion.

### Gate 3 — Implementation audit

After authorized implementation, a separate audit must verify the focused tests,
compile checks, canonical/digest behavior, complete linkage, legacy refusal, and
scope integrity. Passing tests alone do not close the contract.

No gate is satisfied by this specification alone.

## 16. Acceptance and completion criteria

This specification task is complete when:

- this document is marked `SPECIFICATION CORRECTED / AWAITING FORMAL RE-AUDIT`;
- the exact v2 and reference contracts are documented;
- legacy handling and exact G1 refusal are documented;
- propagation and fail-closed behavior are documented;
- the eight-file future scope is documented;
- the separate implementation-authorization gate is documented;
- `PROJECT_STATE.md` remains unchanged until the formal re-audit passes; the
  synchronized state sentence is not part of this correction;
- no runtime, test, dependency, environment, provider, or future-phase file is
  changed by this specification task; and
- no commit or push is performed.

P07 v2 implementation remains NOT AUTHORIZED until the formal audit and
separate limited implementation authorization pass.