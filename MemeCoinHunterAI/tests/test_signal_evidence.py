from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from core.signals.signal_evidence import (
    P04_T01_CONTRACT_VERSION,
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _evidence(
    *,
    signal_type: str = "momentum",
    signal_status: str = "observed",
    source_id: str = "signal-source",
    evidence_reference: str = "evidence-1",
    confidence: float = 0.75,
    observed_at: datetime = OBSERVED_AT,
    reason_codes: tuple[str, ...] = ("MOMENTUM_OBSERVED",),
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
        reason_codes=reason_codes,
        confidence=confidence,
        provenance=SignalProvenance(
            source_id=source_id,
            method="bounded-market-observation",
            observed_at=observed_at,
            metadata=metadata or {"source": "fixture"},
        ),
    )


def test_signal_evidence_is_immutable_and_provenance_is_frozen():
    evidence = _evidence(metadata={"nested": {"stable": True}})

    with pytest.raises(FrozenInstanceError):
        evidence.signal_status = "changed"
    assert isinstance(evidence.provenance.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        evidence.provenance.metadata["new"] = "value"


def test_collection_is_immutable_and_canonically_ordered():
    first = _evidence(signal_type="trend", evidence_reference="z-reference")
    second = _evidence(signal_type="momentum", evidence_reference="a-reference")
    collection = SignalEvidenceCollection.from_evidence([first, second])

    assert tuple(item.signal_type for item in collection.evidence) == (
        "momentum",
        "trend",
    )
    with pytest.raises(FrozenInstanceError):
        collection.evidence = ()


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan"), float("inf"), True])
def test_confidence_must_be_bounded_and_finite(confidence):
    with pytest.raises(ValueError):
        _evidence(confidence=confidence)


def test_confidence_boundaries_are_accepted():
    assert _evidence(confidence=0).confidence == 0.0
    assert _evidence(confidence=1).confidence == 1.0


def test_timestamps_must_be_timezone_aware():
    with pytest.raises(ValueError):
        _evidence(observed_at=datetime(2026, 8, 12, 12, 0))

    offset = timezone(timedelta(hours=-4))
    evidence = _evidence(
        observed_at=datetime(2026, 8, 12, 8, 0, tzinfo=offset)
    )
    assert evidence.observed_at == datetime(2026, 8, 12, 8, 0, tzinfo=offset)


def test_duplicate_evidence_references_are_preserved():
    first = _evidence(evidence_reference="duplicate", source_id="source-a")
    second = _evidence(evidence_reference="duplicate", source_id="source-b")
    collection = SignalEvidenceCollection.from_evidence([first, second])

    assert tuple(item.evidence_reference for item in collection.evidence) == (
        "duplicate",
        "duplicate",
    )
    assert tuple(item.source_id for item in collection.evidence) == (
        "source-a",
        "source-b",
    )


def test_empty_collection_is_supported():
    collection = SignalEvidenceCollection(
        chain_id="solana",
        token_identity="mint-A",
        evidence=(),
    )

    assert collection.evidence == ()
    assert collection.contract_version == P04_T01_CONTRACT_VERSION


def test_equivalent_evidence_has_stable_representation_digest():
    left = _evidence(metadata={"z": 1, "a": {"b": 2, "a": 1}})
    right = _evidence(metadata={"a": {"a": 1, "b": 2}, "z": 1})

    assert left == right
    assert left.representation_digest == right.representation_digest


def test_reordered_collection_has_stable_representation_digest():
    first = _evidence(signal_type="trend", evidence_reference="trend")
    second = _evidence(signal_type="momentum", evidence_reference="momentum")
    left = SignalEvidenceCollection.from_evidence([first, second])
    right = SignalEvidenceCollection.from_evidence([second, first])

    assert left.evidence == right.evidence
    assert left.representation_digest == right.representation_digest


def test_reason_codes_are_deterministically_normalized():
    evidence = _evidence(reason_codes=("z", "a", "z"))

    assert evidence.reason_codes == ("a", "z")


def test_provenance_must_match_signal_identity_and_timestamp():
    with pytest.raises(ValueError):
        SignalEvidence(
            chain_id="solana",
            token_identity="mint-A",
            signal_type="trend",
            signal_status="observed",
            observed_at=OBSERVED_AT,
            source_id="signal-source",
            evidence_reference="evidence-1",
            reason_codes=("OBSERVED",),
            confidence=0.5,
            provenance=SignalProvenance(
                source_id="other-source",
                method="fixture",
                observed_at=OBSERVED_AT,
            ),
        )


def test_collection_rejects_evidence_for_another_token():
    other = SignalEvidence(
        chain_id="solana",
        token_identity="mint-B",
        signal_type="trend",
        signal_status="observed",
        observed_at=OBSERVED_AT,
        source_id="signal-source",
        evidence_reference="evidence-1",
        reason_codes=("OBSERVED",),
        confidence=0.5,
        provenance=SignalProvenance(
            source_id="signal-source",
            method="fixture",
            observed_at=OBSERVED_AT,
        ),
    )

    with pytest.raises(ValueError):
        SignalEvidenceCollection(
            chain_id="solana",
            token_identity="mint-A",
            evidence=(other,),
        )
