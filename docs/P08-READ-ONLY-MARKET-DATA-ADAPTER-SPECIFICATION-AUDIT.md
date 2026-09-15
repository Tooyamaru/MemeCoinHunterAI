# P08 — Read-Only Market-Data Adapter Specification Audit

**Status:** FORMAL AUDIT COMPLETE / FAIL / IMPLEMENTATION NOT AUTHORIZED  
**Phase:** P08 — Outcome Learning  
**Audited document:** `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION.md`  
**Contract version reviewed:** `p08-read-only-market-data-observation-v1`  
**Audit basis:** Independent documentation review against the repository-root
governance rules, the directly relevant P02, P05, P06, Risk/Capital, P07, and
G1 contracts, and the eleven Gate 1 criteria defined by the specification.

## 1. Scope and audit method

This audit reviewed the formal specification and the directly relevant
governance and downstream ownership documents. The review covered:

- repository-root governance and project-state requirements;
- the P02 identity, observation, market-intelligence, provenance, ordering,
  freshness, and digest boundaries;
- P05 candidate, feature, risk, score, and opportunity-context ownership;
- P06 intent-only decision behavior;
- Risk/Capital authority and the P07 v2 paper-admission linkage;
- P07 point-in-time simulation, non-economic result, and reconciliation
  boundaries; and
- G1 predecessor-owned validation and simulation-only recognition.

The audit is a documentation gate only. It does not authorize source code,
tests, dependencies, providers, network access, persistence, workflows, or
implementation.

## 2. Executive verdict

**VERDICT: FAIL**

The specification correctly establishes a narrow, immutable, provider-neutral,
read-only, paper-only evidence boundary and preserves the authority of its
predecessors and downstream consumers. However, it is not yet sufficiently
closed for a passing formal audit:

1. The earlier proposal and the formal specification use the same contract
   version while expressing different `chain_id` requiredness semantics. The
   formal specification does not explicitly state that it supersedes the
   proposal for that version, so an implementation cannot identify one
   authoritative wire contract from the repository documents alone.
2. Exact canonical representation is deferred for `NonNegativeInteger`,
   bounded text, and bounded mapping size/byte limits. Those choices are part
   of the contract’s type and canonicalization behavior and cannot be left to
   a later implementation authorization while the audit criterion requires
   exact, implementation-testable types and serialization.

Because not every criterion passes, `PROJECT_STATE.md` must remain unchanged
with the status **COMPLETE / AWAITING FORMAL AUDIT**. This audit does not
authorize implementation.

## 3. Criterion-by-criterion assessment

### Criterion 1 — Internal consistency and implementation-testability

**Result: FAIL**

The formal specification is detailed and most behaviors are testable, but the
repository contains an unresolved same-version contract conflict:

- the proposal with the same version,
  `p08-read-only-market-data-observation-v1`, defines `chain_id` as a
  non-empty canonical identity; and
- the formal specification permits explicit `null` for `chain_id` when the
  consumer profile allows it.

The formal specification appears intended to be the later authoritative
document, but it does not explicitly supersede the proposal or declare the
proposal non-authoritative for this version. A future implementer could
therefore select incompatible requiredness rules without violating either
document’s stated version.

The deferred type and size decisions described under Criterion 2 also prevent
the contract from being fully implementation-testable as written.

### Criterion 2 — Exact fields, types, null semantics, canonical serialization, identity, provenance, timestamps, freshness, and digests

**Result: FAIL**

The specification successfully defines the top-level fields, nested envelopes,
explicit `null` behavior, UTC timestamps, freshness equations, SHA-256
coverage, provenance consistency, and fixed reason precedence. It also
defines the observation identity projection and digest exclusions clearly
enough to establish the intended algorithm.

The criterion nevertheless fails because exact canonical types and bounds are
left open:

- `NonNegativeInteger` may be either canonical base-10 integer text or a
  bounded integer value, with the choice deferred to implementation
  authorization.
- `CanonicalText` requires a documented maximum length, but the actual
  maximum is deferred.
- bounded text and mapping byte/depth/size limits are deferred to the future
  implementation authorization.

These alternatives change canonical representation, accepted input, digest
material, and rejection behavior. They must be fixed in the audited
specification, or the contract version must be explicitly treated as
unapproved until a versioned correction is audited.

The identity projection’s placeholder values are not independently blocking:
the specification states that actual populated values replace the examples and
provides fixed keys, order-independent canonicalization, a domain prefix, and
SHA-256 derivation. The blocking issue is the unresolved type/bound choice, not
the use of illustrative values in the projection example.

### Criterion 3 — Provider, chain, exchange, wallet, and source neutrality

**Result: PASS**

The contract does not select or name a provider, chain, exchange, venue, pool,
route, wallet, endpoint, SDK, or transport. Source-specific parsing,
credentials, transport, raw-payload handling, and source error translation
remain outside the canonical observation. `source_id` is provenance, not
authority, and source aggregation or source preference is excluded.

The explicit nullable chain behavior is a contract-closure issue assessed
under Criteria 1 and 2; it does not introduce provider or chain dependence.

### Criterion 4 — Preservation of P02 predecessor identity and digest ownership

**Result: PASS**

When a P02 predecessor is supplied, the specification requires exact copying
and validation of the predecessor’s identity and digest context and prohibits
re-admission, repair, refresh, aggregation, or mutation of P02 state. It
preserves source, observation, predecessor-version, and predecessor-digest
references and leaves P02-owned market-observation admission and state
ownership intact.

