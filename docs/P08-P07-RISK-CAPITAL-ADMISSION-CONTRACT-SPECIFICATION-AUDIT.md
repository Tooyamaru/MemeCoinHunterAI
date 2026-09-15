# P08 — P07 Risk/Capital Admission Contract Specification Formal Audit

**Audit date:** 2026-09-15  
**Project:** MemeCoinHunterAI  
**Audit type:** Documentation-only formal specification audit  
**Checkpoint:** `main` at `2a0d8ac`  
**Audited specification:** `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION.md`

## Overall verdict

**BLOCKED — SPECIFICATION NOT CLOSED / NOT AUDITED PASS**

The specification correctly establishes the intended direction: a new
Risk/Capital-gated P07 admission must carry an immutable reference, generic
`PASS` alone must not be sufficient, legacy v1 evidence must not be promoted,
and P07/G1 must remain deterministic, paper-only, and provider-neutral.

The specification is not internally audit-ready because its exact
`RiskCapitalAuthorizationReference` schema conflicts with the preceding
proposal, its P07-v2/G1 supported-version boundary is not synchronized, and
some temporal and cross-boundary reason mappings are not deterministic enough
to serve as a closed contract.

`PROJECT_STATE.md` was not modified. The specification must not be marked
`COMPLETE / CLOSED / AUDITED PASS` until the blockers below are corrected and
audited again.

## Audit basis and scope

The required materials were inspected in the requested order:

1. `REPLIT_RULES.md`
2. `PROJECT_STATE.md`
3. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-PROPOSAL.md`
4. `docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION.md`
5. `docs/P08-PAPER-LIFECYCLE-END-TO-END-READINESS-REAUDIT.md`
6. `docs/P08-RISK-CAPITAL-AUTHORITY-SPECIFICATION.md`
7. `docs/P08-G1-SIMULATION-ONLY-ECONOMIC-AUTHORITY-SPECIFICATION.md`
8. `docs/P07-T01-SPECIFICATION.md`
9. `docs/P07-T06-SPECIFICATION.md`
10. `docs/P07-T07-SPECIFICATION.md`
11. `core/execution/paper_simulation_input.py`
12. `core/execution/paper_simulation_result.py`
13. `core/execution/paper_simulation_result_history.py`
14. `core/learning/g1_simulation_only_economic_authority.py`
15. Directly relevant P07, Risk/Capital, and G1 focused tests

The imported `MemeCoinHunterAI/PROJECT_STATE.md` is explicitly documented as
a legacy mirror. The repository-root `PROJECT_STATE.md` and repository-root
documentation are therefore the canonical audit sources.

No source, test, dependency, environment, provider, wallet, signer, workflow,
execution, settlement, accounting, classification, G2, G3, G4, or P09 file
was changed by this audit.

## Criterion-by-criterion findings

### 1. v2 requires an immutable canonical `RiskCapitalAuthorizationReference`

**Assessment: FAIL**

The requiredness rule itself is explicit in the formal specification:
Section 4.2 says a v2 `PASS` admission requires
`authorization_reference != null`, and Section 7.1 repeats that requirement.
The reference is also described as immutable and digest-protected in Sections
5 and 8.

However, the exact reference contract is not consistent across the governing
documents:

- The proposal’s Section 4.2 defines an exact reference containing a reference
  schema version, policy snapshot identity and digest, simulation reference
  time, validity bounds, authority versions, and the reference digest.
- The formal specification’s Section 5.1 defines a different exact reference
  with only twelve semantic fields. It omits the reference schema version,
  policy snapshot identity and digest, simulation reference time, and validity
  bounds.
- In the proposal, `contract_version` identifies
  `p07-risk-capital-authorization-reference-v1`; in the formal specification,
  `contract_version` identifies `p08-risk-capital-authority-v1`.

The current source confirms that the existing v1 reference follows the
smaller twelve-field shape and that the reference remains optional in the
existing v1 `AuthorizationObservation`. That is expected before separately
authorized v2 implementation, but it makes the unresolved specification
schema conflict material rather than a runtime audit finding.

**Smallest correction:** choose one exact reference schema and version meaning,
then update the formal specification, proposal, provenance table, digest
coverage, and future-test scope to use that schema consistently.

### 2. The reference proves exact Risk/Capital and same P06 identity/digest linkage

**Assessment: BLOCKED**

The core identity graph is correctly specified in Section 6:

```text
P06 intent digest
  == Risk/Capital result intent digest
  == reference intent digest
  == P07 intent digest
