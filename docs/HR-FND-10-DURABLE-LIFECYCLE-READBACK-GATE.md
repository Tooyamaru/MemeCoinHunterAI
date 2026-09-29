# HR-FND-10 — Durable Lifecycle Readback Gate

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Prevent Hunter Room from presenting a lifecycle readback action before RTI-03
has actually confirmed durable persistence.

## Behavior

- the lifecycle digest produced by a paper run is not treated as proof of storage;
- `Read persisted lifecycle` remains disabled until the case review exposes a
  server `readback_path` and persistence outcome `STORED` or `ALREADY_STORED`;
- the terminal detail panel shows the exact server readback path when present;
- the UI explains whether durable readback is available or still gated;
- history/catalog inspection remains independent because those entries are
  already sourced from durable persistence.

The server remains authoritative. Hunter Room does not synthesize a readback
path from the lifecycle digest and does not probe storage automatically.

## Boundary

This is presentation gating only. It does not change RTI-03 persistence,
perform automatic readback, retry persistence, poll storage, invoke providers,
or add autonomous discovery, worker/scheduler, wallet/signing, DEX routing,
settlement, live trading, or economic authority.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
