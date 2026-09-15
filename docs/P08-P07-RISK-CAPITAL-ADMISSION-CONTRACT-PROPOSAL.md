# P08 — P07 Risk/Capital Admission Contract Proposal

**Status:** DOCUMENTATION-ONLY PROPOSAL / IMPLEMENTATION NOT AUTHORIZED  
**Phase:** P08 — Outcome Learning  
**Project:** MemeCoinHunterAI  
**Boundary:** P06 `DecisionIntent` → Risk/Capital paper admission → P07-T01  
**Purpose:** Resolve blocker B-01 from the paper-lifecycle readiness re-audit

## 1. Executive proposal

P07-T01 currently accepts a structurally valid generic `PASS`
`AuthorizationObservation` without proving that the observation came from the
exact Risk/Capital approval for the same P06 `DecisionIntent`. The existing
linked path is valid when `RiskCapitalAuthorizationReference` is present, and
G1 already fails closed when the reference or the complete Risk/Capital result
is absent. The remaining gap is that P07 admission itself does not require the
reference.

This proposal defines Safe V1 for the future P07 admission contract:

1. every new Risk/Capital-gated P07-T01 admission requires one immutable,
   canonical `RiskCapitalAuthorizationReference`;
2. the reference identifies the exact Risk/Capital authorization identity and
   result digest;
3. the reference carries the exact P06 `DecisionIntent` identity and context
   digest to which that authorization applies;
4. a generic `PASS` observation without that reference is insufficient;
5. missing, mismatched, stale, tampered, unsupported, duplicate, and
   contradictory material fails closed;
6. legacy P07 artifacts remain readable as legacy evidence only and can never
   become G1-recognized through inference or automatic migration; and
7. no P07, Risk/Capital, G1, provider, live, settlement, accounting, or
   classification authority is expanded by this proposal.

This document defines a future contract and its verification scope. It does not
authorize source changes, test changes, migration, runtime release, or a
project-state update.

## 2. Current blocker and evidence

The current implementation has the following useful behavior:

- `RiskCapitalAuthorizationReference` is an immutable value object.
- It preserves the authorization ID and digest, P06 intent and context
  digests, lifecycle and scope, authority versions, the fixed
  `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY` effect, and its own digest.
- `AuthorizationObservation.from_risk_capital_result()` creates the reference
  from the actual Risk/Capital result.
- `PaperSimulationInput` validates the reference against the P06 intent when a
  reference is supplied.
- G1 independently validates the complete Risk/Capital result, the reference,
  the observation handoff, and the P06 linkage.

The remaining deficiency is:

- `AuthorizationObservation.authorization_reference` is optional;
- `PaperSimulationInput` validates the P06 linkage only when the optional
  reference is present; and
- a generic `PASS` observation without the reference remains constructible.

This contradicts the intended required paper-entry path, where Safe V1
Risk/Capital approval is the only authority that may admit one identity-linked
P07 paper lifecycle. The exact linked path is implemented, but the admission
boundary still permits an unlinked structural substitute.

## 3. Safe V1 contract identity and compatibility

### 3.1 New contract versions

The proposed contract introduces:

```text
P07-T01 contract version:
    p07-t01-v2

RiskCapitalAuthorizationReference contract:
    p07-risk-capital-authorization-reference-v1
```

Making the reference mandatory changes P07-T01 field requiredness and digest
material. It therefore requires a new P07-T01 contract version rather than
silently changing the meaning of `p07-t01-v1`.

The Risk/Capital authority contract remains:

```text
p08-risk-capital-authority-v1
```

and its fixed effect remains:

```text
PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
```

The reference version identifies the reference schema. It does not create a
second Risk/Capital evaluator or authorize P07 to make a Risk/Capital
decision.

### 3.2 Legacy compatibility boundary

Existing `p07-t01-v1` artifacts without a
`RiskCapitalAuthorizationReference` are legacy evidence. They may be:

