---
name: Validation wrapper assertions
description: Durable testing guidance for layered immutable-contract validation.
---

When a boundary revalidates an upstream immutable object, constructor failures
may be deliberately normalized into a boundary-level validation error. Tests
should assert the fail-closed exception and relevant behavior rather than rely
on the upstream constructor's exact internal message.

**Why:** Layered P08 validation preserves ownership while intentionally hiding
implementation-specific upstream error details.

**How to apply:** Prefer stable error categories or contract behavior in focused
tests; only match exact messages when the message itself is part of the contract.