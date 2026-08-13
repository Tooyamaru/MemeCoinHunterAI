from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from types import MappingProxyType

import pytest

from core.signals.signal_aggregation import aggregate_signal_evidence
from core.signals.signal_aggregation import SignalAggregationStatus
from core.signals.signal_evaluation import evaluate_signal_evidence
from core.signals.signal_evidence import (
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)
from core.signals.signal_normalization import normalize_signal_evidence
from core.signals.signal_quality import assess_signal_evidence_quality
from core.signals.signal_snapshot import (
    P04_T06_CONTRACT_VERSION,
    SignalSnapshotStatus,
    SignalEvidenceSnapshot,
    SignalEvidenceSnapshotCollection,
    create_signal_evidence_snapshot,
    snapshot_signal_evidence_result,
    snapshot_signal_evidence,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _evidence(
    *,
    source_id: str = "signal-source",
    evidence_reference: str = "evidence-1",
    signal_type: str = "momentum",
    signal_status: str = "observed",
    observed_at: datetime = OBSERVED_AT,
    metadata: dict | None = None,
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
            metadata=metadata or {"source": "fixture"},
        ),
    )


def _aggregation(*items: SignalEvidence):
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection(
            chain_id="solana",
            token_identity="mint-A",
            evidence=tuple(items),
        )
    )
    quality = assess_signal_evidence_quality(normalized)
    evaluation = evaluate_signal_evidence(normalized, quality)
    return aggregate_signal_evidence(evaluation)


def _snapshot_kwargs(result):
    return {
        "chain_id": result.chain_id,
        "token_identity": result.token_identity,
        "aggregation_status": result.aggregation_status,
        "aggregated": result.aggregated,
        "evaluation_status": result.evaluation_status,
        "quality_status": result.quality_status,
        "signal_statuses": result.signal_statuses,
        "reason_codes": result.reason_codes,
        "evidence_references": result.evidence_references,
        "provenance": result.provenance,
        "observation_timestamps": result.observation_timestamps,
        "normalized_evidence_digest": result.normalized_evidence_digest,
        "evaluation_digest": result.evaluation_digest,
        "aggregation_digest": result.representation_digest,
        "aggregation_contract_version": result.contract_version,
    }


def test_snapshot_preserves_the_evidence_chain():
    result = _aggregation(
        _evidence(source_id="source-a", evidence_reference="first"),
        _evidence(
            source_id="source-b",
            evidence_reference="second",
            signal_type="trend",
            signal_status="confirmed",
            observed_at=datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
        ),
    )

    snapshot = snapshot_signal_evidence(result)

    assert snapshot.chain_id == "solana"
    assert snapshot.token_identity == "mint-A"
    assert snapshot.evidence_references == ("first", "second")
    assert snapshot.signal_statuses == ("observed", "confirmed")
    assert snapshot.reason_codes == result.reason_codes
    assert snapshot.provenance == result.provenance
    assert snapshot.observation_timestamps == (
        OBSERVED_AT,
        datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
    )
    assert snapshot.quality_status is result.quality_status
    assert snapshot.evaluation_status is result.evaluation_status
    assert snapshot.normalized_evidence_digest == result.normalized_evidence_digest
    assert snapshot.aggregation_digest == result.representation_digest
    assert snapshot.aggregation_contract_version == result.contract_version
    assert snapshot.contract_version == P04_T06_CONTRACT_VERSION