- read;
- inspected;
- retained for historical documentation; and
- used by explicitly versioned legacy-evidence tooling.

They may not be:

- automatically migrated to `p07-t01-v2`;
- repaired by copying fields from a digest, timestamp, label, or observation;
- inferred to contain Risk/Capital approval;
- substituted with a newly constructed reference;
- accepted as a new Risk/Capital-gated P07 admission; or
- recognized by G1 as a complete current paper lifecycle.

No compatibility rule may reinterpret a `p07-t01-v1` digest under the v2
canonicalization or required-field rules. A future G1 implementation/specification
update must explicitly recognize only the linked v2 admission path for current
recognition. A legacy artifact without the reference must produce a
deterministic non-recognition outcome, such as `UNSUPPORTED_VERSION` or
`MISSING_REQUIRED_INPUT` under the approved G1 mapping, never
`RECOGNIZED / FINAL`.

There is no automatic migration path. If a legacy lifecycle is ever to be
re-admitted, that requires a separately approved migration contract with explicit
source evidence, identity rules, versioned canonicalization, focused tests, and
its own audit. This proposal does not define or authorize that migration.

## 4. `RiskCapitalAuthorizationReference`

### 4.1 Purpose

`RiskCapitalAuthorizationReference` is a bounded immutable reference to one
specific, already materialized Risk/Capital authorization result. It is not an
authorization, a new approval, an order, a quote, a position, or an execution
request.

The reference must be produced from the actual immutable
`PaperRiskCapitalAuthorizationResult` through the approved value-preserving
handoff. P07-T01 does not recalculate Risk/Capital predicates and does not
select, renew, repair, reduce, or replace an authorization.

A raw ID/digest pair supplied as an unverified assertion is not sufficient to
manufacture a new approval. A future implementation must provide either:

1. a construction path that derives the reference only from an actual
   validated Risk/Capital result; or
2. a validation boundary that receives the complete referenced result and
   verifies the reference against it.

P07-T01 remains a consumer of the reference. G1 remains responsible for the
independent verification of the complete Risk/Capital result and its exact
observation handoff before recognition.

### 4.2 Required fields

The v1 reference contains exactly these semantic fields:

| Field | Required | Meaning |
|---|---:|---|
| `contract_version` | yes | `p07-risk-capital-authorization-reference-v1`. |
| `authorization_id` | yes | Exact Risk/Capital authorization identity. |
| `authorization_digest` | yes | SHA-256 digest of the complete Risk/Capital result. |
| `decision_intent_digest` | yes | Exact P06 `DecisionIntent` digest. |
| `context_digest` | yes | Exact P06 context digest. |
| `policy_snapshot_id` | yes | Exact consumed policy snapshot identity. |
| `policy_snapshot_digest` | yes | Exact consumed policy snapshot digest. |
| `paper_lifecycle_id` | yes | Exact one-lifecycle identity. |
| `scope_identity` | yes | Complete Risk/Capital scope identity. |
| `simulation_reference_time` | yes | Risk/Capital result's supplied paper cutoff. |
| `valid_from` | yes | Result lower validity bound. |
| `valid_until` | yes | Result upper validity bound. |
| `risk_governor_version` | yes | Preserved Risk Governor version. |
| `capital_authorization_version` | yes | Preserved capital-authorization version. |
| `authority_contract_version` | yes | `p08-risk-capital-authority-v1`. |
| `authority_evaluator_version` | yes | `p08-risk-capital-authority-evaluator-v1`. |
| `authorization_effect` | yes | `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`. |
| `reference_digest` | derived and verified | Digest of every other reference field. |

No provider, wallet, account, signer, order, transaction, settlement, realized
P&L, accounting, valuation, classification, or external-state field is allowed.

The `scope_identity` must preserve the complete Safe V1 scope, including:

```text
paper_lifecycle_id
paper_portfolio_id
candidate_id
chain_id
token_identity
```

The scope is identity material only. `chain_id` does not select or contact a
chain or provider.

