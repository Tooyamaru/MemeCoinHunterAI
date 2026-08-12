from dataclasses import FrozenInstanceError
from datetime import datetime, timezone, timedelta
from types import MappingProxyType

import pytest

from core.signals.signal_evidence import (
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)
from core.signals.signal_normalization import normalize_signal_evidence
from core.signals.signal_quality import (
    SignalEvidenceQualityResult,
    SignalQualityStatus,
    assess_signal_evidence_quality,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _evidence(
    *,
    source_id: str = "signal-source",
    evidence_reference: str = "evidence-1",
    signal_status: str = "observed",
    confidence: float = 0.75,
    observed_at: datetime = OBSERVED_AT,
    metadata: dict | None = None,
) -> SignalEvidence:
    return SignalEvidence(
        chain_id="solana",
        token_identity="mint-A",
        signal_type="momentum",
        signal_status=signal_status,
        observed_at=observed_at,
        source_id=source_id,
        evidence_reference=evidence_reference,
        reason_codes=("MOMENTUM_OBSERVED",),
        confidence=confidence,
        provenance=SignalProvenance(
            source_id=source_id,
            method="bounded-market-observation",
            observed_at=observed_at,
            metadata=metadata or {"source": "fixture"},
        ),
    )


def _quality(*items: SignalEvidence):
    source = SignalEvidenceCollection.from_evidence(list(items))
    return assess_signal_evidence_quality(normalize_signal_evidence(source))


def test_valid_normalized_evidence_is_acceptable():
    result = _quality(_evidence())

    assert result.quality_status is SignalQualityStatus.ACCEPTABLE
    assert result.acceptable is True
    assert result.reason_codes == ()


def test_empty_collection_is_insufficient_and_fails_closed():
    source = SignalEvidenceCollection(
        chain_id="solana",
        token_identity="mint-A",
        evidence=(),
    )

    result = assess_signal_evidence_quality(normalize_signal_evidence(source))

    assert result.quality_status is SignalQualityStatus.INSUFFICIENT
    assert result.acceptable is False
    assert result.reason_codes == ("NO_EVIDENCE",)
    assert result.evidence_references == ()


def test_invalid_required_field_fails_closed():
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence([_evidence()])
    )
    object.__setattr__(normalized.evidence[0], "signal_type", "")

    result = assess_signal_evidence_quality(normalized)

    assert result.quality_status is SignalQualityStatus.INVALID
    assert result.acceptable is False
    assert "INVALID_SIGNAL_TYPE" in result.reason_codes


def test_invalid_confidence_fails_closed():
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence([_evidence()])
    )
    object.__setattr__(normalized.evidence[0], "confidence", 1.01)

    result = assess_signal_evidence_quality(normalized)

    assert result.quality_status is SignalQualityStatus.INVALID
    assert result.acceptable is False
    assert result.reason_codes == ("INVALID_CONFIDENCE",)


def test_invalid_timestamp_fails_closed():
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence([_evidence()])
    )
    object.__setattr__(
        normalized.evidence[0],
        "observed_at",
        datetime(2026, 8, 12, 12, 0),
    )

    result = assess_signal_evidence_quality(normalized)

    assert result.quality_status is SignalQualityStatus.INVALID
    assert result.acceptable is False
    assert "INVALID_TIMESTAMP" in result.reason_codes


def test_provenance_source_reference_and_duplicates_are_preserved():
    first = _evidence(source_id="source-a", evidence_reference="duplicate")
    second = _evidence(source_id="source-b", evidence_reference="duplicate")

    result = _quality(first, second)

    assert result.evidence_references == ("duplicate", "duplicate")
    assert tuple(item.source_id for item in result.provenance) == (
        "source-a",
        "source-b",
    )
    assert result.provenance[0].method == "bounded-market-observation"
    assert result.observation_timestamps == (OBSERVED_AT, OBSERVED_AT)


def test_reason_codes_are_deterministic():
    first = _evidence()
    second = _evidence(source_id="source-b", evidence_reference="second")
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence([first, second])
    )
    object.__setattr__(normalized.evidence[0], "confidence", float("nan"))
    object.__setattr__(normalized.evidence[1], "signal_status", "")

    result = assess_signal_evidence_quality(normalized)

    assert result.reason_codes == (
        "INVALID_CONFIDENCE",
        "INVALID_SIGNAL_STATUS",
    )


def test_quality_result_is_immutable():
    result = _quality(_evidence())

    with pytest.raises(FrozenInstanceError):
        result.acceptable = False
    assert isinstance(result.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        result.canonical_representation["new"] = "value"


def test_repeated_identical_input_has_identical_result_and_digest():
    first = _quality(_evidence(metadata={"z": 1, "a": {"b": 2, "a": 1}}))
    second = _quality(_evidence(metadata={"a": {"a": 1, "b": 2}, "z": 1}))

    assert first == second
    assert first.representation_digest == second.representation_digest


def test_quality_result_requires_consistent_acceptability():
    with pytest.raises(ValueError):
        SignalEvidenceQualityResult(
            chain_id="solana",
            token_identity="mint-A",
            quality_status=SignalQualityStatus.ACCEPTABLE,
            acceptable=False,
            reason_codes=(),
            evidence_references=(),
            provenance=(),
            observation_timestamps=(),
            normalized_evidence_digest="digest",
        )