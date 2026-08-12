from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from core.data.contracts import DataQuality
from core.risk.safety_evidence import (
    DerivedEligibilityOutput,
    EligibilityStatus,
    P02StateReference,
    SafetyDomain,
    SafetyEvidenceCollection,
    SafetyProvenance,
    SafetyStatus,
    TokenSafetyEvidence,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def _evidence(
    *,
    status: SafetyStatus = SafetyStatus.PASS,
    domain: SafetyDomain = SafetyDomain.LIQUIDITY_QUALITY,
    source_id: str = "safety-source",
    quality: DataQuality = DataQuality.VALID,
    freshness_status: DataQuality = DataQuality.VALID,
    data_age: timedelta | None = timedelta(seconds=5),
    evidence_reference: str = "evidence-1",
    evidence_context: dict | None = None,
    reason_codes: tuple[str, ...] = (),
    token_identity: str = "mint-A",
    observed_at: datetime = OBSERVED_AT,
    p02_reference: P02StateReference | None = None,
):
    return TokenSafetyEvidence(
        chain_id="solana",
        token_identity=token_identity,
        domain=domain,
        status=status,
        source_id=source_id,
        observed_at=observed_at,
        quality=quality,
        freshness_status=freshness_status,
        data_age=data_age,
        provenance=SafetyProvenance(
            source_id=source_id,
            method="bounded-observation",
            observed_at=observed_at,
            metadata={"source": "fixture", "nested": {"stable": True}},
        ),
        evidence_reference=evidence_reference,
        evidence_context=(
            {"observation": "explicit qualifying fact"}
            if evidence_context is None and status is SafetyStatus.PASS
            else evidence_context or {}
        ),
        p02_reference=(
            p02_reference
            if p02_reference is not None
            else P02StateReference(
                state_version="p02-state-v1",
                state_digest="p02-digest",
                contract_version="p02-t09-v1",
            )
        ),
        reason_codes=reason_codes,
    )


def test_pass_fail_and_unknown_evidence_are_constructible():
    passed = _evidence()
    failed = _evidence(
        status=SafetyStatus.FAIL,
        reason_codes=("EXPLICIT_NEGATIVE_EVIDENCE",),
        evidence_context={},
    )
    unknown = _evidence(
        status=SafetyStatus.UNKNOWN,
        reason_codes=("EVIDENCE_UNAVAILABLE",),
        quality=DataQuality.SOURCE_UNAVAILABLE,
        freshness_status=DataQuality.SOURCE_UNAVAILABLE,
        data_age=None,
        evidence_context={},
    )

    assert passed.status is SafetyStatus.PASS
    assert failed.status is SafetyStatus.FAIL
    assert unknown.status is SafetyStatus.UNKNOWN


@pytest.mark.parametrize(
    "overrides",
    [
        {"evidence_context": {}},
        {"quality": DataQuality.STALE},
        {"freshness_status": DataQuality.STALE},
        {"quality": DataQuality.SOURCE_UNAVAILABLE, "freshness_status": DataQuality.SOURCE_UNAVAILABLE},
        {"data_age": None},
    ],
)
def test_pass_without_qualifying_fresh_evidence_is_rejected(overrides):
    with pytest.raises(ValueError):
        _evidence(**overrides)


def test_unknown_and_unavailable_evidence_are_non_positive():
    unknown = _evidence(
        status=SafetyStatus.UNKNOWN,
        reason_codes=("NOT_ENOUGH_DATA",),
        quality=DataQuality.INCOMPLETE,
        freshness_status=DataQuality.INCOMPLETE,
        data_age=None,
        evidence_context={},
    )
    unavailable = _evidence(
        status=SafetyStatus.UNKNOWN,
        reason_codes=("SOURCE_UNAVAILABLE",),
        quality=DataQuality.SOURCE_UNAVAILABLE,
        freshness_status=DataQuality.SOURCE_UNAVAILABLE,
        data_age=None,
        evidence_context={},
    )

    assert unknown.is_positive_evidence is False
    assert unavailable.is_non_positive is True


def test_p02_known_state_does_not_become_p03_pass():
    evidence = _evidence(
        status=SafetyStatus.UNKNOWN,
        reason_codes=("P02_STATE_IS_NOT_SAFETY_EVIDENCE",),
        quality=DataQuality.VALID,
        freshness_status=DataQuality.VALID,
        evidence_context={"p02_status": "KNOWN"},
    )

    assert evidence.status is SafetyStatus.UNKNOWN
    assert evidence.is_positive_evidence is False


def test_conflicting_evidence_is_preserved_without_a_winner():
    passed = _evidence(evidence_reference="pass")
    failed = _evidence(
        status=SafetyStatus.FAIL,
        evidence_reference="fail",
        reason_codes=("NEGATIVE_EVIDENCE",),
        evidence_context={"observation": "explicit negative fact"},
    )
    collection = SafetyEvidenceCollection.from_evidence([passed, failed])

    assert collection.has_conflicts is True
    assert collection.conflicting_domains == (SafetyDomain.LIQUIDITY_QUALITY,)
    assert {item.evidence_reference for item in collection.evidence} == {"pass", "fail"}


def test_p02_reference_and_identity_fields_are_preserved():
    evidence = _evidence()

    assert evidence.token_key == ("solana", "mint-A")
    assert evidence.source_id == "safety-source"
    assert evidence.provenance.source_id == "safety-source"
    assert evidence.observed_at == OBSERVED_AT
    assert evidence.quality is DataQuality.VALID
    assert evidence.evidence_reference == "evidence-1"
    assert evidence.p02_reference is not None
    assert evidence.p02_reference.state_version == "p02-state-v1"
    assert evidence.p02_reference.state_digest == "p02-digest"


def test_top_level_and_nested_values_are_immutable():
    evidence = _evidence()

    with pytest.raises(FrozenInstanceError):
        evidence.status = SafetyStatus.FAIL
    assert isinstance(evidence.evidence_context, MappingProxyType)
    assert isinstance(evidence.evidence_context["observation"], str)
    with pytest.raises(TypeError):
        evidence.evidence_context["new"] = "value"

    nested = _evidence(
        evidence_context={"facts": [{"name": "liquidity", "value": "adequate"}]}
    )
    with pytest.raises(TypeError):
        nested.evidence_context["facts"][0]["value"] = "changed"


def test_equivalent_inputs_have_deterministic_representations():
    left = _evidence(
        evidence_context={"z": 1, "a": {"b": 2, "a": 1}},
        evidence_reference="same",
    )
    right = _evidence(
        evidence_context={"a": {"a": 1, "b": 2}, "z": 1},
        evidence_reference="same",
    )

    assert left == right
    assert left.representation_digest == right.representation_digest
    assert SafetyEvidenceCollection.from_evidence([left]).representation_digest == (
        SafetyEvidenceCollection.from_evidence([right]).representation_digest
    )


def test_timezone_equivalent_timestamps_have_identical_digests():
    utc_evidence = _evidence()
    offset_evidence = _evidence(
        observed_at=datetime(2026, 8, 12, 8, 0, tzinfo=timezone(timedelta(hours=-4)))
    )

    assert utc_evidence.representation_digest == offset_evidence.representation_digest


def test_reordered_collection_evidence_has_identical_digest():
    passed = _evidence(evidence_reference="pass")
    failed = _evidence(
        status=SafetyStatus.FAIL,
        evidence_reference="fail",
        reason_codes=("NEGATIVE_EVIDENCE",),
        evidence_context={"observation": "explicit negative fact"},
    )
    first = SafetyEvidenceCollection.from_evidence([passed, failed])
    reordered = SafetyEvidenceCollection.from_evidence([failed, passed])

    assert first.evidence == (passed, failed)
    assert reordered.evidence == (failed, passed)
    assert first.representation_digest == reordered.representation_digest


def test_upstream_p02_reference_is_not_mutated():
    reference = P02StateReference(
        state_version="state",
        state_digest="digest",
        contract_version="p02-t09-v1",
        evaluation_id="evaluation",
    )
    evidence = _evidence(p02_reference=reference)
    before = reference

    assert evidence.p02_reference == before
    assert reference.state_version == "state"
    assert reference.state_digest == "digest"


def test_caller_eligible_value_is_only_a_non_authoritative_future_output():
    output = DerivedEligibilityOutput(
        status=EligibilityStatus.ELIGIBLE,
        evaluator_id="future-evaluator",
        evaluated_at=OBSERVED_AT,
        evidence_references=("evidence-1",),
    )

    assert output.status is EligibilityStatus.ELIGIBLE
    assert output.is_authoritative is False


def test_derived_eligibility_output_accepts_empty_evidence_references():
    output = DerivedEligibilityOutput(
        status=EligibilityStatus.UNKNOWN,
        evaluator_id="future-evaluator",
        evaluated_at=OBSERVED_AT,
        evidence_references=(),
    )

    assert output.evidence_references == ()


def test_derived_eligibility_output_preserves_duplicate_evidence_references():
    output = DerivedEligibilityOutput(
        status=EligibilityStatus.UNKNOWN,
        evaluator_id="future-evaluator",
        evaluated_at=OBSERVED_AT,
        evidence_references=("duplicate", "duplicate"),
    )

    assert output.evidence_references == ("duplicate", "duplicate")


def test_derived_eligibility_output_normalizes_references_and_remains_immutable():
    output = DerivedEligibilityOutput(
        status=EligibilityStatus.UNKNOWN,
        evaluator_id="future-evaluator",
        evaluated_at=OBSERVED_AT,
        evidence_references=["reference"],
    )

    assert output.evidence_references == ("reference",)
    with pytest.raises(FrozenInstanceError):
        output.evidence_references = ("changed",)