### 4.3 Reference invariants

The reference is valid only when all of the following hold:

1. `authorization_id` is a lowercase 64-character SHA-256 digest.
2. `authorization_digest` is a lowercase 64-character SHA-256 digest.
3. `decision_intent_digest` and `context_digest` are lowercase SHA-256
   digests.
4. `scope_identity.paper_lifecycle_id == paper_lifecycle_id`.
5. `scope_identity` is exactly the Safe V1 scope and contains no unknown keys.
6. `policy_snapshot_digest` is the digest used by the authorization identity.
7. `simulation_reference_time`, `valid_from`, and `valid_until` are explicit
   timezone-aware UTC values.
8. `valid_from <= simulation_reference_time <= valid_until`.
9. `authority_contract_version` and `authority_evaluator_version` are the
   supported Risk/Capital versions.
10. `authorization_effect` is exactly
    `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`.
11. `reference_digest` matches the complete canonical reference excluding only
    `reference_digest`.
12. The reference's P06 digests, scope, policy identity, and lifecycle identity
    match the actual Risk/Capital result when that result is supplied.
13. The reference's `authorization_id` matches the Risk/Capital identity
    derivation:

    ```text
    SHA-256(
      contract_version,
      paper_lifecycle_id,
      decision_intent_digest,
      policy_snapshot_digest,
      simulation_reference_time
    )
    ```

14. The referenced authorization status is `APPROVED` for a new paper-entry
    admission. A rejected authorization cannot be upgraded by the reference.

The reference does not replace validation of the full Risk/Capital result. It
preserves the exact result identity and digest so downstream boundaries can
verify the same approval rather than accept a generic status.

## 5. Required P07-T01 admission semantics

### 5.1 New Risk/Capital-gated admission

For `p07-t01-v2`, a new paper-simulation admission in the Safe V1
Risk/Capital-gated path must contain:

```text
one validated P06 DecisionIntent
one PASS AuthorizationObservation
one RiskCapitalAuthorizationReference
one exact P06 identity match
one exact scope/lifecycle match
one valid temporal window
one valid canonical input digest
```

The `PASS` observation is admissible only when:

```text
authorization_observation.authorization_reference is present
AND
reference.authorization_id == authorization_observation.observation_id
AND
reference.scope_identity == authorization_observation.scope_identity
AND
reference.decision_intent_digest
    == PaperSimulationInput.decision_intent.decision_intent_digest
AND
reference.context_digest
    == PaperSimulationInput.decision_intent.context_digest
AND
reference.contract_version
    == authorization_observation.contract_version
AND
reference.risk_governor_version
    == authorization_observation.risk_governor_version
AND
reference.capital_authorization_version
    == authorization_observation.capital_authorization_version
AND
reference.authorization_effect
    == PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
AND
reference is canonical, immutable, and digest-valid
```

A structurally valid generic `PASS` without the reference is rejected. Matching
only `observation_id`, scope, timestamps, or status is insufficient.

### 5.2 Non-admission states

`FAIL` and `UNKNOWN` remain explicit observations and cannot be upgraded. A
Risk/Capital-gated simulation input with either state is not simulatable and
does not become an admission through a reference.

`NOT_REQUIRED` remains a legacy or separately approved non-gated scenario state
only. It is never valid for the Safe V1 paper-entry path defined by the
Risk/Capital Authority specification. A new v2 input must carry an explicit
scenario contract proving that `NOT_REQUIRED` is applicable before it can be
accepted outside the Risk/Capital-gated path. This proposal does not create that
separate scenario contract.

### 5.3 P07 ownership remains unchanged

P07-T01:

- validates the supplied reference and identity links;
- does not create or evaluate Risk/Capital authorization;
- does not recompute Risk/Capital budget, exposure, risk, or action rules;
- does not turn P06 `BUY + WAIT` into an order or execution instruction;
- does not create fills, positions, ledgers, reconciliation, or results;
- does not contact providers, chains, wallets, signers, networks, or APIs; and
- does not grant live, settlement, accounting, or economic authority.

