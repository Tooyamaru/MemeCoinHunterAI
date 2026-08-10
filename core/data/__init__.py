"""Provider-neutral data contracts for the P02 ingestion boundary."""

from core.data.contracts import (
    DataQuality,
    FreshnessPolicy,
    NormalizationContext,
    NormalizationResult,
    NormalizedMarketState,
    OrderingStatus,
    ProviderNeutralAdapter,
    RawEvent,
    SourceHealth,
    SourceHealthStatus,
    canonical_identity,
    normalize_raw_event,
    validate_raw_event,
)

__all__ = [
    "DataQuality",
    "FreshnessPolicy",
    "NormalizationContext",
    "NormalizationResult",
    "NormalizedMarketState",
    "OrderingStatus",
    "ProviderNeutralAdapter",
    "RawEvent",
    "SourceHealth",
    "SourceHealthStatus",
    "canonical_identity",
    "normalize_raw_event",
    "validate_raw_event",
]