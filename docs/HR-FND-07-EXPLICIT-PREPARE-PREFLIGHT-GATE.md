# HR-FND-07 — Explicit Prepare Preflight Gate

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Require the Hunter Room operator to complete both existing manual preflights
before the browser enables the Prepare action.

## Required preflights

1. Operator readiness must report `READY`.
2. The current explicit prepare payload must report `VALID` through the
   no-I/O prepare validation endpoint.

Changing the API base clears both cached preflights because a different server
may expose different configuration or decoder behavior. Changing the bearer
clears readiness because the current authenticated operator session changed.
Editing or resetting the payload clears payload validation.

## Authority

This is a browser usability/safety gate only. It does not replace server-side
authentication, canonical validation, registry state, or owner contracts.
The server remains authoritative if a caller bypasses the UI.

`READY` still does not probe provider connectivity and `VALID` still does not
mean eligibility or RTI-11 success. Prepare may therefore still stop or fail
through its existing bounded server outcomes.

## Boundary

No provider/source call, retry, polling, autonomous discovery, worker/scheduler,
wallet/signing, DEX routing, settlement, live trading, or economic authority is
added.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
