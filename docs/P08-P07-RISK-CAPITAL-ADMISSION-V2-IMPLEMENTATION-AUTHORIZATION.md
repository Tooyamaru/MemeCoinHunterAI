# P08 — P07 Risk/Capital Admission Safe V1 / `p07-t01-v2`
# Prospective Limited Implementation Authorization

**Authorization type:** Documentation-only prospective limited implementation authorization  
**Project:** MemeCoinHunterAI  
**Phase:** P08 — Outcome Learning  
**Boundary:** P06 `DecisionIntent` → Safe V1 Risk/Capital → P07-T01  
**Contract:** `p07-t01-v2`  
**Status:** AUTHORIZED FOR FUTURE LIMITED IMPLEMENTATION ONLY  
**Current implementation status:** NOT IMPLEMENTED BY THIS AUTHORIZATION  
**Nature:** Immutable, deterministic, provider-neutral, paper-first/paper-only

## 1. Authorization purpose

This document authorizes a future, narrowly scoped implementation of the
corrected P07 Risk/Capital admission contract. It closes the separate
implementation-authorization gate required by the audited specification while
preserving all existing authority boundaries.

The authorized correction is limited to making the exact immutable
`RiskCapitalAuthorizationReference` mandatory for a new Safe V1
Risk/Capital-gated P07-T01 admission under `p07-t01-v2`, and to preserving and
validating that linkage through the already existing P07 result/history and G1
recognition boundaries.

This document does not perform the implementation. It does not authorize a
runtime release, a project-state closure claim, a migration, or any behavior
outside the scope stated below.

## 2. Authorization basis

This authorization relies on the following completed governance materials:

1. `REPLIT_RULES.md`
2. `PROJECT_STATE.md`
3. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION.md`
4. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION-SECOND-REAUDIT.md`
5. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-PROPOSAL.md`
6. `docs/P08-PAPER-LIFECYCLE-END-TO-END-READINESS-REAUDIT.md`
7. `core/execution/paper_simulation_input.py`
8. `core/execution/paper_simulation_result.py`
9. `core/execution/paper_simulation_result_history.py`
10. `core/learning/g1_simulation_only_economic_authority.py`
11. Their directly relevant focused tests.

The second formal re-audit records:

```text
PASS — SPECIFICATION COMPLETE / CLOSED / AUDITED PASS
```

The corrected specification is the sole normative Safe V1 source. The
historical proposal is superseded and non-normative; its former eighteen-field
reference schema has no authority.

The current runtime remains the pre-v2 implementation. This authorization does
not retroactively change `p07-t01-v1`, and no v2 artifact may be produced until
the future implementation is completed and independently audited.

## 3. Exact future file scope

Future implementation is authorized only in these eight existing files:

### Source files

1. `core/execution/paper_simulation_input.py`
2. `core/execution/paper_simulation_result.py`
3. `core/execution/paper_simulation_result_history.py`
4. `core/learning/g1_simulation_only_economic_authority.py`

### Focused test files

5. `tests/test_paper_simulation_input.py`
6. `tests/test_paper_simulation_result.py`
7. `tests/test_paper_simulation_result_history.py`
8. `tests/test_g1_simulation_only_economic_authority.py`

No new source file, test file, helper file, fixture file, schema file,
migration, registry, provider adapter, dependency, or configuration file is
authorized. The Risk/Capital evaluator and its focused tests are separately
governed and must not be changed under this authorization.

## 4. Required future implementation behavior

The future implementation must enforce all of the following.

### 4.1 Version and requiredness

- New required-entry admissions must use exactly `p07-t01-v2`.
- A v2 Safe V1 paper-entry admission must contain one
  `AuthorizationObservation` with `status == PASS`.
- That observation must contain exactly one immutable, canonical
  `RiskCapitalAuthorizationReference`.
- A generic `PASS` without the reference must fail closed before a simulation
  lifecycle begins.
- `p07-t01-v1` remains legacy/read-only evidence only.
- A v1 artifact must never be promoted, repaired, inferred, reconstructed,
  merged, or substituted into a v2 admission.
- A v1 artifact presented to the current G1 recognition path must produce:

  ```text
  recognition_state = NOT_RECOGNIZED
  finality_state    = NOT_APPLICABLE
  reason_code       = UNSUPPORTED_VERSION
  ```

- A v2 artifact with a missing required reference must produce:

  ```text
  recognition_state = NOT_RECOGNIZED
  finality_state    = NOT_APPLICABLE
  reason_code       = MISSING_REQUIRED_INPUT
  ```

- A v2 artifact with a present but mismatched, invalid, or tampered reference
  must produce:

  ```text
  recognition_state = NOT_RECOGNIZED
  finality_state    = NOT_APPLICABLE
  reason_code       = INVALID_IDENTITY_LINK
  ```

`MISSING_REQUIRED_INPUT` must take precedence over
`INVALID_IDENTITY_LINK` when the required reference is absent.

### 4.2 Canonical reference and exact linkage

The implementation must preserve one immutable canonical reference with exactly
these twelve semantic fields:

```text
authorization_id
authorization_digest
decision_intent_digest
context_digest
paper_lifecycle_id
scope_identity
contract_version
risk_governor_version
capital_authorization_version
authorization_effect
evaluator_version
reference_digest
```

The reference must preserve the exact value-preserving handoff from the actual
Safe V1 Risk/Capital result:

```text
result.authorization_id
    → reference.authorization_id
