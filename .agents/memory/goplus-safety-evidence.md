---
name: GoPlus safety evidence
description: Durable boundary for using GoPlus Token Security responses as P03 evidence.
---

GoPlus Token Security responses may supply explicit risk flags, but the documented response does not provide a source observation timestamp. Treat explicit risk flags as fail-closed evidence; do not turn favorable, missing, or unsupported fields into PASS evidence.

**Why:** Receipt time and adapter evaluation time describe when the application received or evaluated the response, not when GoPlus observed the token state. Using either as source time would overstate freshness and weaken the existing UNKNOWN semantics.

**How to apply:** Keep the adapter bounded to validated identities and the existing P03 evaluator. Preserve `UNKNOWN`/unavailable limitations, and verify any future live provider behavior separately from browser credentials or frontend requests.