from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from types import MappingProxyType

import pytest

from core.signals.signal_evidence import (
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)
from core.signals.signal_evaluation import (
    SignalEvaluationStatus,
    evaluate_signal_evidence,
)
from core.signals.signal_normalization import normalize_signal_evidence
from core.signals.signal_quality import (
    SignalQualityStatus,
    assess_signal_evidence_quality,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _evidence(
    *,
    source_id: str = "signal-source",
    evidence_reference: str = "evidence-1",
    signal_type: str = "momentum",
    signal_status: str = "observed",
) -> SignalEvidence:
    return SignalEvidence(
        chain_id="solana",
        token_identity="mint-A",
        signal_type=signal_type,
        signal_status=signal_status,
        observed_at=OBSERVED_AT,
        source_id=source_id,
        evidence_reference=evidence_reference,
        reason_codes=("MOMENTUM_OBSERVED",),
        confidence=0.75,
        provenance=SignalProvenance(
            source_id=source_id,
            method="bounded-market-observation",
            observed_at=OBSERVED_AT,
            metadata={"source": "fixture"},
        ),
    )


def _normalized(*items: SignalEvidence):
    if not items:
        return normalize_signal_evidence(
            SignalEvidenceCollection(
                chain_id="solana",
                token_identity="mint-A",
                evidence=(),
            )
        )
    return normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence(list(items))
    )


def _evaluated(*items: SignalEvidence):
    normalized = _normalized(*items)
    quality = assess_signal_evidence_quality(normalized)
    return normalized, quality, evaluate_signal_evidence(normalized, quality)


def test_valid_acceptable_evidence_is_evaluated():
    normalized, quality, result = _evaluated(_evidence())

    assert quality.quality_status is SignalQualityStatus.ACCEPTABLE
    assert result.evaluation_status is SignalEvaluationStatus.EVALUATED
    assert result.evaluated is True
    assert result.signal_statuses == ("observed",)
    assert result.normalized_evidence_digest == normalized.representation_digest


def test_insufficient_quality_fails_closed():
    normalized = _normalized()
    quality = assess_signal_evidence_quality(normalized)

    result = evaluate_signal_evidence(normalized, quality)

    assert quality.quality_status is SignalQualityStatus.INSUFFICIENT
    assert result.evaluation_status is SignalEvaluationStatus.QUALITY_BLOCKED
    assert result.evaluated is False
    assert result.reason_codes == ("NO_EVIDENCE",)


def test_invalid_quality_fails_closed():
    normalized = _normalized(_evidence())
    object.__setattr__(normalized.evidence[0], "confidence", 1.5)
    quality = assess_signal_evidence_quality(normalized)

    result = evaluate_signal_evidence(normalized, quality)

    assert quality.quality_status is SignalQualityStatus.INVALID
    assert result.evaluation_status is SignalEvaluationStatus.QUALITY_BLOCKED
    assert result.evaluated is False
    assert result.reason_codes == ("INVALID_CONFIDENCE",)


def test_repeated_evaluation_is_deterministic():
    normalized, quality, first = _evaluated(_evidence())
    second = evaluate_signal_evidence(normalized, quality)

    assert first == second
    assert first.representation_digest == second.representation_digest


def test_input_order_does_not_change_evaluation():
    first = _evidence(signal_type="trend", evidence_reference="trend")
    second = _evidence(signal_type="momentum", evidence_reference="momentum")

    left = _evaluated(first, second)[2]
    right = _evaluated(second, first)[2]

    assert left == right
    assert left.representation_digest == right.representation_digest


def test_evidence_references_and_duplicates_are_preserved():
    _, _, result = _evaluated(
        _evidence(source_id="source-a", evidence_reference="duplicate"),
        _evidence(source_id="source-b", evidence_reference="duplicate"),
    )

    assert result.evidence_references == ("duplicate", "duplicate")


def test_provenance_is_preserved():
    _, _, result = _evaluated(
        _evidence(source_id="source-a", evidence_reference="first")
    )

    assert len(result.provenance) == 1
    assert result.provenance[0].source_id == "source-a"
    assert result.provenance[0].method == "bounded-market-observation"
    assert result.provenance[0].observed_at == OBSERVED_AT


def test_normalized_input_digest_is_preserved():
    normalized, _, result = _evaluated(_evidence())

    assert result.normalized_evidence_digest == normalized.representation_digest


def test_reason_codes_are_deterministic():
    normalized = _normalized(
        _evidence(source_id="source-a", evidence_reference="first"),
        _evidence(source_id="source-b", evidence_reference="second"),
    )
    object.__setattr__(normalized.evidence[0], "confidence", float("nan"))
    object.__setattr__(normalized.evidence[1], "signal_status", "")
    quality = assess_signal_evidence_quality(normalized)

    result = evaluate_signal_evidence(normalized, quality)

    assert result.reason_codes == (
        "INVALID_CONFIDENCE",
        "INVALID_SIGNAL_STATUS",
    )


def test_evaluation_result_is_immutable():
    _, _, result = _evaluated(_evidence())

    with pytest.raises(FrozenInstanceError):
        result.evaluated = False
    assert isinstance(result.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        result.canonical_representation["new"] = "value"


def test_evaluation_uses_observation_time_without_current_time():
    _, _, result = _evaluated(_evidence())

    assert result.observation_timestamps == (OBSERVED_AT,)
    assert not hasattr(result, "evaluated_at")
    assert not hasattr(result, "evaluation_timestamp")


def test_malformed_or_unsupported_input_fails_closed():
    result = evaluate_signal_evidence(object(), object())

    assert result.evaluation_status is SignalEvaluationStatus.INVALID_INPUT
    assert result.evaluated is False
    assert result.reason_codes == ("INVALID_NORMALIZED_EVIDENCE",)