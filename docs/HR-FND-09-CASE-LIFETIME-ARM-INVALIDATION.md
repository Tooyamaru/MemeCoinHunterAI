# HR-FND-09 — Case Lifetime Visibility and Armed-State Invalidation

Status: IMPLEMENTATION / CONTROLLED PAPER ONLY

## Purpose

Make the process-local case lifetime visible in Hunter Room and ensure a
two-step armed mutation cannot survive a server-observed case state change.

## Behavior

- Case review now exposes the exact server `created_at` and `expires_at` values;
- the existing server `source_label` is shown as provenance context;
- an armed run/persist action is bound to both the exact case digest and the
  exact reviewed case state;
- a manual refresh that returns a different digest or state clears the arm;
- successful run/persist and manual cancel also clear digest/state arm data.

No browser countdown or client-side expiry verdict is introduced. The server
registry remains authoritative for expiry and case availability.

## Boundary

This is presentation and stale-action invalidation only. It does not change
registry TTL, refresh cases automatically, retry requests, invoke providers,
or add autonomous discovery, worker/scheduler, wallet/signing, DEX routing,
settlement, live trading, or economic authority.

G2 remains BLOCKED / UNRESOLVED / NOT AUTHORIZED. G3/G4/P09 remain NOT
AUTHORIZED.
