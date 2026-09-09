# P08 — Authority B Formal Specification Closure Audit

**Status:** SPECIFICATION COMPLETE / CLOSED / AUDITED PASS — IMPLEMENTATION NOT AUTHORIZED
**Phase:** P08 — Outcome Learning
**Authority:** Authority B — Correction / Supersession Lineage Facts
**Audit date:** 2026-09-09

## 1. Audit scope

This is a governance and specification-closure audit only. It does not create
source code, runtime behavior, persistence, tests, external access, wallet or
provider behavior, a new P08 task, or any authorization for P09.

The audit verifies the current Authority B specification against the existing
closed P08-T07 contract. It does not redesign Authority A, Authority B, or
P08-T07.

The audit specifically covers:

1. canonical serialization and digest determinism;
2. explicit duplicate-comparison context;
3. exact Authority B to T07 adapter mapping;
4. failure vocabulary and precedence;
5. lineage-only authority boundaries; and
6. preservation of the implementation and P09 authorization boundaries.

## 2. Documents reviewed

The following repository documents were reviewed:

- `REPLIT_RULES.md`;
- `PROJECT_STATE.md`;
- `docs/P08-AUTHORITY-A-SPECIFICATION-AUDIT.md`;
- `docs/P08-AUTHORITY-B-SPECIFICATION-AUDIT.md`;
- `docs/P08-T07-SPECIFICATION.md`;
- `docs/P08-T07-CANONICAL-RESULT-AUTHORITY-EXTENSION-SPECIFICATION.md`;
- `docs/P08-T04-SPECIFICATION.md`;
- `docs/P08-T05-SPECIFICATION.md`;
- `docs/P08-T06-SPECIFICATION.md`;
- `docs/ARCHITECTURE.md`;
- `docs/RISK_ENGINE.md`;
- `docs/EXECUTION_ENGINE.md`;
- `docs/LEARNING_ENGINE.md`; and
- `docs/SECURITY.md`.

Relevant repository history was also checked. Authority A is recorded as
`SPECIFICATION COMPLETE / CLOSED / AUDITED PASS — IMPLEMENTATION NOT
AUTHORIZED`, and P08-T07 is recorded as complete, closed, and audited PASS.

## 3. Audit status vocabulary

| Result | Meaning |
|---|---|
| `PASS` | The requirement is explicitly and deterministically specified. |
| `FAIL` | The specification contradicts an approved boundary or contains an invalid rule. |
| `BLOCKED` | A required semantic or compatibility decision remains unresolved. |
| `NOT AUTHORIZED` | The audit result does not authorize implementation or a later phase. |

## 4. Formal verdict

The Authority B specification passes the required closure criteria.

```text
AUTHORITY B SPECIFICATION = COMPLETE / CLOSED / AUDITED PASS
AUTHORITY B IMPLEMENTATION = NOT AUTHORIZED
P09 = NOT AUTHORIZED
```

The three blockers previously recorded in the Authority B audit are verified
as resolved:

1. canonical JSON escaping;
2. deterministic duplicate-comparison context; and
3. exact field-level Authority B to T07 mapping.

No remaining semantic or T07 compatibility blocker was found for
specification closure.

## 5. Criterion 1 — Canonical serialization

**Result: PASS**

The Authority B specification Section 5.3 defines one shared serialization
profile for `LineageFact`, `LineageEdge`, identity projections, and the
lineage-fact-set snapshot.

### 5.1 Verified serialization rules

