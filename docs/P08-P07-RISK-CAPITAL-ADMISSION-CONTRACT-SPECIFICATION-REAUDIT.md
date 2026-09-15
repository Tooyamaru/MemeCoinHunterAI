# P08 — P07 Risk/Capital Admission Contract Specification Formal Re-Audit

**Audit date:** 2026-09-15  
**Project:** MemeCoinHunterAI  
**Audit type:** Documentation-only formal specification re-audit  
**Checkpoint requested:** `main` at `64dfa23`  
**Audited specification:** `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION.md`

## Overall verdict

**BLOCKED — SPECIFICATION NOT CLOSED / NOT AUDITED PASS**

The corrected specification closes the earlier provenance, temporal, legacy
handling, canonicalization, replay, duplicate, contradiction, and authority
boundary gaps in its primary contract text. It now documents a twelve-field
reference matching the current P07/G1 reference object, separates
result-only provenance from the bounded reference, defines the P07-T01 v2
version boundary, and gives explicit paper-only and future-scope limits.

The specification still cannot pass this re-audit because two contract
sources remain unresolved:

1. The proposal retains a different eighteen-field exact reference schema and
   different field names for the authority and evaluator versions. The
   corrected specification declares its twelve-field shape canonical, but it
   does not explicitly supersede or invalidate the proposal's competing
   schema. Therefore the repository does not yet contain one unambiguous
   exact reference schema across the required audit basis.
2. The corrected specification gives two different G1 outcomes for the same
   v2 missing-reference case. Section 3.3 first states that a missing required
   reference maps to `INVALID_IDENTITY_LINK`, then states that the canonical
   missing-reference mapping is `MISSING_REQUIRED_INPUT`. The later reason
   mapping and precedence text also use `MISSING_REQUIRED_INPUT`, but the
   earlier exact refusal remains contradictory. The required single
   deterministic G1 reason is therefore not established.

`PROJECT_STATE.md` was not modified because not every criterion passes.

## Audit basis and scope

The requested materials were inspected in the specified order:

1. `REPLIT_RULES.md`
2. `PROJECT_STATE.md`
3. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION-AUDIT.md`
4. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION.md`
5. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-PROPOSAL.md`
6. `docs/P08-PAPER-LIFECYCLE-END-TO-END-READINESS-REAUDIT.md`
7. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`
8. `docs/P08-G1-SIMULATION-ONLY-ECONOMIC-AUTHORITY-SPECIFICATION.md`
9. `docs/P07-T01-SPECIFICATION.md`
10. `docs/P07-T06-SPECIFICATION.md`
11. `docs/P07-T07-SPECIFICATION.md`
12. `core/execution/paper_simulation_input.py`
13. `core/execution/paper_simulation_result.py`
14. `core/execution/paper_simulation_result_history.py`
15. `core/learning/g1_simulation_only_economic_authority.py`
16. Directly relevant P07, Risk/Capital, and G1 tests

The repository-root files were treated as canonical. The nested
`MemeCoinHunterAI/` copies are documented legacy mirrors and were not used as
audit sources.

This was a documentation-only audit. No source code, tests, dependencies,
environment files, providers, wallets, signers, exchanges, chains, APIs,
live orders, execution, settlement, accounting, realized P&L,
classification, G2, G3, G4, P09, commit, or push was changed or performed.

## Criterion-by-criterion findings

### 1. One exact canonical twelve-field reference schema matches P07/G1 names and types

**Assessment: FAIL — unresolved cross-document schema conflict**

The corrected formal specification defines one twelve-field
`RiskCapitalAuthorizationReference`:

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

That shape matches the current P07 reference value object and uses the
Risk/Capital authority contract and evaluator version names used by the P07
handoff. The specification also correctly identifies policy snapshot identity,
policy snapshot digest, simulation reference time, and validity bounds as
required provenance on the complete Risk/Capital result rather than silently
inventing nullable substitutes in the bounded reference.

