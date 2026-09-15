# P08 — P07 Risk/Capital Admission Contract Specification Second Formal Re-Audit

**Audit date:** 2026-09-15
**Project:** MemeCoinHunterAI
**Audit type:** Documentation-only formal specification second re-audit
**Checkpoint requested:** `main` at `63b2392`
**Audited specification:** `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION.md`

## Overall verdict

**PASS — SPECIFICATION COMPLETE / CLOSED / AUDITED PASS**

The two blockers recorded by the prior formal re-audit are resolved:

1. The former proposal is explicitly marked
   `SUPERSEDED / NON-NORMATIVE HISTORICAL PROPOSAL`, its former eighteen-field
   schema has no contract authority, and the corrected specification is
   explicitly the sole normative Safe V1 source with the canonical
   twelve-field schema.
2. The corrected specification now assigns exactly one G1 reason to each
   reference state:
   - an absent required v2 reference is
     `NOT_RECOGNIZED / NOT_APPLICABLE / MISSING_REQUIRED_INPUT`;
   - a present but mismatched, invalid, or tampered reference is
     `NOT_RECOGNIZED / NOT_APPLICABLE / INVALID_IDENTITY_LINK`.

All requested criteria pass. `PROJECT_STATE.md` was updated with the exact
required closure sentence. No v2 implementation authorization is implied.

## Audit basis and scope

The requested materials were inspected in the specified order:

1. `REPLIT_RULES.md`
2. `PROJECT_STATE.md`
3. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION-REAUDIT.md`
4. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION-AUDIT.md`
5. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-PROPOSAL.md`
6. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION.md`
7. `docs/P08-PAPER-LIFECYCLE-END-TO-END-READINESS-REAUDIT.md`
8. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`
9. `docs/P08-G1-SIMULATION-ONLY-ECONOMIC-AUTHORITY-SPECIFICATION.md`
10. `docs/P07-T01-SPECIFICATION.md`
11. `docs/P07-T06-SPECIFICATION.md`
12. `docs/P07-T07-SPECIFICATION.md`
13. `core/execution/paper_simulation_input.py`
14. `core/execution/paper_simulation_result.py`
15. `core/execution/paper_simulation_result_history.py`
16. `core/learning/g1_simulation_only_economic_authority.py`
17. Directly relevant P07, G1, and Risk/Capital tests

The repository-root files were treated as canonical. The nested
`MemeCoinHunterAI/` copies are documented legacy mirrors and were not used as
audit sources.

This was a documentation-only audit. No source code, tests, dependencies,
environment files, providers, wallets, signers, exchanges, chains, APIs,
live orders, execution, settlement, accounting, realized P&L,
classification, G2, G3, G4, P09, commit, or push was changed or performed.
The current runtime remains the pre-v2 implementation described by the
specification; v2 implementation remains separately unauthorized.

## Criterion-by-criterion findings

### 1. The proposal is explicitly superseded and has no contract authority

**Assessment: PASS**

The proposal header states:

```text
SUPERSEDED / NON-NORMATIVE HISTORICAL PROPOSAL
```

Its top-level notice preserves the historical eighteen-field schema while
explicitly stating that it has no current contract authority and must not be
used for implementation, validation, or compatibility decisions. The same
notice identifies the corrected specification as the sole normative Safe V1
source.

### 2. The corrected specification is the sole normative source with one canonical twelve-field schema

**Assessment: PASS**

The corrected specification explicitly declares the reference to contain
exactly these twelve fields:

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

The names and types match the current P07
`RiskCapitalAuthorizationReference` value object. The former proposal's
different field set is now historical and non-normative, so it cannot create a
second active schema.

### 3. Required provenance fields and canonical/null policies are complete

**Assessment: PASS**

Every twelve-field reference member has an explicit requiredness and
canonical/null policy. The complete Risk/Capital result separately owns the
required linked provenance not duplicated in the bounded reference:

- `policy_snapshot_id`;
- `policy_snapshot_digest`;
- `simulation_reference_time`;
- `valid_from`; and
- `valid_until` for an approved result.

The specification requires those result-only values to be present, canonical,
verified, and compared to the P07 observation and cutoff. It prohibits
reconstructing them from the reference and distinguishes explicit `null` from
omission.

### 4. v2 mandatory-reference behavior and v1 legacy/G1 refusal are synchronized

**Assessment: PASS**

The supported-version matrix consistently defines:

- `p07-t01-v2` as the new reference-required admission;
- `p07-t01-v1` as legacy/read-only evidence;
- P07-T02 through P07-T07 as preserving the v2 T01 identity through their
  existing versioned boundaries; and
- G1 as recognizing only the complete linked v2 path.

The legacy section gives the exact v1 refusal:

```text
NOT_RECOGNIZED / NOT_APPLICABLE / UNSUPPORTED_VERSION
```

The specification also explicitly says the current source remains v1 until a
separate implementation authorization passes. The source inspection confirms
that no v2 behavior was introduced: the current P07 contract constant remains
v1 and the reference is still optional in the current runtime. This is
consistent with the documented future implementation gate, not a contract
ambiguity.

P07-T06 preserves the T01 input digest, and P07-T07 stores validated T06
results and transitively preserves that identity. G1's documented predecessor
chain requires the supported P07 artifacts and exact linkage.

### 5. An absent or missing v2 reference maps only to MISSING_REQUIRED_INPUT

**Assessment: PASS**

The corrected specification contains one exact missing-reference outcome:

```text
recognition_state = NOT_RECOGNIZED
finality_state    = NOT_APPLICABLE
reason_code       = MISSING_REQUIRED_INPUT
```

The same mapping appears in the G1 mapping section, the fail-closed matrix,
the focused future-test requirements, and the direct P07 admission rule.
`MISSING_REQUIRED_INPUT` precedes identity-link validation in the declared
reason precedence.

### 6. A present but mismatched, invalid, or tampered reference maps only to INVALID_IDENTITY_LINK

**Assessment: PASS**

The specification gives one exact outcome for a present reference that is
mismatched, invalid, or tampered:

```text
recognition_state = NOT_RECOGNIZED
finality_state    = NOT_APPLICABLE
reason_code       = INVALID_IDENTITY_LINK
```

The G1 mapping and fail-closed matrix repeat that distinction. Reference digest
tampering is mapped to `INVALID_IDENTITY_LINK`; supplied Risk/Capital result
digest tampering remains separately mapped to `DIGEST_FAILURE`, because it is
not a reference-state classification. No missing-reference path is mapped to
`INVALID_IDENTITY_LINK`.

### 7. Cutoff, future, stale, and equality boundaries are deterministic and UTC-defined

**Assessment: PASS**

The sole cutoff is the supplied
`PaperSimulationInput.simulation_reference_time`. All relevant timestamps are
timezone-aware, normalized to UTC, and compared as instants.

- `observed_at` or `valid_from` strictly after the cutoff is
  `AUTHORIZATION_FUTURE_DATED`.
- `valid_until` strictly before the cutoff is `AUTHORIZATION_STALE`.
- Equality at the observation, lower-validity, and upper-validity boundaries is
  valid.
- Missing, malformed, naive, offset-invalid, or non-canonical temporal
  material is rejected under the declared precedence.

No wall clock, external lookup, or freshness inference is allowed.

### 8. Generic PASS alone is insufficient for v2

**Assessment: PASS**

The v2 admission requires `p07-t01-v2`, a `PASS` observation, one present and
valid immutable reference, an actual `APPROVED` Risk/Capital result, exact P06
and Risk/Capital linkage, valid scope and lifecycle identity, valid digests,
and valid cutoff coverage. A generic `PASS` without the reference is rejected
before a simulation lifecycle can begin. `FAIL`, `UNKNOWN`, and required-path
`NOT_REQUIRED` cannot be upgraded.

### 9. No automatic migration, inference, reconstruction, or substitution exists

**Assessment: PASS**

The specification prohibits adding a reference to v1 after the fact, copying
fields from observations or digests, inferring approval, reconstructing from
P06 or lifecycle identity, substituting authorization or policy, merging v1
with v2, or silently migrating legacy evidence. Any future migration requires
its own versioned contract, source-evidence rules, focused tests,
implementation authorization, and audit.

### 10. Canonical, digest, replay, duplicate, contradiction, and immutability rules remain adequate

**Assessment: PASS**

The normative specification defines sorted keys, ordered arrays, forbidden
sets, explicit enum values, canonical UTC timestamps, normalized finite
decimal text, rejected binary floating-point values, explicit nulls, rejected
unknown fields, and compact sorted-key JSON for SHA-256.

Reference, observation, and input digest coverage is explicit. Nested digests
are verified before parent digests. Recursive immutability, equivalent replay,
duplicate handling, contradiction handling, canonical history ordering, and
non-mutation of accepted history remain defined.

### 11. Paper-only, provider-neutral, and future-authorization boundaries remain intact

**Assessment: PASS**

P07 remains limited to one identity-linked paper-simulation lifecycle. The
normative specification prohibits providers, exchanges, RPC, networks,
wallets, signers, orders, execution, settlement, accounting, valuation,
realized P&L, ROI, classification, and external authority.

The implementation scope is explicitly future and limited to the named P07/G1
source and focused-test files. The Risk/Capital implementation remains
separately governed. No current implementation authorization is implied.

## Final governance verdict

All requested criteria pass. The P07 Risk/Capital admission contract
specification is complete, closed, and audited PASS at the specification
level.

This PASS authorizes no source or test changes. A separate limited P07 v2
implementation authorization is required before code may be created.

## Remaining blockers

None for the documentation specification audit.

The following remain explicitly outside this closure:

- P07 v2 implementation authorization;
- P07 v2 implementation and focused tests;
- provider, exchange, chain, RPC, wallet, signer, execution, settlement,
  accounting, realized P&L, or classification behavior; and
- G2, G3, G4, and P09.

## Authority boundaries

- **P05:** normalized opportunity context and hard-risk viability.
- **P06:** analytical `DecisionIntent`, not authorization or an order.
- **Risk/Capital Safe V1:** deterministic approval or rejection of one
  identity-linked P07 paper lifecycle.
- **P07-T01:** validates and preserves the exact Risk/Capital handoff and paper
  simulation input; it does not create or evaluate Risk/Capital authorization.
- **P07-T02 through T07:** paper observations, fills, state transitions,
  ledger, reconciliation, canonical non-economic result, and local history.
- **G1:** simulation-only recognition and simulation finality.
- **G2/G3/G4/P09:** separately governed and not authorized.

No paper approval, P07 result, history record, or G1 recognition means
settlement, realized value, accounting truth, profitability, classification,
provider truth, wallet permission, or live authority.

## Change-control confirmation

This second re-audit created exactly:

```text
docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION-SECOND-REAUDIT.md
```

`PROJECT_STATE.md` was updated only with the exact required closure sentence.
No commit or push was performed.