def test_snapshot_and_nested_representation_are_immutable():
    snapshot = snapshot_signal_evidence(_aggregation(_evidence()))

    with pytest.raises(FrozenInstanceError):
        snapshot.aggregated = False
    with pytest.raises(TypeError):
        snapshot.canonical_representation["new"] = "value"
    assert isinstance(snapshot.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        snapshot.canonical_representation["provenance"][0]["metadata"]["new"] = 1


def test_snapshot_factory_alias_is_deterministic():
    first = snapshot_signal_evidence(_aggregation(_evidence()))
    second = create_signal_evidence_snapshot(_aggregation(_evidence()))

    assert first == second
    assert first.canonical_representation == second.canonical_representation
    assert first.representation_digest == second.representation_digest
    assert first.digest == first.representation_digest


def test_collection_is_immutable_and_deterministically_ordered():
    first = snapshot_signal_evidence(
        _aggregation(_evidence(evidence_reference="first"))
    )
    second = snapshot_signal_evidence(
        _aggregation(
            _evidence(
                evidence_reference="second",
                signal_type="trend",
            )
        )
    )

    left = SignalEvidenceSnapshotCollection.from_snapshots([second, first])
    right = SignalEvidenceSnapshotCollection.from_snapshots([first, second])

    assert left == right
    assert left.snapshots == right.snapshots
    with pytest.raises(FrozenInstanceError):
        left.snapshots = ()
    with pytest.raises(TypeError):
        left.canonical_representation["new"] = "value"


def test_duplicate_records_are_preserved_without_deduplication():
    snapshot = snapshot_signal_evidence(
        _aggregation(
            _evidence(source_id="source-a", evidence_reference="duplicate"),
            _evidence(source_id="source-b", evidence_reference="duplicate"),
        )
    )

    assert snapshot.evidence_references == ("duplicate", "duplicate")
    assert tuple(item.source_id for item in snapshot.provenance) == (
        "source-a",
        "source-b",
    )
    collection = SignalEvidenceSnapshotCollection.from_snapshots(
        [snapshot, snapshot]
    )
    assert collection.snapshot_count == 2
    assert collection.snapshots == (snapshot, snapshot)


def test_empty_snapshot_collection_is_deterministic():
    collection = SignalEvidenceSnapshotCollection.from_snapshots([])

    assert collection.snapshots == ()
    assert collection.snapshot_count == 0
    assert collection.canonical_representation["snapshots"] == ()
    assert collection.representation_digest == (
        SignalEvidenceSnapshotCollection.from_snapshots([]).representation_digest
    )


def test_digest_changes_when_semantic_content_changes():
    first = snapshot_signal_evidence(
        _aggregation(_evidence(evidence_reference="first"))
    )
    second = snapshot_signal_evidence(
        _aggregation(_evidence(evidence_reference="changed"))
    )

    assert first.representation_digest != second.representation_digest


def test_dictionary_insertion_order_does_not_change_digest():
    first = snapshot_signal_evidence(
        _aggregation(_evidence(metadata={"z": 1, "a": {"b": 2, "a": 1}}))
    )
    second = snapshot_signal_evidence(
        _aggregation(_evidence(metadata={"a": {"a": 1, "b": 2}, "z": 1}))
    )

    assert first.canonical_representation == second.canonical_representation
    assert first.representation_digest == second.representation_digest


def test_snapshot_requires_timezone_aware_observation_timestamps():
    result = _aggregation(_evidence())
    with pytest.raises(ValueError, match="timezone-aware"):
        type(snapshot_signal_evidence(result))(
            chain_id=result.chain_id,
            token_identity=result.token_identity,
            aggregation_status=result.aggregation_status,
            aggregated=result.aggregated,
            evaluation_status=result.evaluation_status,
            quality_status=result.quality_status,
            signal_statuses=result.signal_statuses,
            reason_codes=result.reason_codes,
            evidence_references=result.evidence_references,
            provenance=result.provenance,
            observation_timestamps=(datetime(2026, 8, 12, 12, 0),),
            normalized_evidence_digest=result.normalized_evidence_digest,
            evaluation_digest=result.evaluation_digest,
            aggregation_digest=result.representation_digest,
            aggregation_contract_version=result.contract_version,
        )


def test_snapshot_does_not_add_a_current_time():
    snapshot = snapshot_signal_evidence(_aggregation(_evidence()))

    assert snapshot.observation_timestamps == (OBSERVED_AT,)
    assert not hasattr(snapshot, "snapshot_at")
    assert not hasattr(snapshot, "created_at")


def test_valid_snapshot_result_preserves_upstream_context():
    aggregation = _aggregation(_evidence())

    result = snapshot_signal_evidence_result(aggregation)

    assert result.status is SignalSnapshotStatus.SNAPSHOTTED
    assert result.valid is True
    assert result.snapshot is not None
    assert result.upstream_aggregation_status is aggregation.aggregation_status
    assert result.upstream_evaluation_status is aggregation.evaluation_status
    assert result.upstream_quality_status is aggregation.quality_status
    assert result.aggregation_digest == aggregation.representation_digest


def test_invalid_snapshot_input_fails_closed():
    result = snapshot_signal_evidence_result(object())

    assert result.status is SignalSnapshotStatus.INVALID_INPUT
    assert result.snapshotted is False
    assert result.snapshot is None
    assert result.reason_codes == ("INVALID_AGGREGATION_RESULT",)
    assert result.canonical_representation["snapshot"] is None


def test_empty_snapshot_input_fails_closed():
    result = snapshot_signal_evidence_result(_aggregation())

    assert result.status is SignalSnapshotStatus.EMPTY_INPUT
    assert result.valid is False
    assert result.snapshot is None
    assert result.reason_codes == ("NO_EVIDENCE",)
    assert result.upstream_aggregation_status.value == "EMPTY_INPUT"


def test_blocked_upstream_evaluation_fails_closed():
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence([_evidence()])
    )
    object.__setattr__(normalized.evidence[0], "confidence", 1.5)
    quality = assess_signal_evidence_quality(normalized)
    evaluation = evaluate_signal_evidence(normalized, quality)
    aggregation = aggregate_signal_evidence(evaluation)

    result = snapshot_signal_evidence_result(aggregation)

    assert result.status is SignalSnapshotStatus.UPSTREAM_BLOCKED
    assert result.snapshot is None
    assert result.reason_codes == ("INVALID_CONFIDENCE",)
    assert result.upstream_evaluation_status.value == "QUALITY_BLOCKED"