However, the required proposal still defines a competing exact reference with
eighteen semantic/derived fields. It includes
`policy_snapshot_id`, `policy_snapshot_digest`,
`simulation_reference_time`, `valid_from`, and `valid_until`, and calls the
version fields `authority_contract_version` and
`authority_evaluator_version`. The formal specification says the twelve-field
schema is canonical but does not explicitly mark the proposal's eighteen-field
schema as superseded, historical, or non-authoritative.

The formal specification must explicitly resolve the proposal conflict before
there is one exact schema for implementation and audit.

### 2. Every mandatory provenance field has an explicit canonical/null policy

**Assessment: PASS**

The corrected specification gives non-null policies for every field in the
twelve-field reference. It also explicitly documents the complete-result-only
provenance:

- `policy_snapshot_id`;
- `policy_snapshot_digest`;
- `simulation_reference_time`;
- `valid_from`; and
- `valid_until` for an approved result.

Those fields are required on the complete result, validated against the P07
cutoff and observation, and are not reconstructed from the reference. The
specification distinguishes required non-null values from allowed explicit
nulls and states that omission and null are not equivalent.

### 3. v2 mandatory-reference behavior and v1 legacy/G1 refusal are synchronized

**Assessment: FAIL — synchronization is contradicted by the reason mapping**

The corrected specification provides a clear future version matrix:

- `p07-t01-v2` is the new required-reference admission;
- `p07-t01-v1` is legacy/read-only evidence;
- P07-T02 through P07-T07 preserve the v2 input identity through their
  existing versioned boundaries; and
- G1 recognizes only the fully linked v2 path.

It also correctly states that the current runtime remains v1 until separate
implementation authorization. The inspected source confirms that current
implementation status: the reference is an immutable twelve-field object, but
the current `AuthorizationObservation` still permits an absent reference.
That is consistent with the specification's separate future implementation
gate and is not treated as an unauthorized source change.

The specification is not synchronized internally, however. Its Section 3.3
first assigns a missing v2 reference to `INVALID_IDENTITY_LINK`, then assigns
the same missing-reference case to `MISSING_REQUIRED_INPUT`. P07 direct
admission is stated to use the latter, while the earlier G1 refusal block uses
the former. History and T06 propagation are otherwise stated consistently.
The conflicting G1 mapping prevents closure.

### 4. Cutoff validation is fully deterministic

**Assessment: PASS**

The sole cutoff source is explicitly
`PaperSimulationInput.simulation_reference_time`. The specification requires
timezone-aware timestamps normalized to UTC and comparison as instants. It
defines:

- observation and `valid_from` strictly after the cutoff as
  `AUTHORIZATION_FUTURE_DATED`;
- `valid_until` strictly before the cutoff as `AUTHORIZATION_STALE`;
- equality at observation, lower-bound, and upper-bound cutoffs as valid; and
- missing, malformed, naive, offset-invalid, or non-canonical temporal
  material as `REFERENCE_TIME_INVALID` under the declared precedence.

No wall clock, external lookup, or freshness inference is permitted.

### 5. Missing references map to exactly one G1 fail-closed reason

**Assessment: FAIL**

The specification does not meet this criterion because it contains both of
these statements for `v2 PASS` without an authorization reference:

```text
reason_code = INVALID_IDENTITY_LINK
```

and:

```text
reason_code = MISSING_REQUIRED_INPUT
```

The later text says `MISSING_REQUIRED_INPUT` wins before
`INVALID_IDENTITY_LINK`, which is a workable intended resolution, but the
earlier exact refusal is still part of the specification. A validator,
implementation author, or G1 audit cannot treat both as the one exact outcome.

The correction must retain exactly one rule, preferably the explicitly stated
precedence rule that an absent required reference is
`MISSING_REQUIRED_INPUT`, while reserving `INVALID_IDENTITY_LINK` for a
present but mismatched reference or authorization handoff.

### 6. Generic PASS alone is insufficient for v2

**Assessment: PASS in the corrected future contract**

The v2 admission requires all of:

- `p07-t01-v2`;
- a `PASS` authorization observation;
- a present valid immutable reference;
- an actual `APPROVED` Risk/Capital result;
- exact P06, Risk/Capital, lifecycle, scope, version, effect, and digest
  linkage; and
- a valid explicit simulation cutoff.

