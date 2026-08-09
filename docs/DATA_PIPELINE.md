# Data Pipeline

```text
Raw blockchain / DEX data
        ↓
Validation
        ↓
Normalization
        ↓
Market state
        ↓
Features
        ↓
Signals
        ↓
Opportunity
        ↓
Decision
        ↓
Risk
        ↓
Paper / execution
        ↓
Outcome
```

## Data contract principles

- Preserve both event timestamp and received timestamp.
- Compute data age and expose freshness explicitly.
- Stale data must be visible and may block downstream decisions.
- Detect duplicate events and preserve sequence integrity where the source supports it.
- Normalize units, identifiers, decimals, direction, and venue metadata before feature work.
- Track source health, failure state, retries, recovery, and resynchronization.
- Preserve the evidence available at each decision point; do not silently overwrite history.
- Separate raw source records from normalized market state and derived features.

## Failure handling

Bad, missing, duplicated, delayed, or contradictory input must produce an explicit quality state. Downstream consumers must fail closed when required data is stale or unavailable. Recovery must be observable and replayable before a stream is considered healthy again.

## P00 boundary

No blockchain or DEX connection, scanner, signal calculation, trading simulator, or execution implementation belongs in this phase.
