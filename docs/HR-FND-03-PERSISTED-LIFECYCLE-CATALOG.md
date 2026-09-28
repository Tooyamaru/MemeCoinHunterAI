# HR-FND-03 — Manual Persisted Lifecycle Catalog

Status: IMPLEMENTATION / READ-ONLY CONTROLLED PAPER

## Purpose

Expose the existing bounded RTI-07/RTI-06 persisted paper lifecycle read surface
inside Hunter Room without adding a new backend owner, ranking rule, polling
loop, analytics claim, or automatic activity.

## UI behavior

Hunter Room now provides a manual **Persisted lifecycle catalog** panel.

- `Load` requests one RTI-07 page with `limit=20`.
- `Next page` uses the returned exclusive `next_after_digest` cursor.
- `First page` clears the cursor.
- Selecting one digest performs exactly one RTI-06 detail read.
- The detail panel shows only the canonical read outcome, lifecycle/result
  digests, artifact count and artifact kinds already returned by the read API.
- No page is loaded automatically and no timer/polling loop is introduced.

RTI-07 orders lifecycle identities lexicographically by digest. The Hunter Room
must not present this as chronological history, profitability ranking, or a
"latest trades" feed.

## Boundary

This is a read-only presentation milestone over already-persisted controlled
paper results. It does not invoke prepare, run, persistence, providers,
discovery, wallet/signing, DEX execution, settlement, or live/economic trading.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
