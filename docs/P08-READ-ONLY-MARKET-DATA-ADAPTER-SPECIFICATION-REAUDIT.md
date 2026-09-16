# P08 — Read-Only Market-Data Adapter Specification Re-Audit

**Status:** FORMAL RE-AUDIT COMPLETE / PASS / LIMITED IMPLEMENTATION AUTHORIZED
**Phase:** P08 — Outcome Learning
**Boundary:** Provider-neutral, immutable, read-only market observations
**Audited document:** `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION.md`
**Contract version:** `p08-read-only-market-data-observation-v1`
**Audit type:** Independent documentation-only formal re-audit

## 1. Scope and audit method

This re-audit independently reviewed the corrected formal specification and its
non-normative proposal against the repository-root governance rules, the prior
failed audit, and the directly relevant predecessor and downstream contracts.
The reviewed materials included:

- `REPLIT_RULES.md`;
- `PROJECT_STATE.md`;
- `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-PROPOSAL.md`;
- `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION.md`;
- `docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-SPECIFICATION-AUDIT.md`;
- the P02 token-universe, token-scoped observation, market-state, and market
  intelligence specifications;
- the P05 feature and opportunity-context specifications;
- the P06 decision-boundary specifications;
- the Risk/Capital and P07 v2 admission specification;
- the P07-T01, P07-T05, P07-T06, and P07-T07 specifications;
- the P08-T01 and P08-T02 specifications; and
- `docs/P08-G1-SIMULATION-ONLY-ECONOMIC-AUTHORITY-SPECIFICATION.md` and its
  formal audit.

The prior audit remains historical evidence. It is not overwritten or
reclassified. This document evaluates the corrected package only.

## 2. Executive verdict

**VERDICT: PASS**

All eleven formal-audit criteria pass. The corrected specification is the sole
normative contract for `p08-read-only-market-data-observation-v1`; the proposal
is explicitly historical and non-normative. The previous blockers are closed:

1. `chain_id` has one identical nullability rule in both documents; and
2. canonical text, nonnegative integer, mapping, sequence, depth, member, and
   byte limits are fixed and implementation-testable.

This re-audit authorizes only the separate limited implementation authorization
created with this document. It does not authorize any provider, network,
credential, persistence, workflow, or downstream behavior.

## 3. Criterion-by-criterion findings

### Criterion 1 — Internal consistency, authority, and implementation-testability

**Finding: PASS**

For this contract version, the formal specification explicitly declares itself
the sole normative contract and identifies the proposal as a non-normative
traceability document. The proposal repeats the same closed scalar, bounded
mapping, rejection, and precedence rules without variation. The exact top-level
fields, nested envelopes, requiredness, null behavior, supported versions,
validation order, output behavior, and focused implementation/test paths are
defined in the specification.

The former same-version authority conflict is therefore closed. The prior audit
file remains unchanged and records the historical FAIL only.

### Criterion 2 — Exact fields, types, null semantics, canonical serialization, identity, provenance, timestamps, freshness, and digests

**Finding: PASS**

The specification defines:

- the exact top-level observation fields and nested source, provenance, metric,
  and evaluation-context envelopes;
- explicit required-field and nullable-field behavior;
- one closed `CanonicalText` rule with NFC normalization, trimming, scalar and
  UTF-8 byte limits, and surrogate rejection;
- one closed ASCII decimal `NonNegativeInteger` representation, digit bound,
  leading-zero rule, and inclusive numeric range;
- exact bounded-mapping depth, member, sequence, and compact UTF-8 byte limits;
- forbidden sets, opaque values, non-string keys, unknown fields, binary
  floating point, NaN, and infinity;
- canonical compact UTF-8 JSON, key ordering, array semantics, UTC timestamps,
  decimal text, enum values, and explicit `null`;
- the fixed observation-identity projection and domain-separated SHA-256
  derivation;
- field, raw-payload, and observation digest coverage and nested-digest
  validation order; and
- bounded provenance linking source, identity, timestamps, cutoff, profile,
  predecessor, and field context.

The freshness contract requires explicit UTC cutoff and policy inputs, enforces
`observed_at <= availability_at <= cutoff_time`, distinguishes inclusive and
exclusive stale boundaries, rejects future and negative-age observations, and
never reads or substitutes ambient time.

### Criterion 3 — Provider, chain, exchange, wallet, and source neutrality

**Finding: PASS**

The contract contains no selected provider, vendor, exchange, venue, pool,
route, wallet, endpoint, SDK, transport, credential, or network behavior.
`source_id`, `chain_id`, `token_identity`, and `market_subject_id` are opaque
identity/provenance values only. No identity is derived from display metadata,
object identity, process state, insertion order, randomness, or current time.

### Criterion 4 — Preservation of P02 predecessor identity and digest ownership

**Finding: PASS**

The specification preserves P02-owned identity, source, observation,
predecessor-version, provenance, ordering, freshness, and digest facts when a
P02 predecessor is supplied. A P02-linked observation must copy its non-null
`chain_id` exactly, and the chain/token identity remains predecessor-owned. The
adapter does not re-admit, repair, refresh, aggregate, or mutate P02 state.

This agrees with the P02-T06/T07/T08 and market-intelligence boundaries, which
require explicit read-only predecessor contexts, local state ownership, stable
source-scoped identity, and no provider or ambient-state dependency.

### Criterion 5 — Preservation of P05 hard-risk, feature, scoring, and opportunity ownership

