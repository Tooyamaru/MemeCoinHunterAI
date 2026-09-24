# Post-P01-OSC-02 Controlled Input Path — Bounded Successor Review

**Status:** REVIEW COMPLETE / P01-PFX-01 SELECTED FOR SPECIFICATION

**Baseline:** GitHub `main` at `01693351be370eef9b959f556205c830c418d98a`.
P01-OSC-02 is COMPLETE / CLOSED / CI PASS.

## Question

What is the smallest missing governed capability required before one complete,
prevalidated controlled paper experiment can be assembled without rerunning
closed owners?

## Finding

OSC-02 solves only the **suffix** problem. It accepts one already-produced
canonical RTI-14 result and then owns at most one RTI-15 and one RTI-16 call.

The remaining missing bounded capability is the **prefix** preparation step:

`RTI-11 → RTI-12 → RTI-13 → exact policy snapshot → RTI-14`

The repository already owns RTI-12, RTI-13, the canonical
`PaperRiskCapitalPolicySnapshot` constructor, and RTI-14. The missing
integration concern is ordering and exact binding.

A Risk/Capital policy snapshot cannot be fully canonical before RTI-13 because
its `decision_intent_digest`, `context_digest`, and corresponding provenance
must match the exact materialized decision. Supplying a prebuilt snapshot before
RTI-13 recreates the lineage problem that motivated OSC-02.

Therefore the smallest missing composition is a staged prefix coordinator that:

1. accepts one exact canonical RTI-11 result;
2. runs RTI-12 at most once;
3. runs RTI-13 at most once with explicit ruleset/time;
4. constructs exactly one canonical policy snapshot **after** RTI-13 from
   explicit controller-owned policy material plus exact decision/context
   identity;
5. runs RTI-14 at most once;
6. preserves the exact RTI-12/13/14 objects;
7. stops at exact RTI-14.

## Why a policy seed is required

The repository has a canonical final `PaperRiskCapitalPolicySnapshot`, but no
canonical pre-decision input type that can safely carry the explicit policy
material before the decision/context digests exist.

The selected specification therefore introduces one application-layer immutable
input record, provisionally `PaperRiskCapitalPolicySeed`.

It is not a new Risk Governor or domain policy owner. It only carries all
controller-supplied fields that are independent of the yet-unmaterialized
DecisionIntent. The prefix coordinator must derive only the fields that are
owned by the exact RTI-13 result:

- candidate/chain/token scope identity where required;
- `decision_intent_digest`;
- `context_digest`;
- P05/P06 contract/evaluator/ruleset provenance;
- state digest references already present on the supplied risk/capital states.

No threshold, budget, risk status, lifecycle ID, portfolio ID, time window,
state, amount, or limit may be defaulted or inferred.

## Selected gate

**P01-PFX-01 — Deterministic Prevalidated Decision/Risk-Capital Prefix Preparation**

This is specification-only at this checkpoint.

## STOP / forbidden boundary

P01-PFX-01 stops at exact RTI-14.

It must never call RTI-15, RTI-16, OSC-01, OSC-02, PFS, OSP, RTI-03/04,
provider/network/polling, autonomous selection, worker/scheduler/queue,
API/dashboard, wallet/signing/RPC/DEX, execution/live trading, economic
realization, G2, G3, G4, or P09.

G2 remains **BLOCKED / UNRESOLVED / NOT AUTHORIZED**.
G3/G4/P09 remain **NOT AUTHORIZED**.
