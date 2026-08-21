# P06-T03 — Bounded Deep Analysis Contract

**Status:** COMPLETE / CLOSED  
**Phase:** P06 — AI Decision Engine  
**Input:** One validated P05-T08 `OpportunityContext` and supplied point-in-time
analysis material  
**Output:** One immutable, bounded, non-authoritative `BoundedDeepAnalysis`

## Boundary

P06-T03 is an optional, standalone analytical record:

```text
P05-T08 OpportunityContext
        ↓
optional bounded deep analysis
        ↓
P06-T02 deterministic evaluation (authority)
        ↓
P06-T01 DecisionIntent
```

Analysis is never required by, consulted by, or authoritative over T02. Its
absence cannot change the deterministic result.

## Contract

The versioned contract is `p06-t03-v1`, evaluated by
`p06-t03-analysis-v1`. It preserves the context digest, source identity and
version, context reference time, supplied analysis and validation timestamps,
bounded supplied observations, and bounded generated narrative. Observations
retain source, evidence-reference, content, and observation time. Generated
narrative is a separate field and is never treated as authoritative evidence.

All records are frozen dataclasses. Canonical representations are immutable
and produce deterministic SHA-256 digests. Construction validates the
`OpportunityContext` and rejects non-canonical or tampered provenance,
unsupported versions, incomplete provenance, future observations, stale
analysis, invalid timestamps, and bounded-size violations. Time validation uses
only caller-supplied `validation_time`; no system clock is read.

## Explicit non-scope

This contract has no action, ranking, candidate-comparison, prioritization,
authorization, capital-allocation, risk-authorization, execution,
transaction, wallet, private-key, RPC, DEX, signing, broadcast, reconciliation,
provider-I/O, filesystem-I/O, database-I/O, or LLM behavior. It does not mutate
or overwrite P05 risk/evidence state.

P06-T02 remains authoritative for the deterministic decision result.