| Requirement | Evidence | Finding |
|---|---|---|
| UTF-8 JSON | Section 5.3 | PASS — JSON is encoded as UTF-8 without a byte-order mark |
| No insignificant whitespace | Section 5.3 | PASS — only `,` and `:` separators are permitted |
| NFC string behavior | Section 5.3 | PASS — textual semantic values are normalized to NFC before escaping; unpaired surrogates are invalid |
| No alternate normalization | Section 5.3 | PASS — NFKC, NFD, case folding, trimming, locale transformation, and other normalization are prohibited |
| Quote escaping | Section 5.3 | PASS — `U+0022` is only `\"` |
| Backslash escaping | Section 5.3 | PASS — `U+005C` is only `\\` |
| Solidus escaping | Section 5.3 | PASS — `/` is never escaped |
| Control escaping | Section 5.3 | PASS — named short escapes are fixed and all other controls use lowercase `\u00xx` |
| Non-ASCII output | Section 5.3 | PASS — Unicode scalar values, including U+2028/U+2029, are emitted directly as UTF-8 |
| Key ordering | Section 5.3 | PASS — object keys are sorted by Unicode code-point sequence |
| Array ordering | Section 5.3 | PASS — arrays are never implicitly sorted; their order is contract-defined |
| Nullability | Sections 5.3–5.4 | PASS — Authority B has no nullable or optional semantic fields; absent and explicit `null` are invalid |
| Numeric values | Section 5.3 | PASS — Authority B defines no numeric semantic fields; numeric JSON tokens are invalid |
| Digest input | Section 5.3 | PASS — exact canonical UTF-8 bytes are hashed |
| Digest self-reference | Section 5.3 | PASS — the digest is omitted from the representation it protects |

The specification also fixes non-empty identity/version strings, lowercase
hexadecimal digests, canonical enum values, and fixed provenance sequence
ordering.

### 5.2 Serialization independence

The canonical representation, identity projection, and digest do not depend
on:

- timestamps;
- wall-clock or process time;
- runtime object ordering;
- database insertion or retrieval order;
- filesystem order;
- provider or network state;
- randomness;
- process identity;
- memory address; or
- hidden configuration.

Two conforming implementations given the same semantic fact must produce
byte-identical canonical bytes and the same digest.

## 6. Criterion 2 — Deterministic duplicate comparison

**Result: PASS**

The duplicate comparison context is an explicit, immutable
`Authoritative Lineage Fact Set Snapshot`. It is not discovered from an
ambient database, registry, cache, filesystem, provider, network, or process
state.

The snapshot has:

- one lifecycle scope;
- complete canonical members;
- member identities and canonical bytes;
- snapshot identity;
- snapshot digest; and
- canonical member ordering.

Invalid snapshot conditions fail closed, including missing members, duplicate
member identities, invalid member digests, mixed lifecycle scope,
non-canonical members, and non-canonical ordering.

### 6.1 Duplicate outcomes

| Case | Required outcome |
|---|---|
| No matching member identity | Candidate is not a duplicate |
| One matching member with byte-identical complete fact | `EXACT_DUPLICATE`; idempotently accepted and existing projection reused |
| One matching identity with any byte difference | `CONFLICTING_DUPLICATE`; fail closed |
| More than one matching member | Snapshot determinism failure; never select one member |
| Member identity/bytes/digest disagreement | Digest or determinism failure; never select one representation |
| Same fact against another valid snapshot | Same fact/edge identity and canonical bytes; only contextual duplicate status may differ |
| Same identity with different representation | Fail closed; no last-write-wins |

The snapshot is validation context only. It does not participate in
`LineageFactIdentity` or `LineageEdgeIdentity`:

```text
Identity(F, S1) == Identity(F, S2) == Identity(F)
```

This is a complete deterministic comparison rule and contains no ambient
state dependency.

## 7. Criterion 3 — Exact Authority B to T07 adapter mapping

**Result: PASS**

The closed T07 contract defines:

- `EconomicOutcomeInterpretationInput`;
- `EconomicOutcomeInterpretationResult`;
- `lifecycle_id`;
- `correction_lineage`;
- `supersession_lineage`;
- `provenance`;
- `status`;
- `failure_reason`; and
- the existing T07 failure vocabulary.

Authority B Section 5.7 maps every Authority B field to a T07 destination or
explicitly prohibits the field from being introduced.

