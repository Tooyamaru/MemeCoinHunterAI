# P01-CIP-01 — Controlled One-Shot Paper Experiment Input Preparation

**Status:** SPECIFICATION COMPLETE / READY FOR CONTROLLER REVIEW

**Implementation:** LIMITED IMPLEMENTATION AUTHORIZED / CI AND CLOSURE PENDING

**Contract:** `p01-cip-01-v1`

## 1. Purpose and authority

Prepare exactly one validated, in-memory `P01Osc02Request` from two
**already-produced** canonical results. This is application composition, not
experiment execution or a new domain owner:

```
exact P01Pfx01Result + exact PaperFactSourcingResult
    + explicit OSC-02 invocation_id
    → validate shared lineage and compatibility
    → construct exact P01Osc02Request once
    → STOP before OSC-02
```

PFX-01 already owns RTI-12/13, policy snapshot construction, and RTI-14.
PFS-01 already owns sourcing the simulation-only paper inputs. OSC-02 already
owns any later RTI-15/16 invocation. CIP-01 owns only cross-result validation
and assembly. It never replays, repairs, reinterprets, or moves owner authority.

## 2. Exact entry point and request

A future pure, stateless application service
`ControlledPaperExperimentInputPreparer.prepare(request: P01Cip01Request) -> P01Cip01Result`
accepts an immutable request with exactly:

- `invocation_id: str`, explicit controller-selected **OSC-02** invocation
  identity satisfying the existing `P01Osc02Request` syntax;
- `pfx_result: P01Pfx01Result`, the exact canonical prior PFX result;
- `pfs_result: PaperFactSourcingResult`, the exact canonical prior PFS result;
- `contract_version: str = "p01-cip-01-v1"`.

PFX's existing invocation ID and PFS replay identity remain separate identities.
Neither is silently adopted as the OSC invocation ID. This in-memory contract
does not reserve IDs, ensure globally unique invocations, or provide durable
idempotency.

The caller must have explicitly selected candidate/token and exact pool when
obtaining RTI-11, and supplied the decision rules/time, full PFX policy seed,
selected historical observation, PFS simulation assumptions, and canonical
execution/configuration/replay facts to their respective owners. CIP takes
their **exact results**; it accepts no independent substitute RTI-14, market
observation, policy snapshot, initial state, fill, or lifecycle evidence.

## 3. Canonical input validation

Before any ordinary bounded outcome, revalidate exact type, contract version,
structure, reason/outcome shape, digests and immutable nested owner links of
both supplied results using their existing canonical contracts. Revalidate
the nested PFS request, selected-source fingerprint and each supplied exact
canonical product. Missing/malformed/tampered inputs and unsupported versions
are standardized `ValueError`, never a stop outcome. Do not treat a matching
digest string as proof of exact object identity.

The same `P01Rti11CompositionResult` object must be present in
`pfx_result.request.rti11_result`,
`pfs_result.request.rti11_result`, and the exact nested RTI-14 → RTI-13 →
RTI-12 → RTI-11 predecessor chain when that chain is materialized. Compare
contract, digest, candidate/chain/token, controller-selected exact pool and
reference/selection lineage as exposed by that same object. Different
canonical RTI-11 objects, even with equal values, are not one exact case.

Cross-result identity mismatch is validation failure even when one upstream
result has a bounded terminal outcome. Neither result may be cloned or sourced
again to fix it.

## 4. Eligibility and bounded stops

Check eligibility after canonical and shared RTI-11 validation, in this order:

1. PFX must be `PREFIX_MATERIALIZED`, contain exact RTI-12/13/14 and policy
   snapshot, and its RTI-14 must be `AUTHORIZATION_MATERIALIZED` with
   canonical authorization `APPROVED` and effect
   `PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY`. Any other **canonical** PFX
   outcome or canonical Risk/Capital rejection returns `PREFIX_NOT_ELIGIBLE`
   with no OSC request.
2. PFS must be `FACTS_MATERIALIZED` with exact
   `PaperFillInstruction`, `PaperLifecycleEvidence`, and matching
   `InitialPaperStateIdentity`. Any canonical PFS refusal/unavailability
   returns `FACTS_NOT_MATERIALIZED` with no OSC request.

These are input-preparation outcomes. Preserve exact upstream outcomes and
reasons in the result's exact input objects; wrapper reasons are finite,
stage-specific, and safe. Never convert Risk/Capital rejection to approval or
PFS refusal to fabricated paper facts.

## 5. Cross-result compatibility for an eligible pair

Check only facts already present in the exact owner results:

- RTI-14's authorization must bind the exact nested DecisionIntent/context
  digests and exact decision subject; preserve PFX policy/authorization
  identity. PFS execution subject/target asset, historical source and ledger
  stream candidate/chain/token/pool must agree with the same RTI-11 selection.
- PFX policy snapshot and authorization `simulation_reference_time` must
  equal the explicit `pfs_result.request.simulation_reference_time`.
  Decision, observation availability, state as-of, source close/receipt,
  simulated fill, accounting observation, and paper evaluation times must
  satisfy existing PFX/PFS/P07/RTI-15/16 constraints: evidence exists before
  its use, fill is no later than simulation reference, and paper evaluation
  is no earlier than that reference. Preserve exact source timestamps and
  PFS freshness/valuation policy; never use wall clock.
- PFS's exact initial state must match its exact lifecycle prior-state
  projection, state identity, portfolio scope, and provenance. Require the
  explicitly represented paper portfolio ID in that scope to equal the
  PFX/RTI-14 paper portfolio ID; absence or contradiction fails validation.
  Replay ID, stream identity, sequence, predecessor reference and precommitted
  reconciliation expectation must remain those of PFS. No historical state
  may be synthesized.
