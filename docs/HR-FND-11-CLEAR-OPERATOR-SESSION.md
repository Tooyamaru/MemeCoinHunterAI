# HR-FND-11 — Clear Operator Session

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Give the operator one explicit control to remove the current Hunter Room
session state from browser memory after controlled-paper work is complete.

## Behavior

`Clear operator session` clears, in the current browser tab:

- bearer token;
- API base target;
- prepare payload (reset to the empty explicit template);
- active/open case handles and review projection;
- run/persist response projections;
- durable lifecycle readback and loaded history catalog;
- readiness and prepare-validation results;
- armed run/persist action state;
- current operator message.

The control does not call the backend, delete durable RTI-03 data, revoke a
server token, mutate the process-local registry, or alter any paper lifecycle.

## Security / authority boundary

This is a client-memory cleanup control only. Token issuance/revocation remains
outside Hunter Room. Durable persisted lifecycles remain available through
their existing read-only owners after a new authenticated session is created.

No provider/source call, retry/polling, autonomous discovery, worker/scheduler,
wallet/signing, DEX routing, settlement, live trading, or economic authority is
added.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
