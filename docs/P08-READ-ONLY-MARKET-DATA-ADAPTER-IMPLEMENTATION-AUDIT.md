# P08 — Read-Only Market-Data Adapter Implementation Audit

**Status:** FORMAL IMPLEMENTATION AUDIT COMPLETE / FAIL — CORRECTIVE WORK REQUIRED  
**Audit date:** 2026-09-16  
**Phase:** P08 — Outcome Learning  
**Boundary:** Provider-neutral, immutable, read-only market observations  
**Contract version:** `p08-read-only-market-data-observation-v1`  
**Audit type:** Documentation-only post-implementation audit

## 1. Scope and reviewed materials

This audit reviewed the repository rules, current project state, the normative
Read-only Market Data Adapter specification, its formal re-audit, the limited
implementation authorization, the authorized implementation and focused tests,
and the directly relevant P02, P05, and P06 predecessor/downstream contracts.

Reviewed files:

- `REPLIT_RULES.md`
- `PROJECT_STATE.md`
- `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION.md`
- `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION-REAUDIT.md`
- `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-IMPLEMENTATION-AUTHORIZATION.md`
- `core/data/read_only_market_data.py`
- `tests/test_read_only_market_data.py`
- `docs/P02-T06_SPECIFICATION.md`
- `docs/P02-T07_SPECIFICATION.md`
- `docs/P02-T08_SPECIFICATION.md`
- `docs/P05-T04_SPECIFICATION.md`
- `docs/P05-T08_SPECIFICATION.md`
- `docs/P06-SPECIFICATION.md`
- `docs/P06-T02_SPECIFICATION.md`
- `docs/P06-T03_SPECIFICATION.md`

The implementation authorization names only
`core/data/read_only_market_data.py` and
`tests/test_read_only_market_data.py` as implementation/test paths. No source,
test, dependency, workflow, or environment file was changed during this audit.

## 2. Verification

The required verification commands were run exactly:

```text
uv run pytest -q tests/test_read_only_market_data.py
.................                                                        [100%]
17 passed in 0.20s

uv run python -m compileall -q core/data/read_only_market_data.py
PASS

git diff --check
PASS

git status --short
clean before this audit document was created
```

## 3. Criterion findings

### Criterion 1 — Authorized implementation paths

**Finding: PASS**

The pre-audit working tree was clean, and the implementation authorization
restricts implementation and focused tests to the two named paths. This audit
does not modify either path.

### Criterion 2 — Exact contract fields, types, null rules, bounds, canonicalization, provenance, and digests

**Finding: FAIL**

The constructed dataclass path covers the primary immutable observation shape,
canonical text checks, metric envelopes, timestamps, freshness boundaries, and
SHA-256 digest material. However, the public mapping path does not enforce the
formal exact-field contract consistently:

- `from_mapping` methods use `.get(...)` and do not reject unknown fields.
- Missing mapping members are collapsed into `None` rather than preserving the
  specification’s distinction between absent required fields and explicit
  `null`.
- `source_metadata` and `field_provenance` are passed to `_validate_bounded`
  without first requiring a mapping root, so a non-mapping bounded-envelope
  value can reach validation as if it were a bounded value.

Because `validate_observation` and `derive_observation_id` accept mappings, these
are observable contract-boundary gaps, not merely unused convenience methods.

### Criterion 3 — Provider, chain, exchange, wallet, and source neutrality

**Finding: PASS**

The implementation contains no provider client, endpoint, SDK, exchange,
venue, wallet, RPC, credential, or network behavior. Identity fields remain
opaque values, and no authority is assigned to a source.

### Criterion 4 — P02 predecessor identity and digest ownership

**Finding: PASS**

The adapter preserves explicit chain, token, market-subject, source, and
predecessor digest values through provenance links. It does not refresh,
re-admit, mutate, or replace P02 state, and it does not claim ownership of
P02 materialization or source lifecycle.

### Criterion 5 — P05 hard-risk, feature, scoring, and opportunity ownership

**Finding: PASS**

The implementation exposes only normalized market evidence. It does not
calculate features, evaluate safety or eligibility, score, rank, compare,
reduce, create opportunities, or treat `VALID` as eligibility.

### Criterion 6 — P06 intent-only authority

**Finding: PASS**

No decision intent, action, confidence, decision context, authorization, or
execution behavior is present. The adapter remains evidence-only and does not
alter P06-owned semantics.

### Criterion 7 — Risk/Capital authority and paper-only admission

**Finding: PASS**

No Risk/Capital authorization, Risk Governor behavior, capital admission,
paper-entry authorization, or downstream approval is created or inferred.

### Criterion 8 — P07 non-economic simulation and simulation reference time

**Finding: PASS**

The implementation does not create fills, positions, ledger entries, paper
state, execution observations, reconciliation results, or simulation outcomes.
Its caller-supplied cutoff remains local validation context and does not replace
P07’s `simulation_reference_time`.

### Criterion 9 — G1 predecessor-owned validation and simulation-only recognition

**Finding: PASS**

The adapter adds no G1 authority, recognition, finality, economic state,
settlement meaning, or provenance reinterpretation.

### Criterion 10 — Deterministic failure behavior and focused test coverage

**Finding: FAIL**

The visible happy-path and several rejection paths pass the focused suite, but
the implementation does not fully implement the required global reason
precedence for structurally invalid observations. `_check_observation_structure`
performs multiple checks inside one `try` block and stops at the first
`_ContractError`. For example, an unsupported contract version encountered
before a later invalid runtime type can prevent the required higher-precedence
`INVALID_TYPE` from being collected. Mapping-conversion failures are also
collapsed to `INVALID_TYPE` by a broad exception handler.

The focused tests do not cover the full authorization minimum. In particular,
they do not lock down all of:

- explicit `null` versus omitted required/optional mapping fields;
- unavailable and invalid metric statuses;
- non-finite and other non-canonical numeric inputs;
- unknown top-level and nested mapping fields;
- mapping-input reason precedence;
- complete canonical timestamp, decimal, enum, and null behavior;
- missing sequence and unknown/uncomparable ordering behavior; and
- predecessor non-mutation as a dedicated negative test.

The 17 passing tests therefore demonstrate useful behavior but are not enough
to establish the authorized implementation as complete.

### Criterion 11 — No credentials, provider leakage, ambient state, G2/G3/G4/P09 scope, and governance alignment

**Finding: PASS**

The implementation imports no network, provider, persistence, workflow, wallet,
signing, execution, settlement, accounting, G2, G3, G4, or P09 behavior. It
does not read a wall clock, environment, filesystem, database, cache, or hidden
registry during validation.

## 4. Executive verdict

**VERDICT: FAIL — NOT READY FOR FORMAL CLOSURE**

Criteria 2 and 10 fail because the mapping boundary and strict reason-precedence
behavior do not yet match the normative specification exactly. The focused
tests also do not cover all required negative and boundary cases from the
implementation authorization.

`PROJECT_STATE.md` was intentionally left unchanged because the authorization
requires an implementation audit to pass before the adapter may be considered
complete or closed.

No commit or push was performed.