**Finding: PASS**

The adapter supplies evidence only. It does not create or replace a P05
candidate, evaluate safety or eligibility, calculate or reinterpret P05
features, score, rank, compare, reduce, create an opportunity record, or treat
`VALID` as `ELIGIBLE`. P05 retains ownership of candidate normalization,
hard-risk gating, feature availability, scoring, opportunity records, context,
and missing-data behavior.

The P05-T04 and P05-T08 contracts remain intact: existing feature snapshots and
opportunity context are preserved rather than recomputed or replaced.

### Criterion 6 — Preservation of P06 intent-only authority

**Finding: PASS**

The adapter does not fetch for P06, modify a P06 context, select an action,
produce confidence, create a `DecisionIntent`, or interpret evidence as
authorization. P06 remains the owner of deterministic analytical intent from a
validated P05 context. `BUY`, `WATCH`, `NO_TRADE`, and related analytical
outputs remain outside this adapter.

### Criterion 7 — Preservation of Risk/Capital authority and paper-only admission

**Finding: PASS**

Risk/Capital remains the owner of capital admission, Risk Governor state,
approval scope, validity, and the exact P07 v2 paper-only authorization
reference. The adapter cannot create, infer, renew, validate, or substitute
Risk/Capital authorization. A valid market observation is explicitly not a
Risk/Capital `PASS`.

The P07 v2 contract remains the sole owner of required Risk/Capital admission
linkage for the Safe V1 paper-entry path. Unknown, stale, missing, and invalid
market evidence remains fail-closed wherever the consuming policy requires it.

### Criterion 8 — Preservation of P07 non-economic simulation and `simulation_reference_time`

**Finding: PASS**

The adapter's cutoff is validation context only and does not replace P07's
explicit `simulation_reference_time`. P07 remains the owner of execution
observations, fills, paper-state transitions, ledger records, reconciliation,
the canonical non-economic paper result, and local history.

The adapter does not calculate fills, fees, spread, slippage, impact, latency,
or MEV; create an execution observation by hidden lookup; authorize a paper
lifecycle; mutate position, exposure, ledger, or history; reconcile external
truth; or turn an observation into an order or execution request.

### Criterion 9 — Preservation of G1 predecessor-owned validation and simulation-only recognition

**Finding: PASS**

The adapter adds no G1 authority, cutoff, economic state, or provenance link.
G1 validates its explicitly supplied P06 → P07 → P08 chain through the
predecessor contracts and owns only simulation-only recognition/finality. It
does not create market observations or reinterpret them as settlement,
valuation, accounting, realized P&L, or performance.

The audited G1 specification keeps P08-T02 `as_of_time` as the sole G1 cutoff
and keeps G2 realization eligibility, G3 accounting/economic-result
calculation, G4 classification, and P09 execution separately governed.

### Criterion 10 — Deterministic missing, invalid, stale, future, unsupported, duplicate, replay, contradiction, ordering, and reason-precedence behavior

**Finding: PASS**

The specification provides:

- explicit missing, invalid, unavailable, incomplete, future, stale, and
  unsupported semantics;
- one fixed reason vocabulary and one strict precedence order;
- deterministic canonicalization, identity, digest, and replay behavior;
- explicit immutable processing context rather than hidden registries or
  ambient state;
- separate exact-replay, duplicate, contradiction, and out-of-order behavior;
- explicit comparable-sequence requirements with no inferred arrival ordering;
  and
- unchanged state and context-digest behavior for rejected, stale, duplicate,
  replayed, contradictory, and out-of-order inputs.

The canonical rejection mapping and Section 12 precedence agree, including
`INVALID_TYPE` before missing, unsupported-version, and canonical-representation
conditions. The adapter rejects rather than repairs, truncates, substitutes,
fetches, or infers unsafe material.

### Criterion 11 — No credentials, provider leakage, ambient state, G2/G3/G4/P09 scope, and governance alignment

**Finding: PASS**

The corrected package excludes credentials, private keys, wallet material,
provider clients, SDKs, endpoints, network access, persistence, queues,
workflows, live trading, orders, execution, settlement, accounting, realized
P&L, G2, G3, G4, P09, AI/ML/LLM behavior, and autonomous behavior.

The pure validation contract forbids clocks, randomness, environment state,
process identity, filesystem/database/cache state, network state, hidden
registries, and unrepresented caller preferences. The repository state is
updated only to record this audit pass and the narrowly bounded authorization;
no downstream implementation or phase is started.

## 4. Limited implementation gate

Because every criterion passes, the separate limited authorization is created:

`docs/P08-READ-ONLY-MARKET-DATA-ADAPTER-IMPLEMENTATION-AUTHORIZATION.md`

That authorization is restricted to:

```text
core/data/read_only_market_data.py
tests/test_read_only_market_data.py
```

No package export change is authorized. The authorization requires immutable,
canonical, provider-neutral, read-only observations and focused deterministic
tests. It prohibits credentials, network calls, provider-specific integration,
wallets, signing, orders, execution, settlement, accounting, realized P&L,
G2, G3, G4, and P09.

## 5. Governance conclusion

The corrected Read-only Market Data Adapter specification is:

```text
COMPLETE / CLOSED / AUDITED PASS
```

The limited implementation authorization is separate from this re-audit and
does not authorize any behavior outside the two named source/test paths. G2,
G3, G4, and P09 remain not authorized.

No commit or push was performed.