The reference proves which Risk/Capital result the observation claims to carry.
It does not make P07 the owner of that result.

## 6. Canonicalization, provenance, and digest rules

### 6.1 Canonical reference representation

The reference uses the existing project canonicalization rules:

- all allowed fields are explicit;
- unknown fields are rejected;
- mapping keys are sorted canonical strings;
- tuples are represented as ordered arrays;
- sets are forbidden;
- text is trimmed, non-empty, bounded UTF-8 text;
- timestamps are timezone-aware UTC values in one canonical ISO-8601 form;
- digests are lowercase hexadecimal SHA-256 text;
- nullable values are explicit `null` where permitted;
- opaque, executable, credential-bearing, or unbounded values are rejected;
- binary floating-point values, NaN, and infinity are rejected; and
- SHA-256 is computed over compact UTF-8 JSON with sorted keys and no
  insignificant whitespace.

The reference and every nested mapping or sequence are recursively immutable.
The P07 input digest covers the reference's complete canonical representation.
Changing any reference field therefore changes the P07 input identity.

### 6.2 Cross-boundary provenance

The new P07 input provenance must preserve:

```text
P06 DecisionIntent digest
P06 context digest
Risk/Capital authorization ID
Risk/Capital authorization result digest
Risk/Capital policy snapshot ID
Risk/Capital policy snapshot digest
paper lifecycle identity
scope identity
Risk Governor version
capital-authorization version
Risk/Capital contract and evaluator versions
fixed authorization effect
reference digest
```

The observation's canonical representation includes the reference. The
`PaperSimulationInput` canonical representation includes the observation, so
the linkage is protected by both the observation digest and the P07 input
digest. P07 and G1 must validate the supplied values; neither may reconstruct a
missing reference from partial fields.

### 6.3 Complete-result validation

Where the full `PaperRiskCapitalAuthorizationResult` is available, the
validation boundary must independently verify:

- the result's contract and evaluator versions;
- `status == APPROVED`;
- the result authorization ID;
- the result digest;
- the result's P06 intent and context digests;
- the lifecycle and scope identity;
- the policy snapshot identity and digest;
- the fixed paper-only effect;
- the result's observation handoff; and
- equality of every reference field copied from the result.

P07-T01 may store the bounded reference instead of duplicating the full result,
but storage is not proof of approval by itself. G1 must continue to require the
actual result and validate it independently before recognition.

## 7. Failure reasons and deterministic precedence

The future P07-T01 v2 admission validator should use stable, bounded reason
codes. The exact wire vocabulary requires approval in the formal specification
audit, but the proposal is:

```text
MISSING_REQUIRED_INPUT
UNSUPPORTED_VERSION
INVALID_CANONICAL_REPRESENTATION
DIGEST_MISMATCH
PROVENANCE_LINKAGE_FAILURE
CONTRADICTORY_INPUT
SCOPE_MISMATCH
REFERENCE_TIME_INVALID
AUTHORIZATION_NOT_APPROVED
AUTHORIZATION_STALE
LEGACY_ADMISSION_NOT_SUPPORTED
```

The proposed precedence is:

1. `MISSING_REQUIRED_INPUT`
2. `UNSUPPORTED_VERSION`
3. `INVALID_CANONICAL_REPRESENTATION`
4. `DIGEST_MISMATCH`
5. `PROVENANCE_LINKAGE_FAILURE`
6. `CONTRADICTORY_INPUT`
7. `SCOPE_MISMATCH`
8. `REFERENCE_TIME_INVALID`
9. `AUTHORIZATION_NOT_APPROVED`
10. `AUTHORIZATION_STALE`
11. `LEGACY_ADMISSION_NOT_SUPPORTED`

Within a category, the validator uses fixed field order, never mapping order,
caller order, insertion order, freshness preference, result magnitude, or
ambient state. It records no permissive fallback. A failed validation must not
produce an accepted P07 admission.

