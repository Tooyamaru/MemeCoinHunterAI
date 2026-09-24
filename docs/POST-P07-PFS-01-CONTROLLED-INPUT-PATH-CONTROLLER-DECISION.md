# Post-P07-PFS-01 Controlled Input Path — Controller Decision

**Status:** DIRECTION B SELECTED / SPECIFICATION-ONLY FOLLOW-UP AUTHORIZED

**Baseline:** GitHub `main` at `49f8081a62ec189fc6a9cc51ca8c1458edd58ca0`.

The controller selects Direction B from
`docs/POST-P07-PFS-01-CONTROLLED-INPUT-PATH-DEPENDENCY-REVIEW.md`:

> require prevalidated Decision/Risk-Capital lineage and do not allow OSC to
> rerun already-produced RTI-12/13/14 owners.

## Selected architecture

The smallest bounded architecture change is a new suffix caller that starts from
one already-produced canonical RTI-14 result and invokes only the existing
RTI-15 and RTI-16 owners.

Selected gate:

**P01-OSC-02 — Prevalidated Risk/Capital Suffix One-Shot Paper Caller**

This gate does not replace P01-OSC-01. OSC-01 remains the explicit-input
RTI-11→RTI-16 caller. OSC-02 is a separate staged entry point for a controller
workflow that has already produced and validated the exact RTI-12/13/14 prefix.

## Why this resolves the identified lineage gap

A canonical `P01Rti14RiskCapitalContinuationResult` already contains and binds:

- the exact RTI-13 result;
- the exact RTI-12 result nested below RTI-13;
- the exact RTI-11 result nested below RTI-12;
- the exact `DecisionIntent`;
- the exact `PaperRiskCapitalPolicySnapshot`;
- the exact `PaperRiskCapitalAuthorizationResult`, when materialized;
- exact context/decision/policy/authorization digests and provenance.

Starting the controlled-paper suffix from that exact RTI-14 result therefore
avoids recomputing RTI-12, RTI-13, or RTI-14 and preserves owner cardinality.

The suffix caller may then pass the exact RTI-14 result and explicit simulation
inputs to RTI-15 once, followed by RTI-16 once.

## Explicit scope boundary

Specification-only at this checkpoint. No runtime/source implementation is
authorized yet.

The formal OSC-02 specification must:

- accept one canonical RTI-14 result;
- accept explicit RTI-15 inputs;
- accept exact PFS-compatible fill/lifecycle inputs;
- call RTI-15 at most once;
- call RTI-16 at most once;
- preserve exact nested owner results;
- stop at the exact RTI-16 result;
- never invoke RTI-11/12/13/14;
- never invoke OSC-01;
- never invoke persistence or OSP.

This decision does not yet define a new prefix preparer. A later, separately
governed gate may coordinate production of the exact RTI-12/13/14 prefix and
controller-bound policy snapshot if needed.

## Forbidden surfaces

No provider/network/polling, autonomous selection, runtime loop,
worker/scheduler/queue, API/dashboard publication, persistence, RTI-03/04,
wallet/signing/RPC/DEX, execution/live trading, economic realization, G2, G3,
G4, or P09 is authorized.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.
G3/G4/P09 remain **NOT AUTHORIZED**.
