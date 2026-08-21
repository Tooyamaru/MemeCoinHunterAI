---
name: P06 deterministic timestamps
description: Durable timestamp rule for the P06 DecisionIntent contract.
---

P06 DecisionIntent creation must use an explicitly supplied, timezone-aware
decision timestamp or deterministically derive it from the validated P05-T08
context reference time. It must never read the wall clock.

**Why:** Reproducible intent digests and evidence-first provenance require the
same validated inputs to produce the same output across runs.

**How to apply:** Keep timestamp defaults local and deterministic; require
decision time not to precede the context reference time.