The future formal specification audit must reconcile these P07-specific codes
with the existing P07 and G1 reason vocabularies without changing the meaning
of the Risk/Capital reason contract. G1's existing `INVALID_IDENTITY_LINK`,
`MISSING_REQUIRED_INPUT`, `UNSUPPORTED_VERSION`, `DIGEST_FAILURE`, and
`CONTRADICTORY_INPUT` categories remain available at its own boundary.

## 8. Duplicate, replay, and contradiction behavior

The contract remains stateless. It introduces no registry, cache, database,
queue, filesystem lookup, or external duplicate service.

The validator must reject:

- two supplied reference representations for one observation that differ in
  any field;
- a reference whose lifecycle identity conflicts with the observation scope;
- a reference whose P06 digest conflicts with the supplied DecisionIntent;
- a reference whose context digest conflicts with the supplied context;
- a reference whose authorization ID conflicts with the observation ID;
- a reference whose authorization digest conflicts with the actual result when
  that result is supplied;
- a reference whose policy identity or digest conflicts with the actual result;
- a reference whose contract, evaluator, effect, or authority versions conflict
  with the observed handoff;
- a stale or future-dated reference;
- a duplicate lifecycle with a different authorization or policy digest; and
- a legacy v1 input presented as a new v2 admission.

Equivalent canonical v2 input replay is allowed to reproduce the same input
digest and validation outcome. A different authorization, policy snapshot,
P06 digest, lifecycle, scope, time, or reference digest is a different
identity and cannot be silently merged with the first.

No caller preference, timestamp, insertion order, or status value may select
between contradictory representations.

## 9. G1 recognition boundary

G1 must preserve the stronger rule already required by the paper-lifecycle
readiness re-audit:

```text
actual approved Risk/Capital result
    + exact immutable reference
    + exact P06-linked P07 input
    + complete P07 result/history
    + complete P08 chain
    → possible G1 recognition
```

The following must never produce
`RECOGNIZED / FINAL / RECOGNIZED_COMPLETE`:

- a generic P07 `PASS` with no reference;
- a legacy v1 P07 artifact without a reference;
- a reference without a matching actual Risk/Capital result;
- a reference for a different P06 DecisionIntent;
- a reference for a different lifecycle or scope;
- a stale, unsupported, tampered, or contradictory reference; or
- a P07 input that is otherwise structurally valid but not Risk/Capital-linked.

G1 remains a validation-only simulation boundary. It does not convert the
reference into settlement evidence, realized value, accounting input,
profitability, classification, or live permission.

## 10. Future implementation and focused test scope

Implementation is not authorized by this proposal. If separately authorized,
the smallest implementation scope should be limited to the P07/G1 files named
by the existing linkage-remediation authorization and their directly
corresponding focused tests. The Risk/Capital implementation and its focused
tests remain unchanged.

The focused test plan must include at least:

### Valid path

1. Build a real P06 `DecisionIntent`.
2. Evaluate the actual Safe V1 Risk/Capital authorization.
3. Create the observation through the value-preserving Risk/Capital handoff.
4. Create the reference from the actual authorization result.
5. Construct a v2 P07 input.
6. Verify the reference, observation, P06 identity, scope, lifecycle, versions,
   cutoff, and digests all agree.
7. Verify repeated evaluation produces identical canonical representation,
   input digest, identity, status, and reason.
8. Verify the reference and nested scope are recursively immutable.

### Required negative paths

9. Generic `PASS` without a reference is rejected at P07 admission.
10. Missing reference is rejected before any paper simulation can begin.
11. Mismatched P06 intent digest or context digest is rejected.
12. Mismatched lifecycle, candidate, chain, token, portfolio, or scope is
    rejected.
13. Mismatched authorization ID or result digest is rejected.
14. Tampered reference, observation, actual result, or P07 input digest is
    rejected.
15. Unsupported reference, authority, evaluator, or P07 contract version is
    rejected.