- Pass PFS.request's **exact** `ExecutionObservation`,
  `SimulationConfigurationIdentity`, and `ReplayIdentity`; pass PFS
  result's **exact** `InitialPaperStateIdentity`,
  `PaperFillInstruction`, and `PaperLifecycleEvidence`.
  Validate PFS source/policy digests and their nested simulation provenance.
  The observed historical USD close remains a simulation price proxy;
  simulated capacity/friction/fees/accounting remain explicit assumptions.
  Neither constitutes a real executable quote, real liquidity or settlement.
- Validate the assembled exact `P01Osc02Request` with its existing constructor
  once. CIP may validate known cross-input invariants but may not precompute
  RTI-15 `PaperSimulationInput`, RTI-16 result, or lifecycle outcome.
  Invariants that only those canonical owners can establish remain theirs.

Identity, policy, state, reference-time, source freshness, version, units, or
digest mismatch is `ValueError`; no fallback, hidden default, alternate pool,
substitute candle, second policy, retry, or synthetic fact is permitted.

## 6. Output contract and deterministic digest

An immutable `P01Cip01Result` holds:

- exact `P01Cip01Request` and both exact predecessor objects;
- closed outcome: `REQUEST_PREPARED`, `PREFIX_NOT_ELIGIBLE`,
  `FACTS_NOT_MATERIALIZED`, or `PREPARATION_UNAVAILABLE`;
- finite safe reason codes and terminal stage;
- optional **exact** `P01Osc02Request` (present only for
  `REQUEST_PREPARED`);
- deterministic SHA-256 result digest.

Successful output retains the exact RTI-14 object and each exact PFS input
object by identity inside the OSC request, with the caller's exact OSC
invocation ID. CIP constructs no other canonical owner output. Its digest
binds contract/version, invocation ID, outcome/reasons/stage, PFX contract,
outcome and result digest, PFS contract, outcome and result digest, common
RTI-11 digest, RTI-14/authorization/policy digests where present, selected
historical source ID/fingerprint and PFS policy digest, exact execution,
configuration, initial-state, replay, fill and lifecycle digests where present,
and on success the OSC-02 contract plus its canonical input digest map.
Explicit absence of an OSC request is digested for non-success outcomes.

Canonical time serialization and field order must be fixed. Same canonical
inputs yield identical outputs/digests, including terminal cases. Exclude
wall clock, provider, environment, file/database state, object addresses,
exception text, retry counters and mutable global state. The digest is
**in-memory case identity**, not a durable full-replay archive, reservation,
or proof that execution happened.

## 7. Failure and delegation semantics

- Malformed/tampered/mismatched input, owner-constructor `ValueError`, or
  unsupported contract: standardized validation failure (`ValueError`),
  with no raw exception text disclosed.
- Unexpected construction failure (other than validation): bounded
  `PREPARATION_UNAVAILABLE`, finite safe reason, no OSC request and no retry.
  Cancellation propagates.
- Canonical PFX/PFS terminal inputs: finite non-ready outcomes described
  above, never `PREPARATION_UNAVAILABLE`.
- Invalid return from an injected constructor, if an implementation uses a
  verification seam: bounded `PREPARATION_UNAVAILABLE`, never a fabricated
  canonical request.

Maximum per invocation: one exact OSC-02 request constructor; zero calls to
RTI-11/12/13/14/15/16, PFX-01, PFS-01, OSC-01/02, P07 lifecycle, OSP,
RTI-03/04, provider, or persistence owners. No retries, automatic chain
execution or double materialization. Input/result canonical validation may
reconstruct immutable records for verification but cannot rerun their
**services** or mint alternative canonical paper facts.

## 8. STOP and scope

Hard STOP is the exact canonical `P01Osc02Request` in memory within the
prepared result. The caller must separately and explicitly invoke OSC-02;
OSC-02 still owns RTI-15 → RTI-16 and may stop or fail validation. CIP does not
make the paper run persistent or operationally autonomous.

Forbidden: autonomous candidate/pool selection, discovery/provider polling,
hidden market/safety input construction, scheduler/worker/queue, automatic
retry, recurring run, OSC-02 execution, RTI-15/16 pre-execution, RTI-04,
persistence/OSP/full replay archive, API/dashboard, wallet/signing/RPC/DEX,
transaction/broadcast, economic realization and live trading. G2 remains
BLOCKED / UNRESOLVED / NOT AUTHORIZED; G3/G4/P09 remain NOT AUTHORIZED.

## 9. Future verification and implementation gate

A future separately approved implementation must focus tests on exact
same-object RTI-11 and RTI-14/PFS identity continuity; APPROVED/REJECTED PFX
handling; PFS success/refusals; mismatched source/pool/portfolio/replay/state/
time/policy/fill/evidence; tampering/version and constructor failures;
deterministic digests; OSC request field identity; and **zero** service
delegations or persistence. Relevant regression covers PFX-01, PFS-01,
OSC-02, RTI-14/15, and canonical paper input validators.

The controller authorized limited implementation; that implementation may add
one thin application module, focused tests, minimal export and governance.
The authorization covers only the bounded in-memory preparer, focused tests,
minimal exports and governance. API/model/migration, provider/worker/scheduler,
wallet or execution code remains unauthorized.

`SPECIFICATION COMPLETE; LIMITED IMPLEMENTATION IN REVIEW`