result.digest
    → reference.authorization_digest
result.decision_intent_digest
    → reference.decision_intent_digest
result.context_digest
    → reference.context_digest
result.paper_lifecycle_id
    → reference.paper_lifecycle_id
result.scope_identity
    → reference.scope_identity
result.contract_version
    → reference.contract_version
result.provenance.risk_governor_version
    → reference.risk_governor_version
result.provenance.capital_authorization_version
    → reference.capital_authorization_version
result.authorization_effect
    → reference.authorization_effect
result.evaluator_version
    → reference.evaluator_version
```

The complete linked graph must remain exact:

```text
P06 DecisionIntent
  → actual APPROVED Risk/Capital result
  → exact immutable reference
  → p07-t01-v2 input
  → P07-T02 through P07-T07 artifacts
  → P08 predecessor chain
  → G1 simulation-only recognition
```

The implementation must verify, without reconstructing from partial fields:

- P06 intent and context digests;
- candidate, chain, token, lifecycle, and portfolio identity;
- authorization ID and complete-result digest;
- reference and observation scope identity;
- Risk Governor, capital-authorization, contract, and evaluator versions;
- the fixed effect `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`;
- `status == APPROVED` on the actual Risk/Capital result; and
- the complete result-only linked provenance, including policy identity,
  policy digest, simulation cutoff, and validity bounds.

P07 validates and preserves the handoff. It does not create, evaluate, renew,
reduce, replace, or reinterpret Risk/Capital authorization. G1 must continue to
validate the complete actual Risk/Capital result independently; the reference
alone is never proof of approval.

### 4.3 Fail-closed states

The implementation must reject or preserve, without upgrade or fallback:

- missing authorization observations;
- missing required references;
- generic `PASS` without a reference;
- `NOT_REQUIRED` on the required Safe V1 paper-entry path;
- `FAIL` and `UNKNOWN` observations;
- mismatched P06, Risk/Capital, lifecycle, scope, identity, version, effect,
  observation, or result material;
- unsupported versions;
- malformed, non-canonical, or unknown fields;
- invalid or tampered nested, reference, observation, result, or input digests;
- stale, expired, future-dated, or impossible timestamp relationships;
- duplicate lifecycle evidence with conflicting identity;
- duplicate references with differing fields;
- contradictory repeated simulation-input results; and
- any incomplete predecessor chain at G1.

No rejected, legacy, generic, or contradictory evidence may be upgraded by later
evidence, caller order, insertion order, freshness preference, or status label.

### 4.4 Canonicalization, digest, UTC, and immutability rules

The implementation must preserve the project’s canonical representation rules:

- sorted string mapping keys;
- fixed ordered arrays for sequences;
- no sets or non-string mapping keys;
- explicit wire strings for enum values;
- timezone-aware UTC timestamps;
- finite normalized decimal text;
- rejection of binary floating-point values, NaN, and infinity;
- trimmed, bounded, non-empty canonical text;
- explicit `null` rather than absent-versus-null equivalence;
- rejection of unknown fields and opaque executable values; and
- compact UTF-8 JSON with sorted keys and no insignificant whitespace for
  SHA-256 digests.

Digest coverage must remain:

```text
reference_digest
    = SHA-256(canonical reference excluding reference_digest)

observation_digest
    = SHA-256(canonical observation excluding observation_digest,
              including the complete reference or explicit null)

input_digest
    = SHA-256(canonical P07-T01 input excluding input_digest,
              including the complete observation and reference)
```

Nested digests must be validated before parent digests. The outer input,
observation, reference, nested mappings, sequences, timestamps, and canonical
representations must remain recursively immutable after construction.

All temporal decisions must use supplied values only. The sole P07 cutoff is
`PaperSimulationInput.simulation_reference_time`; no system clock, external
lookup, freshness inference, or ambient state is allowed. UTC equality at the
validity boundaries remains valid:

```text
observed_at == cutoff
valid_from == cutoff
valid_until == cutoff
```

### 4.5 Propagation through P07 and G1

The v2 P07 input digest must remain the predecessor identity through:

```text
T01 input_digest
  → T02 fill/outcome provenance
  → T03 transition provenance
  → T04 ledger provenance
  → T05 reconciliation provenance
  → T06 PaperSimulationResult.input_digest
  → T07 history
  → P08 predecessors
  → G1