16. Expired, future-dated, or invalid reference timestamps are rejected.
17. `FAIL`, `UNKNOWN`, and prohibited `NOT_REQUIRED` paper-entry states remain
    fail closed.
18. Duplicate and contradictory reference fields produce deterministic reasons.
19. A legacy v1 artifact without the reference remains readable only as legacy
    evidence and is not G1-recognized.
20. G1 rejects a v1 legacy input, a v2 input without the reference, and a v2
    input whose reference does not match the actual authorization.
21. The real opportunity/risk → P06 → Risk/Capital → P07 → P07 result/history
    → G1 composition remains recognized only for the fully linked path.
22. No test introduces provider, wallet, signer, chain, network, live-order,
    settlement, accounting, realized P&L, classification, G2, G3, G4, or P09
    behavior.

## 11. Separate governance gates

This proposal does not authorize implementation. Before any code or test change:

1. the proposal must receive a formal specification audit;
2. the audit must approve the exact fields, versions, canonicalization, digest
   coverage, compatibility rule, reason vocabulary, and precedence;
3. the P07 and G1 supported-version tables must be reconciled explicitly;
4. a prospective limited implementation authorization must name exact files;
5. implementation and focused tests must remain within that file scope;
6. a fresh implementation audit must verify the complete linked path; and
7. `PROJECT_STATE.md` must remain unchanged until the required audit and
   separately governed closure decision pass.

No specification approval, audit, implementation authorization, or project-state
closure is implied by this proposal.

## 12. Authority boundaries and exclusions

Ownership remains:

- **P05:** normalized opportunity context and hard-risk viability.
- **P06:** analytical `DecisionIntent`, action, posture, assumptions,
  uncertainty, invalidation, confidence, decision time, and provenance.
- **Risk/Capital Safe V1:** deterministic admission of one identity-linked P07
  paper lifecycle.
- **P07-T01:** validation and preservation of the exact Risk/Capital reference
  and simulation input; not Risk/Capital decision-making.
- **P07-T02 through T07:** paper observations, state transitions, ledger,
  reconciliation, canonical non-economic result, and local history.
- **G1:** simulation-only recognition and simulation finality.
- **G2:** future realization and settlement eligibility.
- **G3:** future accounting and canonical economic-result calculation.
- **G4:** future performance classification.
- **P09:** separately governed live-execution chain.

This proposal does not authorize or imply:

- providers, exchanges, venues, RPC, networks, or external APIs;
- wallets, custody, accounts, keys, seed phrases, or signers;
- signing, broadcast, live orders, execution, retries, or settlement;
- accounting, valuation, realized P&L, ROI, cost basis, or classification;
- G2 realization authority;
- G3 accounting authority;
- G4 performance classification;
- P09 live execution;
- database, cache, queue, registry, or persistence behavior;
- automatic legacy migration or inference; or
- changes to `PROJECT_STATE.md`.

## 13. Proposal conclusion

The smallest contract-preserving correction for blocker B-01 is:

```text
new P07-T01 admission
    requires p07-t01-v2
    requires one immutable p07-risk-capital-authorization-reference-v1
    requires exact Risk/Capital identity and digest linkage
    requires exact P06 identity and context linkage
    rejects generic PASS, legacy promotion, and contradiction
    remains paper-only and provider-neutral
```

The existing P07/G1 implementation is not retroactively changed by this
document. Legacy artifacts remain evidence only. A future fully linked v2
artifact may be eligible for G1 recognition only after the separate
specification, authorization, implementation, testing, and audit gates pass.

## 14. Change control

This document creates exactly one proposed project file:

```text
docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-PROPOSAL.md
```

No source code, tests, dependencies, `.replit`, `PROJECT_STATE.md`, provider,
wallet, signer, exchange, chain, API, live-order, execution, settlement,
accounting, realized P&L, classification, G2, G3, G4, or P09 file is changed
or authorized by this proposal.

No commit or push is performed.