### 7.1 Valid lineage destination mapping

| Authority B relation | T07 destination |
|---|---|
| `correction` | `EconomicOutcomeInterpretationInput.correction_lineage` and corresponding `EconomicOutcomeInterpretationResult.correction_lineage` |
| `supersession` | `EconomicOutcomeInterpretationInput.supersession_lineage` and corresponding `EconomicOutcomeInterpretationResult.supersession_lineage` |

Correction and supersession are therefore distinct and cannot be silently
converted into one another.

### 7.2 Field-level mapping verification

| Authority B field or value | T07 destination/behavior | Result |
|---|---|---|
| `contract_version` | Lineage member `contract_version` | PASS — preserved, not replaced by T07 version |
| `lineage_policy_version` | Lineage member `lineage_policy_version` | PASS — preserved exactly |
| `lifecycle_identity` | T07 `lifecycle_id` and lineage member lifecycle identity | PASS — mismatch fails closed |
| `predecessor_result_identity` | Lineage member predecessor identity | PASS — T07 validates existence and lifecycle membership |
| `successor_result_identity` | Lineage member successor identity | PASS — T07 validates existence and lifecycle membership |
| `lineage_type` | Selects `correction_lineage` or `supersession_lineage` | PASS — no semantic conversion |
| `lineage_fact_identity` | Lineage member fact identity | PASS — preserved and independently verified |
| `lineage_edge_identity` | Lineage member edge identity | PASS — preserved and independently verified |
| `authority_identity` | Lineage member authority and T07 provenance | PASS — asserting authority remains explicit |
| `provenance` | Lineage member provenance and T07 output provenance | PASS — fixed stage order preserved |
| `edge_digest` | Lineage member edge digest | PASS — T07 verifies digest |
| Complete canonical edge representation | Selected lineage member representation | PASS — no semantic transformation or replacement by T07 result digest |
| Validation state | T07 `status` | PASS — invalid Authority B projection becomes T07 `INVALID_INPUT` |
| Failure category | T07 existing `failure_reason` | PASS — deterministic many-to-one mapping |

Authority B does not populate or redefine T07's own
`contract_version`, `evaluator_version`, `status`, `failure_reason`, G2/G3/G4
fields, `result_digest`, or `classification_digest`.

For invalid Authority B input, the lineage field is semantically absent under
the existing T07 output contract. An invalid edge is never accepted as valid
lineage.

### 7.3 Failure mapping verification

Every invalid Authority B lineage state maps into T07's existing
`status = INVALID_INPUT` boundary without introducing a new T07 vocabulary:

| Authority B state | Existing T07 failure reason |
|---|---|
| Malformed fact | `MISSING_REQUIRED_INPUT` |
| Invalid identity | `MISSING_REQUIRED_INPUT` |
| Invalid lifecycle | `CONFLICTING_INPUT` |
| Missing endpoint | `MISSING_REQUIRED_INPUT` |
| Cross-lifecycle reference | `CONFLICTING_INPUT` |
| Conflicting duplicate | `CONFLICTING_INPUT` |
| Branching | `CONFLICTING_INPUT` |
| Cycle | `CONFLICTING_INPUT` |
| Self-reference | `CONFLICTING_INPUT` |
| Unsupported merge/convergence | `UNRESOLVED_RESIDUAL` |
| Provenance failure | `PROVENANCE_LINKAGE_FAILURE` |
| Determinism failure | `UNRESOLVED_RESIDUAL` |
| Digest failure | `DIGEST_FAILURE` |

`EXACT_DUPLICATE` is the sole idempotent success exception and reuses the
existing projection. It is not a new T07 failure state.

T07 retains authority to validate endpoints, graph conflicts, provenance,
digests, and canonical-head selection. Authority B supplies facts but cannot
repair, infer, or select among conflicting facts.

## 8. Criterion 4 — Boundary integrity

**Result: PASS**

