# Testing Strategy

The planned verification progression is:

```text
Unit tests
    ↓
Integration tests
    ↓
Data validation
    ↓
Historical simulation
    ↓
Real-time paper trading
    ↓
Small-capital validation
    ↓
Production
```

A feature is not done merely because code exists, the application starts, or an agent says it works. Each task must define explicit verification criteria and preserve evidence of the checks performed.

Future testing must cover failure paths, stale data, duplicate events, recovery, governance blocks, execution friction, reconciliation, and security boundaries—not only successful flows.

For P00-T01, targeted verification covers required file presence, phase consistency, concise continuation state, secret hygiene, shell syntax, documentation consistency, and confirmation that no trading integrations were added. A repository-wide audit is intentionally out of scope.
