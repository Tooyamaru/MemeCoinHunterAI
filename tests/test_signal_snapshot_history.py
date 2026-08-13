from datetime import datetime, timezone

from core.signals.signal_aggregation import aggregate_signal_evidence
from core.signals.signal_evaluation import evaluate_signal_evidence
from core.signals.signal_evidence import (
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)
from core.signals.signal_normalization import normalize_signal_evidence
from core.signals.signal_quality import assess_signal_evidence_quality
from core.signals.signal_snapshot import snapshot_signal_evidence
from core.signals.signal_snapshot_history import (
    P04_T07_CONTRACT_VERSION,
    SignalEvidenceSnapshotHistory,
    SignalSnapshotHistoryOutcome,
)


UTC = timezone.utc
FIRST_TIME = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
SECOND_TIME = datetime(2026, 8, 12, 13, 0, tzinfo=UTC)


def _evidence(
    *,
    evidence_reference: str,
    observed_at: datetime,
    signal_type: str,
) -> SignalEvidence:
    return SignalEvidence(
        chain_id="solana",
        token_identity="mint-A",
        signal_type=signal_type,
        signal_status="observed",
        observed_at=observed_at,
        source_id="signal-source",
        evidence_reference=evidence_reference,
        reason_codes=("OBSERVED",),
        confidence=0.75,
        provenance=SignalProvenance(
            source_id="signal-source",
            method="bounded-market-observation",
            observed_at=observed_at,
            metadata={"fixture": "history"},
        ),
    )


def _snapshot(
    *,
    evidence_reference: str,
    observed_at: datetime,
    signal_type: str,
):
    evidence = SignalEvidenceCollection.from_evidence(
        [
            _evidence(
                evidence_reference=evidence_reference,
                observed_at=observed_at,
                signal_type=signal_type,
            )
        ]
    )
    normalized = normalize_signal_evidence(evidence)
    quality = assess_signal_evidence_quality(normalized)
    evaluation = evaluate_signal_evidence(normalized, quality)
    aggregation = aggregate_signal_evidence(evaluation)
    return snapshot_signal_evidence(aggregation)


def test_history_stores_valid_snapshot_and_preserves_identity() -> None:
    snapshot = _snapshot(
        evidence_reference="first",
        observed_at=FIRST_TIME,
        signal_type="momentum",
    )
    history = SignalEvidenceSnapshotHistory()

    result = history.append(snapshot)

    assert result.outcome is SignalSnapshotHistoryOutcome.STORED
    assert result.accepted is True
    assert result.snapshot is snapshot
    assert history.retrieve() == (snapshot,)
    assert history.retrieve()[0] is snapshot
    assert history.snapshot_count == 1
    assert history.representation_digest == result.history_digest
    assert P04_T07_CONTRACT_VERSION == "p04-t07-v1"


def test_history_retrieval_is_canonical_and_independent_of_insertion_order() -> None:
    first = _snapshot(
        evidence_reference="first",
        observed_at=FIRST_TIME,
        signal_type="momentum",
    )
    second = _snapshot(
        evidence_reference="second",
        observed_at=SECOND_TIME,
        signal_type="trend",
    )

    left = SignalEvidenceSnapshotHistory()
    left.append(second)
    left.append(first)
    right = SignalEvidenceSnapshotHistory()
    right.append(first)
    right.append(second)

    assert left.retrieve() == right.retrieve()
    assert tuple(item.digest for item in left.retrieve()) == tuple(
        sorted((first.digest, second.digest))
    )
    assert left.representation_digest == right.representation_digest


def test_history_accepts_multiple_snapshots_and_deduplicates_by_digest() -> None:
    snapshot = _snapshot(
        evidence_reference="same",
        observed_at=FIRST_TIME,
        signal_type="momentum",
    )
    other = _snapshot(
        evidence_reference="other",
        observed_at=SECOND_TIME,
        signal_type="trend",
    )
    history = SignalEvidenceSnapshotHistory()

    first = history.append(snapshot)
    duplicate = history.append(snapshot)
    second = history.append(other)

    assert first.outcome is SignalSnapshotHistoryOutcome.STORED
    assert duplicate.outcome is SignalSnapshotHistoryOutcome.DUPLICATE
    assert duplicate.duplicate is True
    assert duplicate.snapshot is snapshot
    assert second.outcome is SignalSnapshotHistoryOutcome.STORED
    assert history.snapshot_count == 2
    assert {item.digest for item in history.retrieve()} == {
        snapshot.digest,
        other.digest,
    }


def test_history_rejects_invalid_input_without_mutating_state() -> None:
    snapshot = _snapshot(
        evidence_reference="valid",
        observed_at=FIRST_TIME,
        signal_type="momentum",
    )
    history = SignalEvidenceSnapshotHistory([snapshot])
    before = history.retrieve()
    before_digest = history.digest

    result = history.append(object())

    assert result.outcome is SignalSnapshotHistoryOutcome.INVALID_INPUT
    assert result.accepted is False
    assert result.snapshot is None
    assert result.reason_codes == ("INVALID_SNAPSHOT",)
    assert history.retrieve() == before
    assert history.digest == before_digest


def test_history_rejects_tampered_snapshot_without_mutating_supplied_value() -> None:
    snapshot = _snapshot(
        evidence_reference="tampered",
        observed_at=FIRST_TIME,
        signal_type="momentum",
    )
    original_digest = snapshot.digest
    object.__setattr__(snapshot, "contract_version", "")
    history = SignalEvidenceSnapshotHistory()

    result = history.append(snapshot)

    assert result.outcome is SignalSnapshotHistoryOutcome.INVALID_INPUT
    assert result.snapshot is None
    assert history.retrieve() == ()
    assert snapshot.contract_version == ""
    assert snapshot.digest != original_digest


def test_empty_history_is_deterministic_and_immutable() -> None:
    left = SignalEvidenceSnapshotHistory()
    right = SignalEvidenceSnapshotHistory.from_snapshots([])

    assert left.retrieve() == ()
    assert left.history == ()
    assert left.snapshot_count == 0
    assert left.digest == right.digest
    assert isinstance(left.retrieve(), tuple)


def test_history_preserves_snapshot_digest_and_normalized_timestamps() -> None:
    non_utc = datetime.fromisoformat("2026-08-12T08:00:00-04:00")
    snapshot = _snapshot(
        evidence_reference="timestamped",
        observed_at=non_utc,
        signal_type="momentum",
    )
    history = SignalEvidenceSnapshotHistory()

    history.append(snapshot)
    stored = history.retrieve()[0]

    assert stored is snapshot
    assert stored.digest == snapshot.digest
    assert stored.observation_timestamps == (
        datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
    )
    assert stored.provenance[0].observed_at == stored.observation_timestamps[0]


def test_equivalent_inputs_produce_equal_history_results_and_digest() -> None:
    first_left = _snapshot(
        evidence_reference="first",
        observed_at=FIRST_TIME,
        signal_type="momentum",
    )
    second_left = _snapshot(
        evidence_reference="second",
        observed_at=SECOND_TIME,
        signal_type="trend",
    )
    first_right = _snapshot(
        evidence_reference="first",
        observed_at=FIRST_TIME,
        signal_type="momentum",
    )
    second_right = _snapshot(
        evidence_reference="second",
        observed_at=SECOND_TIME,
        signal_type="trend",
    )

    left = SignalEvidenceSnapshotHistory([first_left, second_left])
    right = SignalEvidenceSnapshotHistory([second_right, first_right])

    assert left.retrieve() == right.retrieve()
    assert left.digest == right.digest
    assert left.snapshot_count == right.snapshot_count == 2
