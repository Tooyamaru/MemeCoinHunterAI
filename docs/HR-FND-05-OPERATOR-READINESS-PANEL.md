# HR-FND-05 — Manual Operator Readiness Panel

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Expose the authenticated no-I/O Operator Facade readiness projection inside
Hunter Room without adding provider probes, polling, automatic retries, or
mutation.

## Behavior

- the operator must explicitly press `Check readiness`;
- the browser sends one authenticated GET to
  `/api/v1/operator/paper-cases/readiness`;
- `READY` and bounded `NOT_READY` responses are rendered with the server's
  database/registry/prepare/run/persist configuration checks;
- the panel states that provider connectivity is not probed;
- no readiness call runs automatically on page load or on a timer;
- the bearer remains session-memory only.

The readiness panel is informational. Existing prepare/run/persist controls
continue to rely on server-side authorization and state-machine checks rather
than a client-side readiness cache.

## Boundary

This milestone performs no provider/source access and no paper mutation by
itself. It does not add discovery, polling, retry loops, workers/schedulers,
wallet/signing, DEX routing, settlement, live trading, or economic authority.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