def test_snapshot_result_is_immutable_and_deterministic():
    first = snapshot_signal_evidence_result(_aggregation(_evidence()))
    second = snapshot_signal_evidence_result(_aggregation(_evidence()))

    assert first == second
    assert first.representation_digest == second.representation_digest
    with pytest.raises(FrozenInstanceError):
        first.snapshotted = False
    with pytest.raises(TypeError):
        first.canonical_representation["new"] = "value"


def test_snapshot_creation_does_not_mutate_upstream_aggregation():
    aggregation = _aggregation(_evidence(metadata={"source": "fixture"}))
    before = aggregation.canonical_representation

    result = snapshot_signal_evidence_result(aggregation)

    assert result.snapshot is not None
    assert aggregation.canonical_representation == before


def test_direct_snapshot_construction_fails_closed_for_empty_input():
    aggregation = _aggregation()

    with pytest.raises(ValueError, match="EMPTY_INPUT"):
        SignalEvidenceSnapshot.from_aggregation(aggregation)

    with pytest.raises(ValueError, match="EMPTY_INPUT"):
        SignalEvidenceSnapshotCollection.from_aggregations([aggregation])


def test_direct_snapshot_construction_fails_closed_for_blocked_input():
    normalized = normalize_signal_evidence(
        SignalEvidenceCollection.from_evidence([_evidence()])
    )
    object.__setattr__(normalized.evidence[0], "confidence", 1.5)
    aggregation = aggregate_signal_evidence(
        evaluate_signal_evidence(
            normalized,
            assess_signal_evidence_quality(normalized),
        )
    )

    with pytest.raises(ValueError, match="UPSTREAM_BLOCKED"):
        SignalEvidenceSnapshot.from_aggregation(aggregation)

    with pytest.raises(ValueError, match="UPSTREAM_BLOCKED"):
        SignalEvidenceSnapshotCollection.from_aggregations([aggregation])


def test_direct_snapshot_construction_fails_closed_for_insufficient_input():
    aggregation = replace(
        _aggregation(_evidence()),
        signal_statuses=(),
        evidence_references=(),
        provenance=(),
        observation_timestamps=(),
    )

    with pytest.raises(ValueError, match="INSUFFICIENT_INPUT"):
        SignalEvidenceSnapshot.from_aggregation(aggregation)

    with pytest.raises(ValueError, match="INSUFFICIENT_INPUT"):
        SignalEvidenceSnapshotCollection.from_aggregations([aggregation])


def test_direct_snapshot_construction_fails_closed_for_invalid_input():
    with pytest.raises(ValueError, match="INVALID_AGGREGATION_RESULT"):
        SignalEvidenceSnapshot.from_aggregation(object())

    with pytest.raises(ValueError, match="INVALID_AGGREGATION_RESULT"):
        SignalEvidenceSnapshotCollection.from_aggregations([object()])


def test_direct_snapshot_construction_rejects_empty_evidence():
    result = _aggregation(_evidence())
    kwargs = _snapshot_kwargs(result)
    kwargs.update(
        signal_statuses=(),
        evidence_references=(),
        provenance=(),
        observation_timestamps=(),
    )

    with pytest.raises(ValueError, match="evidence"):
        SignalEvidenceSnapshot(**kwargs)


def test_direct_snapshot_construction_rejects_missing_evaluation_status():
    result = _aggregation(_evidence())
    kwargs = _snapshot_kwargs(result)
    kwargs["evaluation_status"] = None

    with pytest.raises(ValueError, match="EVALUATED"):
        SignalEvidenceSnapshot(**kwargs)


@pytest.mark.parametrize(
    "evaluation_status",
    (
        "QUALITY_BLOCKED",
        "INVALID_INPUT",
    ),
)
def test_direct_snapshot_construction_rejects_blocked_or_invalid_evaluation(
    evaluation_status,
):
    result = _aggregation(_evidence())
    kwargs = _snapshot_kwargs(result)
    kwargs["evaluation_status"] = evaluation_status

    with pytest.raises(ValueError, match="EVALUATED"):
        SignalEvidenceSnapshot(**kwargs)


def test_snapshot_collection_rejects_malformed_snapshot():
    malformed = snapshot_signal_evidence(_aggregation(_evidence()))
    object.__setattr__(malformed, "evidence_references", ())

    with pytest.raises(ValueError, match="without evidence"):
        SignalEvidenceSnapshotCollection.from_snapshots([malformed])


def test_snapshot_from_aggregation_snapshot_alias_preserves_valid_behavior():
    aggregation = _aggregation(_evidence())

    snapshot = SignalEvidenceSnapshot.from_aggregation_snapshot(aggregation)

    assert snapshot == SignalEvidenceSnapshot.from_aggregation(aggregation)
    assert aggregation.aggregation_status is SignalAggregationStatus.AGGREGATED