```

The same section links the context digest, authorization ID, authorization
result digest, lifecycle, and scope. Section 5.1 also requires value-preserving
construction from the actual Risk/Capital result, while the G1 boundary
requires the complete actual result independently.

The criterion cannot receive a final PASS because the exact reference schema
omits policy identity/digest and temporal material that the proposal and
Section 9.1 call part of the complete linked provenance. Until the schema is
reconciled, it is not possible to determine whether the reference itself
preserves the exact Safe V1 authorization packet or whether those values are
only available through a separately supplied result.

**Smallest correction:** explicitly define which Risk/Capital fields the
reference must preserve, which fields are verified only against the complete
result, and how both sets participate in P07 and G1 validation.

### 3. Generic `PASS` alone is rejected

**Assessment: PASS**

The formal specification is explicit and consistent on this point:

- Section 4.2 requires a reference for a v2 `PASS` admission.
- Section 5.1 says a raw status, observation ID, or digest pair does not prove
  approval.
- Section 7.1 requires an actual `APPROVED` result and a valid reference.
- Section 12 maps generic `PASS` without a reference to a fail-closed outcome.
- Section 13 prohibits using a generic observation as a substitute.

The current v1 implementation still permits a structurally valid generic
`PASS`, as documented by the readiness re-audit. That is the known gap being
specified for a future, separately authorized v2 implementation; it does not
turn this criterion into a specification failure.

### 4. Missing, stale, tampered, mismatched, unsupported, duplicate, and contradictory evidence fails closed with deterministic precedence

**Assessment: BLOCKED**

The specification covers all requested failure classes across Sections 7,
10, 11, and 12. It also defines a bounded P07 vocabulary and a fixed P07
precedence order, and it retains the existing G1 vocabulary.

Two determinism gaps prevent a final PASS:

1. The temporal rules require the validity window to cover the simulation
   cutoff, but they do not explicitly require
   `authorization_observation.observed_at <= simulation_reference_time`.
   Section 12 nevertheless refers to a future-dated approval or observation.
   The contract must state the exact temporal predicate and reason for a
   future-dated observation.
2. The fail-closed matrix says that generic `PASS` without a reference maps at
   G1 to `MISSING_REQUIRED_INPUT` **or** `INVALID_IDENTITY_LINK` “according to
   the first failed validation boundary.” That leaves the emitted G1 reason
   dependent on an implementation boundary rather than a single canonical
   validation precedence. The G1 specification requires exactly one reason.

**Smallest correction:** add the missing observation-time relation and select
one exact G1 reason mapping for each missing-reference state, independent of
which internal validator notices it first.

### 5. v1 legacy artifacts are readable only as legacy evidence and are refused by G1

**Assessment: BLOCKED**

The intended policy is clear:

- Section 3.3 permits version-specific legacy reading and historical
  inspection only.
- Section 3.3 prohibits v1 promotion, repair, inference, reconstruction,
  substitution, and current G1 recognition.
- Sections 11.3 and 12 specify `UNSUPPORTED_VERSION` and
  `NOT_RECOGNIZED / NOT_APPLICABLE` behavior.

The supported-version boundary is not synchronized, however. The G1
specification’s explicit version table lists P07-T07 and P08 versions, but
does not explicitly list `p07-t01-v2`; it only says that P07-T01 through
P07-T06 versions must be validated against their own contracts. The closed
P07-T01 specification and the current implementation still identify
`p07-t01-v1` as the supported contract. The formal P07 admission
specification therefore describes v1 as legacy while not providing one
authoritative, explicit G1 v2 support table.

**Smallest correction:** add an explicit synchronized version matrix stating
that current recognition accepts `p07-t01-v2`, rejects `p07-t01-v1` as legacy,
and applies the exact same rule in P07, G1, and the focused tests.

### 6. No automatic migration, inference, reconstruction, or substitution exists

**Assessment: PASS**

Sections 3.3, 4.1, 5.1, 6.3, 9, 10, and 13 repeatedly prohibit automatic
migration, partial-field repair, inference, reconstruction, substitution, and
promotion of legacy evidence. The specification also requires a separate
versioned migration contract and independent audit if migration is ever
considered.

### 7. P07 result/history propagation is complete and deterministic

**Assessment: FAIL**

The intended identity propagation is well defined in Section 9.2:

```text
T01 input digest
  → T02
  → T03
  → T04
  → T05
  → T06 result
  → T07 history
