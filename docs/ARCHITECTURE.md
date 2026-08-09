# Architecture

## Logical layers

1. **Data layer** — source adapters, raw events, validation, normalization, timestamps, freshness, and persistence.
2. **Intelligence layer** — market state, features, signals, safety evidence, and regime context.
3. **Opportunity layer** — signal fusion, candidate ranking, quality, and phase analysis.
4. **Decision layer** — bounded decisions with evidence, confidence, uncertainty, invalidation, and entry quality.
5. **Governance / risk layer** — independent authorization, exposure controls, circuit breakers, and emergency stop.
6. **Execution layer** — paper execution first; later deterministic interfaces, routers, and venue adapters.
7. **Learning layer** — immutable decision/outcome history, evaluation, and controlled model/strategy versions.
8. **Presentation / dashboard layer** — read-oriented visibility into state, evidence, decisions, risk, and outcomes.
9. **Infrastructure layer** — configuration, logging, health, workers, database, deployment, and recovery.

## Dependency direction

Data flows toward intelligence, opportunity, decision, governance, execution, and learning. Presentation observes published state; it does not bypass governance. Modules should communicate through explicit contracts and remain replaceable.

## Mandatory control boundary

```text
Decision Engine
      ↓
Risk Governor
      ↓
Execution Interface
      ↓
Execution Router
      ↓
Venue Adapter
```

The Decision Engine must never hold unrestricted fund control or call a venue directly. The Risk Governor has higher authority and can ALLOW, REDUCE, BLOCK, or EMERGENCY STOP. P00 does not implement these services.

## Future portability

The initial Replit environment is for development and preview. GitHub is the source of truth. A future stable 24/7 runtime may use Railway, but Railway is explicitly out of scope for P00.