```

P07-T06 remains `p07-t06-v1` and non-economic. P07-T07 remains `p07-t07-v1`
and local. Neither boundary may re-evaluate or recreate Risk/Capital
authorization.

History must retain canonical ordering and must continue to reject:

- an exact repeated accepted input with
  `SIMULATION_INPUT_ALREADY_STORED`; and
- a different result for an existing input digest with
  `CONTRADICTORY_SIMULATION_INPUT`.

Neither rejection may mutate the accepted history.

G1 may recognize only the complete current linked chain. No generic `PASS`,
legacy v1 artifact, reference without the actual matching result, mismatched
reference, stale reference, tampered reference, contradictory input, or
structurally valid but unlinked P07 input may produce
`RECOGNIZED / FINAL / RECOGNIZED_COMPLETE`.

## 5. Required focused and composition verification

The future focused suite must cover at least:

1. valid v2 construction from an actual approved Risk/Capital result;
2. exact reference field preservation and recursive immutability;
3. exact P06 intent and context digest linkage;
4. exact authorization ID, result digest, lifecycle, scope, and version
   linkage;
5. generic `PASS` without a reference rejected at P07 admission;
6. missing observation and required-path `NOT_REQUIRED` rejected;
7. `FAIL` and `UNKNOWN` not upgradeable;
8. mismatched P06, scope, lifecycle, ID, version, effect, or digest rejected;
9. reference, observation, nested, result, and top-level digest tampering
   rejected;
10. unsupported versions rejected;
11. stale, expired, future-dated, and impossible timestamps rejected;
12. canonical key ordering, Unicode normalization, UTC timestamps,
    normalized decimals, explicit nulls, float rejection, and digest stability;
13. equivalent v2 replay producing identical validation and digests;
14. duplicate and contradictory references selecting the fixed reason;
15. P07-T06 preserving the v2 input digest and linked provenance;
16. P07-T07 preserving identity and rejecting duplicate and contradictory
    repeated input;
17. legacy v1 remaining readable only as legacy evidence and refused by G1
    with `NOT_RECOGNIZED / NOT_APPLICABLE / UNSUPPORTED_VERSION`;
18. v2 missing reference refused by G1 with
    `NOT_RECOGNIZED / NOT_APPLICABLE / MISSING_REQUIRED_INPUT`;
19. present but mismatched, invalid, or tampered v2 reference refused by G1
    with `NOT_RECOGNIZED / NOT_APPLICABLE / INVALID_IDENTITY_LINK`;
20. real opportunity/risk → P06 → Risk/Capital → P07 → P07 result/history →
    P08 → G1 composition recognized only when fully linked; and
21. no test introducing any prohibited provider, wallet, signer, live,
    economic, settlement, accounting, classification, G2, G3, G4, or P09
    behavior.

Verification must include Python 3.13 focused execution, focused plus
end-to-end composition tests, and compile checks for the four authorized source
files. The implementation audit must also inspect scope integrity,
canonicalization, digest behavior, cutoff behavior, predecessor propagation,
legacy refusal, and deterministic reason precedence. Passing tests alone do
not close the contract.

## 6. Explicit prohibitions

This authorization does not permit:

- any new file;
- any dependency installation or dependency change;
- any `.replit`, environment, workflow, or secret change;
- any `PROJECT_STATE.md` change as part of implementation;
- any change to the Risk/Capital evaluator or its focused tests;
- provider selection or provider connectivity;
- exchanges, venues, APIs, RPC, networks, chains, or DEX behavior;
- wallets, custody, accounts, keys, seed phrases, or signers;
- signing, broadcast, live orders, retries, execution, or settlement;
- position mutation outside the already existing paper contracts;
- accounting, valuation, realized P&L, ROI, cost basis, or classification;
- external registries, caches, queues, databases, migrations, or persistence;
- wall-clock or external-state lookup;
- automatic legacy migration, inference, reconstruction, or substitution;
- a new simulation engine;
- G2 realization authority;
- G3 accounting authority;
- G4 performance classification; or
- P09 live-execution behavior.

A valid v2 input is paper-simulation context only. It is not permission to
execute, submit, sign, broadcast, settle, account, classify, or trade.

## 7. Required governance sequence

The future work must follow this sequence:

1. Make only the permitted changes in the eight named existing files.
2. Run the required focused, composition, Python 3.13, compile, and
   `git diff --check` verification.
3. Confirm that no prohibited file, behavior, dependency, environment, or
   future phase changed.
4. Complete a fresh independent implementation audit before any closure claim.
5. Only after that audit passes may the separately governed project-state
   closure process be considered.

This authorization itself is not an implementation audit and does not close
P07 v2, P08, G1, G2, G3, G4, or P09.

## 8. Change-control confirmation

This authorization creates exactly one documentation file:

```text
docs/P08-P07-RISK-CAPITAL-ADMISSION-V2-IMPLEMENTATION-AUTHORIZATION.md
```

The authorization does not modify source code, tests, dependencies, `.replit`,
`PROJECT_STATE.md`, providers, wallets, signers, exchanges, chains, APIs, live
orders, execution, settlement, accounting, realized P&L, classification, G2,
G3, G4, or P09.

No commit or push is authorized or performed by this documentation-only
authorization.