```

Section 9.3 also defines canonical history ordering, duplicate rejection, and
contradictory repeated-input rejection. The current result and history
boundaries preserve the T01 input digest and deterministic T06/T07 identities.

The specification’s claim of **complete** linked provenance is not achievable
from its own exact v2 field tables. Section 9.1 requires P07-T01 to retain
policy snapshot ID/digest and other Risk/Capital provenance, but Section 5.1
does not include those values in the reference, and the authorization
observation fields do not contain them. The propagation contract therefore
has a missing source field and cannot be audited as complete.

**Smallest correction:** add the required provenance fields to the chosen
reference schema or explicitly define a separate immutable, versioned
provenance envelope and require it in the v2 input, then specify its
propagation into T06 and T07.

### 8. Canonical representation, null policy, ordering, SHA-256 digest, provenance, cutoff, replay, duplicate, and contradiction rules are adequate

**Assessment: FAIL**

The formal specification provides strong coverage for:

- sorted mapping keys and ordered sequences;
- explicit null versus absent semantics;
- UTC timestamp normalization;
- normalized decimal text and float rejection;
- Unicode normalization;
- recursive immutability;
- SHA-256 coverage for reference, observation, and input;
- caller-supplied cutoff behavior;
- deterministic replay;
- canonical history ordering; and
- duplicate and contradiction refusal.

The rules are not adequate as one closed contract because:

- the proposal and formal specification disagree on the exact reference
  fields and `contract_version` meaning;
- the provenance list requires fields omitted by the exact reference table;
- the future-dated observation predicate is not explicit; and
- the cross-boundary G1 mapping permits two possible reasons for one generic
  missing-reference condition.

These are contract-definition defects, not requests for broader
implementation. The current P07 source also remains v1 and does not implement
the formal specification’s future Unicode/v2 behavior; implementation is
correctly unauthorized until this specification is resolved.

**Smallest correction:** reconcile the exact schema first, then make every
digest, provenance, temporal, duplicate, contradiction, and G1 mapping rule
refer to that one schema and one fixed validation order.

### 9. Future implementation/test scope is minimal and explicitly unauthorized

**Assessment: PASS**

Section 14 names exactly four source files and four focused test files. It
explicitly excludes the Risk/Capital implementation and its tests from this
correction. Sections 15 and 16 keep specification audit, limited
implementation authorization, and implementation audit as separate gates.
No implementation authorization is implied by the specification.

### 10. P07 remains paper-only and provider-neutral

**Assessment: PASS**

The formal specification consistently limits the contract to identity-linked
paper-simulation admission. Sections 5, 9, 13, and 15 prohibit providers,
exchanges, RPC, networks, wallets, signers, orders, execution, settlement,
accounting, valuation, realized P&L, ROI, classification, and external
authority. The referenced P07-T06 and P07-T07 contracts preserve the same
non-economic boundary.

### 11. G2, G3, G4, and P09 remain unauthorized

**Assessment: PASS**

Sections 13, 15, and 16 explicitly keep G2 realization, G3 accounting,
G4 classification, and P09 live execution separately governed and
unauthorized. The specification does not infer any of those authorities from
paper approval, P07 results, history, or G1 recognition.

## Remaining blockers

The smallest correction set before a re-audit is:

1. **Canonical reference schema:** reconcile the proposal and formal
   specification into one exact `RiskCapitalAuthorizationReference` field set,
   including the meaning and version of `contract_version`.
2. **Provenance completeness:** make the Section 9.1 required policy and
   temporal provenance available from the v2 reference/input contract and
   define its T06/T07 propagation.
3. **Version synchronization:** publish one explicit P07/G1 supported-version
   matrix for `p07-t01-v2` and legacy `p07-t01-v1` refusal.
4. **Temporal determinism:** explicitly validate observation time against the
   supplied simulation cutoff and define the exact future-dated reason.
5. **Cross-boundary reason determinism:** replace the G1
   “missing-required-input or invalid-identity-link” alternative with one
   fixed mapping and precedence.

No source or test change is required to resolve this documentation audit.
After those specification corrections, a new formal audit is required before
the separate limited implementation authorization.

## Authority boundaries confirmed

The audit confirms that the intended ownership remains:

- **P05:** normalized opportunity context and hard-risk viability.
- **P06:** analytical `DecisionIntent`; not authorization and not an order.
- **Risk/Capital Safe V1:** deterministic approval or rejection of one exact,
  identity-linked P07 paper lifecycle entry.
- **P07-T01:** validates and preserves the approved handoff; it does not create
  or evaluate Risk/Capital authorization.
- **P07-T02 through T07:** paper observations, fills, state transitions,
  ledger, reconciliation, canonical non-economic result, and local history.
- **G1:** simulation-only recognition and simulation finality.
- **G2:** future realization eligibility; not authorized.
- **G3:** future accounting and economic-result calculation; not authorized.
- **G4:** future performance classification; not authorized.
- **P09:** separately governed live-execution chain; not authorized.

No paper admission, paper result, history record, or G1 recognition means
settlement, realized value, accounting truth, realized P&L, profitability,
classification, live execution, provider truth, wallet permission, or P09
authority.

## Change-control confirmation

This audit created exactly:

```text
docs/P08-P07-RISK-CAPITAL-ADMISSION-CONTRACT-SPECIFICATION-AUDIT.md
```

`PROJECT_STATE.md` was intentionally not changed because not every criterion
passes. No commit or push was performed.