Authority B is limited to immutable correction and supersession lineage for an
already-established lifecycle.

Authority B does not own or establish:

- realization;
- settlement;
- accounting;
- P&L;
- ROI;
- valuation;
- `WIN`;
- `LOSS`;
- `BREAKEVEN`;
- classification;
- wallet;
- custody;
- account ownership;
- signer;
- provider;
- RPC;
- DEX;
- network state;
- signing;
- broadcast;
- execution;
- Risk Governor decisions;
- Risk/Capital Authorization; or
- P09 behavior.

The presence of lineage evidence does not grant any prohibited authority
implicitly.

## 9. Graph, immutability, and temporal integrity

**Result: PASS**

The specification preserves the previously audited graph invariants:

- one direct successor edge at most per predecessor result;
- valid multi-hop correction/supersession chains;
- no direct branching;
- unsupported merge/convergence with fail-closed behavior;
- no self-reference;
- no cycles;
- no cross-lifecycle edges;
- no missing endpoints; and
- no mutation of historical results or identities.

Authority B has no authoritative timestamp field. Upstream timestamps may be
preserved as provenance only. They cannot participate in identity, duplicate
comparison, graph ordering, conflict resolution, or canonical-head selection.

## 10. Explicit verification of the three resolved blockers

| Previously resolved blocker | Verification result | Evidence |
|---|---|---|
| Canonical JSON escaping | PASS | Authority B Section 5.3 fixes NFC-before-escaping, quote/backslash/control escapes, direct non-ASCII UTF-8, sorted code-point keys, separators, null policy, and digest bytes |
| Deterministic duplicate-comparison context | PASS | Authority B Section 5.6 requires an explicit immutable lifecycle-scoped fact-set snapshot and prohibits ambient discovery |
| Exact Authority B → T07 mapping | PASS | Authority B Section 5.7 maps every field, distinguishes correction/supersession, preserves identity/provenance/digest, and maps every failure to existing T07 behavior |

These resolutions are internally consistent with the closed T07
specification. No T07 field meaning, failure vocabulary, canonical-head
authority, G2, G3, G4, or economic boundary is redefined.

## 11. Overall authority matrix

| Concern | Authority B | T07 |
|---|---|---|
| Assert correction fact | Owns | Validates |
| Assert supersession fact | Owns | Validates |
| Lineage fact identity | Owns | Verifies |
| Lineage edge identity/digest | Owns | Verifies |
| Lifecycle identity | Consumes Authority A identity | Validates |
| Predecessor/successor endpoint validity | Asserts relationship | Validates endpoint existence and lifecycle membership |
| Graph conflict detection | Supplies bounded graph semantics | Validates graph |
| Branch selection | Must not select | Must fail closed; selects none on conflict |
| Canonical head | Must not select | Owns per-lifecycle selection |
| Realization/accounting/classification | Prohibited | Consumes separately governed G2/G3/G4 outputs |
| Economic authority | None | T07 interpretation/assembly only |
| Custody/wallet/provider/signing/execution | Prohibited | Prohibited |

## 12. Implementation and phase boundary

This audit closes the Authority B specification only.

```text
AUTHORITY B IMPLEMENTATION = NOT AUTHORIZED
P08-T08 = NOT AUTHORIZED
P09 = NOT AUTHORIZED
```

No implementation, persistence, migration, API, dependency, provider
connection, wallet integration, signing, execution, economic formula, or
test is authorized by this audit.

The closed P08-T07 implementation and contract remain unchanged.

## 13. Final recommendation

Authority B may be recorded as:

```text
SPECIFICATION COMPLETE / CLOSED / AUDITED PASS
IMPLEMENTATION NOT AUTHORIZED
```

The next implementation step, if ever proposed, requires a separate explicit
authorization. It must preserve this closed semantic contract and must not
open P09 or any prohibited economic, custody, provider, wallet, signer, or
execution boundary.