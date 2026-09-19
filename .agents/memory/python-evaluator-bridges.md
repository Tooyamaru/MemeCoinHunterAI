---
name: Python evaluator bridges
description: Boundary rule for invoking canonical Python evaluation from the TypeScript API.
---

When the TypeScript API needs a canonical Python evaluator, use a bounded child
process with stdin/stdout, a timeout, an output cap, and generic fail-closed
errors. Do not duplicate the evaluator policy in TypeScript. Keep an endpoint
that lacks canonical upstream P04/P05 snapshots as an admission diagnostic; it
must not claim to have produced a P05 score.

**Why:** The API holds serialized browser reports while the authoritative
evaluator contracts live in Python, and the opportunity request does not carry
the intermediate P04 snapshots needed for a real P05 evaluation.

**How to apply:** Reuse the bridge pattern for future evaluator-backed API
boundaries, preserving exact identity and source-time limitations while
separating fixture/evaluator verification from live-provider capability.