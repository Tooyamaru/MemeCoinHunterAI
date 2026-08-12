from dataclasses import FrozenInstanceError
from datetime import datetime, timezone, timedelta
from types import MappingProxyType

import pytest

from core.signals.signal_evidence import (
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)
from core.signals.signal_normalization import (
    NormalizedSignalEvidence,
    NormalizedSignalEvidenceCollection,
    normalize_signal_evidence,
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
        confidence=confidence,
        provenance=SignalProvenance(
            source_id=source_id,
            method="bounded-market-observation",
            observed_at=observed_at,
            metadata=metadata or {"source": "fixture"},
        ),
    )


def _collection(*evidence: SignalEvidence) -> SignalEvidenceCollection:
    return SignalEvidenceCollection.from_evidence(list(evidence))


def test_basic_normalization_preserves_signal_identity_and_fields():
    original = _evidence()
    normalized = normalize_signal_evidence(_collection(original))
    item = normalized.evidence[0]

    assert item.chain_id == original.chain_id
    assert item.token_identity == original.token_identity
    assert item.signal_type == original.signal_type
    assert item.signal_status == original.signal_status
    assert item.source_id == original.source_id
    assert item.evidence_reference == original.evidence_reference
    assert item.reason_codes == original.reason_codes
    assert item.confidence == original.confidence
    assert item.contract_version == original.contract_version
    assert original.observed_at == OBSERVED_AT
    assert original.provenance.observed_at == OBSERVED_AT


def test_normalization_orders_records_independently_of_input_order():
    first = _evidence(signal_type="trend", evidence_reference="trend")
    second = _evidence(signal_type="momentum", evidence_reference="momentum")

    left = normalize_signal_evidence(_collection(first, second))
    right = normalize_signal_evidence(_collection(second, first))

    assert left.evidence == right.evidence
    assert left.representation_digest == right.representation_digest


def test_duplicate_evidence_records_and_references_are_preserved():
    first = _evidence(evidence_reference="duplicate", source_id="source-a")
    second = _evidence(evidence_reference="duplicate", source_id="source-b")

    normalized = normalize_signal_evidence(_collection(first, second))

    assert len(normalized.evidence) == 2
    assert tuple(item.evidence_reference for item in normalized.evidence) == (
        "duplicate",
        "duplicate",
    )
    assert {item.source_id for item in normalized.evidence} == {
        "source-a",
        "source-b",
    }


def test_equivalent_timestamps_normalize_to_utc():
    offset = timezone(timedelta(hours=-4))
    original = _evidence(
        observed_at=datetime(2026, 8, 12, 8, 0, tzinfo=offset)
    )
    normalized = normalize_signal_evidence(_collection(original)).evidence[0]

    assert normalized.observed_at == OBSERVED_AT
    assert normalized.observed_at.tzinfo is UTC
    assert normalized.provenance.observed_at == OBSERVED_AT
    assert normalized.provenance.observed_at.tzinfo is UTC


def test_naive_timestamps_are_rejected_by_the_normalized_contract():
    with pytest.raises(ValueError):
        NormalizedSignalEvidence(
            chain_id="solana",
            token_identity="mint-A",
            signal_type="momentum",
            signal_status="observed",
            observed_at=datetime(2026, 8, 12, 12, 0),
            source_id="signal-source",
            evidence_reference="evidence-1",
            reason_codes=("MOMENTUM_OBSERVED",),
            confidence=0.75,
            provenance=SignalProvenance(
                source_id="signal-source",
                method="fixture",
                observed_at=OBSERVED_AT,
            ),
            contract_version="p04-t01-v1",
        )


def test_provenance_and_source_reference_are_preserved():
    original = _evidence(metadata={"feed": {"name": "fixture"}})
    normalized = normalize_signal_evidence(_collection(original)).evidence[0]

    assert normalized.provenance.source_id == original.provenance.source_id
    assert normalized.provenance.method == original.provenance.method
    assert normalized.provenance.metadata == original.provenance.metadata
    assert normalized.source_id == original.source_id
    assert normalized.evidence_reference == original.evidence_reference


def test_normalization_outputs_and_representation_are_immutable():
    normalized = normalize_signal_evidence(
        _collection(_evidence(metadata={"nested": {"stable": True}}))
    )

    with pytest.raises(FrozenInstanceError):
        normalized.evidence = ()
    assert isinstance(normalized.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        normalized.canonical_representation["new"] = "value"
    with pytest.raises(TypeError):
        normalized.evidence[0].canonical_representation["new"] = "value"
    with pytest.raises(TypeError):
        normalized.evidence[0].provenance.metadata["new"] = "value"


def test_digest_is_stable_and_changes_for_semantic_evidence_changes():
    original = normalize_signal_evidence(_collection(_evidence()))
    repeated = normalize_signal_evidence(_collection(_evidence()))
    changed = normalize_signal_evidence(
        _collection(_evidence(signal_status="changed"))
    )

    assert original.representation_digest == repeated.representation_digest
    assert original.representation_digest != changed.representation_digest


def test_empty_collection_normalizes_to_empty_immutable_output():
    source = SignalEvidenceCollection(
        chain_id="solana",
        token_identity="mint-A",
        evidence=(),
    )

    normalized = normalize_signal_evidence(source)

    assert isinstance(normalized, NormalizedSignalEvidenceCollection)
    assert normalized.evidence == ()
    assert normalized.chain_id == source.chain_id
    assert normalized.token_identity == source.token_identity
    assert normalized.representation_digest == (
        normalize_signal_evidence(source).representation_digest
    )