The specification also correctly distinguishes the adapter’s pure validation
context from P02 freshness, ordering, materialization, and local-state
ownership.

### Criterion 5 — Preservation of P05 hard-risk, feature, scoring, and opportunity ownership

**Result: PASS**

The adapter supplies evidence only. It does not create or replace a P05
candidate, evaluate safety, calculate features, score, rank, compare, reduce,
create an opportunity record, or treat `VALID` as `ELIGIBLE`. P05 retains its
own missing-data semantics and downstream input validation.

This is consistent with P05-T04’s rule that existing feature snapshots are
validated and preserved rather than recalculated, and with P05-T08’s
evidence-first opportunity-context boundary.

### Criterion 6 — Preservation of P06 intent-only authority

**Result: PASS**

The specification does not fetch for P06, modify P06 context, choose an
action, produce confidence, create a `DecisionIntent`, or interpret market
evidence as authorization. P06 remains a deterministic analytical intent
boundary and does not gain ranking, authorization, or execution behavior from
this adapter.

### Criterion 7 — Preservation of Risk/Capital authority and paper-only admission

**Result: PASS**

The specification explicitly states that a valid observation is not a
Risk/Capital `PASS` and that the adapter cannot create, infer, renew, validate,
substitute, or attach authorization. It preserves Risk/Capital ownership of
approval scope, validity, and the exact paper-only authorization reference
required by the current P07 v2 path.

Unknown, stale, missing, and invalid evidence remains fail-closed where the
Risk/Capital policy requires it. The adapter does not authorize even paper
execution.

### Criterion 8 — Preservation of P07 non-economic simulation and `simulation_reference_time`

**Result: PASS**

The specification makes the adapter cutoff validation-only and expressly states
that it does not replace P07’s `simulation_reference_time`. It does not
calculate fills, fees, spread, slippage, impact, latency, or MEV; create an
execution observation by lookup; authorize a paper lifecycle; mutate paper
state, positions, exposure, ledger, or history; or reconcile external truth.

P07 remains the owner of its own execution-observation contract, temporal
validation, paper simulation, reconciliation, and canonical non-economic
result.

### Criterion 9 — Preservation of G1 predecessor-owned validation and simulation-only recognition

**Result: PASS**

The specification gives G1 no new authority, cutoff, economic state, or
provenance ownership. It states that G1 validates predecessor-owned contracts,
does not create market observations, and does not reinterpret an observation
as settlement, valuation, accounting, realized P&L, or performance.

This preserves G1’s requirement for an explicitly supplied, complete,
validated P06 → P07 → P08 chain and its simulation-only recognition boundary.

### Criterion 10 — Deterministic missing, invalid, stale, future, unsupported, duplicate, replay, contradiction, ordering, and reason-precedence behavior

**Result: PASS**

The specification provides:

- explicit missing, invalid, unavailable, future, stale, unsupported, and
  incomplete semantics;
- a fixed reason vocabulary and strict precedence;
- explicit immutable processing context rather than hidden registries or
  ambient state;
- distinct replay, duplicate, contradiction, and out-of-order behavior;
- explicit sequence/cursor requirements and no inferred arrival ordering;
- unchanged state and digest behavior for rejected and duplicate input; and
- deterministic canonicalization and SHA-256 replay requirements.

The adapter rejects rather than repairs, substitutes, truncates, fetches, or
infers when identity, digest, timestamp, provenance, or canonicalization
material is unsafe.

### Criterion 11 — No credentials, provider leakage, ambient-state dependency, G2/G3/G4/P09 scope, and alignment with repository governance

**Result: PASS**

The specification excludes credentials, private keys, wallet material, provider
clients, SDKs, endpoints, network access, persistence, caches, queues,
workflows, live trading, orders, execution, settlement, accounting, realized
P&L, G2, G3, G4, P09, AI/ML/LLM behavior, and autonomous behavior. Its pure
validation contract forbids clocks, randomness, environment state, process
identity, filesystem/database/cache state, network state, hidden registries,
and unrepresented caller preferences.

The current `PROJECT_STATE.md` status remains consistent with the audit being
unfinished and implementation remaining unauthorized. Since the verdict is
FAIL, no audited-closed state update is permitted.

## 4. Required corrective actions before re-audit

Before requesting another formal audit, the specification package must:

1. state explicitly which document is authoritative for
   `p08-read-only-market-data-observation-v1`, or revise the versioning so the
   proposal and formal specification cannot be mistaken for competing
   contracts;
2. choose one canonical representation for `NonNegativeInteger`;
3. define the maximum length and encoding bounds for `CanonicalText`;
4. define the exact depth, entry-count, and byte-size bounds for
   `BoundedMapping` and any bounded metadata; and
5. ensure the corrected specification, proposal relationship, and
   `PROJECT_STATE.md` status are synchronized before re-audit.

These corrections require a separate documentation change and a new formal
audit. They do not authorize runtime implementation.

## 5. Governance conclusion

The read-only market-data adapter is directionally compatible with the
repository’s evidence-first, risk-first, paper-only architecture. The
formal-audit gate is **not passed** because the versioned contract is not yet
fully closed and exact at the representation level.

`PROJECT_STATE.md` intentionally remains:

> Read-only Market Data Adapter specification is COMPLETE / AWAITING FORMAL
> AUDIT; implementation remains NOT AUTHORIZED.

No source code, tests, dependencies, workflows, providers, persistence, or
external access are authorized by this audit.