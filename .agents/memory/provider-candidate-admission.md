---
name: Provider candidate admission
description: Boundary decision for provider-backed candidate listings that lack canonical discovery evidence.
---

Provider profile listings without documented source observation time, source event identity, and cursor continuity must remain explicitly unadmitted provider candidates; do not fabricate canonical discovery acceptance.

**Why:** DexScreener's latest token-profiles endpoint documents optional token metadata but not the event and ordering semantics required by the existing discovery contracts.

**How to apply:** Preserve provider order, identity, missing metadata, duplicates, and invalid entries in a bounded listing. Only forward candidates into canonical discovery after a provider adapter supplies and validates the required evidence.