The specification explicitly rejects generic `PASS` without the reference and
prohibits upgrading `FAIL`, `UNKNOWN`, or `NOT_REQUIRED`.

### 7. No automatic migration, inference, reconstruction, or substitution exists

**Assessment: PASS**

Legacy v1 artifacts are restricted to version-specific read-only evidence.
The specification prohibits adding a reference after the fact, copying
fields from observations or digests, inferring approval, reconstructing from
P06 or lifecycle identity, substituting authorization or policy, merging v1
with v2, and silently migrating legacy material. Any future migration
requires a separate contract, source-evidence rules, versioned
canonicalization, tests, authorization, and audit.

### 8. Canonical representation, digest, replay, duplicate, contradiction, and immutability rules are adequate

**Assessment: PASS**

The corrected specification defines sorted keys, fixed ordered arrays,
forbidden sets, explicit enum strings, canonical UTC timestamps,
normalized finite decimal text, rejection of binary floating-point values,
explicit null representation, rejected unknown fields, string mapping keys,
and compact sorted-key JSON for SHA-256.

Reference, observation, and input digest coverage is explicit and nested
digests must be verified before parent digests. Recursive immutability,
equivalent replay, duplicate evidence, contradictory evidence, canonical
ordering, and non-mutation of accepted history are also defined. No caller
order, retrieval order, freshness preference, or status label resolves
contradictions.

### 9. Future implementation scope is explicitly separate and unauthorized

**Assessment: PASS**

The specification separates the formal audit, limited implementation
authorization, and implementation audit gates. It states that the current
runtime remains v1 and that v2 implementation cannot be produced until a
separate authorization passes. The future source and focused-test scope is
bounded and excludes Risk/Capital implementation changes, providers,
wallets, live behavior, economic authority, G2, G3, G4, and P09.

### 10. P07 remains paper-only and provider-neutral

**Assessment: PASS**

The reference and all P07 propagation rules are limited to one identity-linked
paper-simulation lifecycle. The specification prohibits provider, exchange,
RPC, network, wallet, signer, order, execution, settlement, accounting,
valuation, realized P&L, ROI, classification, and external-authority
behavior. P07-T06 and P07-T07 remain immutable, deterministic, non-economic,
and local.

### 11. G2, G3, G4, and P09 remain unauthorized

**Assessment: PASS**

The corrected specification preserves the separate boundaries:

- G2 remains future realization and settlement eligibility;
- G3 remains future accounting and economic-result calculation;
- G4 remains future performance classification; and
- P09 remains separately governed live execution.

No paper approval, P07 result, history record, or G1 recognition is treated
as settlement, realized value, accounting truth, profitability,
classification, or live authority.

## Required corrections before another audit

The smallest documentation-only correction set is:

1. Explicitly reconcile the proposal's eighteen-field draft with the formal
   specification's twelve-field canonical reference. Either update the
   proposal to the twelve-field schema or explicitly mark its old schema
   superseded/non-authoritative in the governing specification.
2. Remove the contradictory Section 3.3 G1 missing-reference mapping and
   retain exactly one outcome. The specification must state that a missing
   required v2 reference maps to
   `NOT_RECOGNIZED / NOT_APPLICABLE / MISSING_REQUIRED_INPUT`, while
   `INVALID_IDENTITY_LINK` applies only to present but mismatched linked
   material, if that is the intended precedence.
3. Re-run the formal re-audit after those documentation corrections. Do not
   authorize or implement P07 v2 as part of that correction.

## Authority and change-control confirmation

The intended ownership remains:

- **P06:** analytical `DecisionIntent`, not authorization or an order;
- **Risk/Capital Safe V1:** deterministic admission of one identity-linked
  P07 paper lifecycle;
- **P07:** paper input, observations, fills, state, ledger, reconciliation,
  canonical non-economic result, and local history;
- **G1:** simulation-only recognition and simulation finality;
- **G2/G3/G4/P09:** separately governed and not authorized.

This re-audit created exactly:

```text
docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION-REAUDIT.md
```

`PROJECT_STATE.md` was intentionally not changed because the audit did not
pass. No commit or push was performed.