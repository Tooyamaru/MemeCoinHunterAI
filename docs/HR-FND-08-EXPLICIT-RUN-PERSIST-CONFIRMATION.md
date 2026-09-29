# HR-FND-08 — Explicit Run / Persist Confirmation

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Reduce accidental operator mutation in Hunter Room by requiring a visible
two-step arm/confirm interaction before the browser sends the existing explicit
run or persistence confirmation.

## Behavior

- first press arms the selected action for the exact current case digest;
- second matching press sends the existing server request with
  `confirm_run=true` or `confirm_persist=true`;
- changing to a different case digest clears the armed action;
- completing run/persist clears the armed action;
- the operator can cancel an armed action manually;
- no automatic retry, polling, timer, or background mutation is introduced.

The browser arm state is only a UX safety layer. The backend remains
authoritative and still enforces the existing case digest, state machine,
one-shot claim, and explicit confirmation contracts.

## Boundary

This does not add new paper execution authority. It only adds an additional
operator confirmation gesture before already-authorized controlled-paper
run/persistence calls. No provider/source call, autonomous discovery, worker,
scheduler, wallet/signing, DEX routing, settlement, live trading, or economic
authority is added.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
