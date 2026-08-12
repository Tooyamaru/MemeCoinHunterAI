from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from types import MappingProxyType

import pytest

from core.signals.signal_aggregation import (
    SignalAggregationStatus,
    aggregate_signal_evidence,
)
from core.signals.signal_evaluation import SignalEvaluationStatus
from core.signals.signal_evidence import (
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)
from core.signals.signal_normalization import normalize_signal_evidence
from core.signals.signal_quality import assess_signal_evidence_quality
from core.signals.signal_evaluation import evaluate_signal_evidence


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _evidence(
    *,
    source_id: str = "signal-source",
    evidence_reference: str = "evidence-1",
    signal_type: str = "momentum",
    signal_status: str = "observed",
    observed_at: datetime = OBSERVED_AT,
) -> SignalEvidence:
    return SignalEvidence(
        chain_id="solana",
        token_identity="mint-A",
        signal_type=signal_type,
        signal_status=signal_status,
        observed_at=observed_at,
        source_id=source_id,
        evidence_reference=evidence_reference,
        reason_codes=("MOMENTUM_OBSERVED",),
        confidence=0.75,
        provenance=SignalProvenance(
            source_id=source_id,
            method="bounded-market-observation",
            observed_at=observed_at,
            metadata={"source": "fixture"},
        ),
    )


def _evaluated(*items: SignalEvidence):
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence(list(items))
    )
    quality = assess_signal_evidence_quality(normalized)
    return evaluate_signal_evidence(normalized, quality)


def _empty_evaluation():
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection(
            chain_id="solana",
            token_identity="mint-A",
            evidence=(),
        )
    )
    quality = assess_signal_evidence_quality(normalized)
    return evaluate_signal_evidence(normalized, quality)


def test_aggregation_preserves_trace_and_is_immutable():
    evaluation = _evaluated(
        _evidence(source_id="source-a", evidence_reference="first"),
        _evidence(source_id="source-b", evidence_reference="second"),
    )

    result = aggregate_signal_evidence(evaluation)

    assert result.aggregation_status is SignalAggregationStatus.AGGREGATED
    assert result.aggregated is True
    assert result.evidence_references == ("first", "second")
    assert result.signal_statuses == ("observed", "observed")
    assert result.provenance[0].source_id == "source-a"
    assert result.observation_timestamps == (OBSERVED_AT, OBSERVED_AT)
    with pytest.raises(FrozenInstanceError):
        result.aggregated = False
    assert isinstance(result.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        result.canonical_representation["new"] = "value"


def test_input_order_does_not_change_aggregate():
    first = _evidence(source_id="source-a", evidence_reference="a")
    second = _evidence(source_id="source-b", evidence_reference="b")

    left = aggregate_signal_evidence(_evaluated(first, second))
    right = aggregate_signal_evidence(_evaluated(second, first))

    assert left == right
    assert left.representation_digest == right.representation_digest


def test_duplicate_evidence_references_are_preserved():
    result = aggregate_signal_evidence(
        _evaluated(
            _evidence(source_id="source-a", evidence_reference="duplicate"),
            _evidence(source_id="source-b", evidence_reference="duplicate"),
        )
    )

    assert result.evidence_references == ("duplicate", "duplicate")
    assert tuple(item.source_id for item in result.provenance) == (
        "source-a",
        "source-b",
    )


def test_provenance_timestamps_and_statuses_are_preserved():
    result = aggregate_signal_evidence(
        _evaluated(
            _evidence(
                source_id="source-a",
                evidence_reference="trend",
                signal_type="trend",
                signal_status="confirmed",
                observed_at=datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
            ),
            _evidence(
                source_id="source-b",
                evidence_reference="momentum",
                signal_type="momentum",
                signal_status="observed",
            ),
        )
    )

    assert result.signal_statuses == ("observed", "confirmed")
    assert tuple(item.method for item in result.provenance) == (
        "bounded-market-observation",
        "bounded-market-observation",
    )
    assert result.observation_timestamps == (
        OBSERVED_AT,
        datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
    )


def test_empty_input_is_explicit_and_fail_closed():
    result = aggregate_signal_evidence(_empty_evaluation())

    assert result.aggregation_status is SignalAggregationStatus.EMPTY_INPUT
    assert result.aggregated is False
    assert result.evidence_count == 0
    assert result.reason_codes == ("NO_EVIDENCE",)


def test_blocked_evaluation_is_not_aggregated():
    result = aggregate_signal_evidence(_empty_evaluation())

    assert result.evaluation_status is SignalEvaluationStatus.QUALITY_BLOCKED
    assert result.quality_status is not None
    assert result.aggregated is False


def test_invalid_or_unsupported_input_fails_closed():
    result = aggregate_signal_evidence(object())

    assert result.aggregation_status is SignalAggregationStatus.INVALID_INPUT
    assert result.aggregated is False
    assert result.reason_codes == ("INVALID_EVALUATION_RESULT",)


def test_stable_canonical_representation_and_digest():
    first = aggregate_signal_evidence(_evaluated(_evidence()))
    second = aggregate_signal_evidence(_evaluated(_evidence()))

    assert first.canonical_representation == second.canonical_representation
    assert first.representation_digest == second.representation_digest
    assert first.evaluation_digest == second.evaluation_digest


def test_aggregation_does_not_introduce_current_time():
    result = aggregate_signal_evidence(_evaluated(_evidence()))

    assert result.observation_timestamps == (OBSERVED_AT,)
    assert not hasattr(result, "aggregated_at")
    assert not hasattr(result, "aggregation_timestamp")