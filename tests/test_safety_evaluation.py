from datetime import datetime, timedelta, timezone
from types import MappingProxyType

from core.data.contracts import DataQuality
from core.risk.safety_evaluation import (
    P03_T02_CONTRACT_VERSION,
    SafetyEvaluationResult,
    evaluate_safety_evidence,
)
from core.risk.safety_evidence import (
    P02StateReference,
    SafetyDomain,
    SafetyEvidenceCollection,
    SafetyProvenance,
    SafetyStatus,
    TokenSafetyEvidence,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 8, 12, 12, 1, tzinfo=UTC)


def _evidence(
    *,
    status: SafetyStatus = SafetyStatus.PASS,
    domain: SafetyDomain = SafetyDomain.LIQUIDITY_QUALITY,
    evidence_reference: str = "evidence-1",
    source_id: str = "safety-source",
    observed_at: datetime = OBSERVED_AT,
    quality: DataQuality = DataQuality.VALID,
    freshness_status: DataQuality = DataQuality.VALID,
    data_age: timedelta | None = timedelta(seconds=5),
    reason_codes: tuple[str, ...] = (),
    evidence_context: dict | None = None,
    token_identity: str = "mint-A",
) -> TokenSafetyEvidence:
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
            metadata={"source": "fixture"},
        ),
        evidence_reference=evidence_reference,
        evidence_context=(
            {"observation": "explicit qualifying fact"}
            if evidence_context is None and status is SafetyStatus.PASS
            else evidence_context or {}
        ),
        p02_reference=P02StateReference(
            state_version="p02-state-v1",
            state_digest="p02-digest",
            contract_version="p02-t09-v1",
        ),
        reason_codes=reason_codes,
    )


def _collection(*items: TokenSafetyEvidence) -> SafetyEvidenceCollection:
    return SafetyEvidenceCollection.from_evidence(list(items))


def test_pass_evidence_produces_pass_result():
    result = evaluate_safety_evidence(
        _collection(_evidence()),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.domain_results == {
        SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS
    }


def test_fail_evidence_produces_fail_result():
    result = evaluate_safety_evidence(
        _collection(
            _evidence(
                status=SafetyStatus.FAIL,
                reason_codes=("NEGATIVE_EVIDENCE",),
                evidence_context={},
            )
        ),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.domain_results == {
        SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.FAIL
    }


def test_unknown_evidence_produces_unknown_result():
    result = evaluate_safety_evidence(
        _collection(
            _evidence(
                status=SafetyStatus.UNKNOWN,
                quality=DataQuality.SOURCE_UNAVAILABLE,
                freshness_status=DataQuality.SOURCE_UNAVAILABLE,
                data_age=None,
                reason_codes=("SOURCE_UNAVAILABLE",),
                evidence_context={},
            )
        ),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.domain_results == {
        SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.UNKNOWN
    }


def test_contradictory_pass_and_fail_produce_unknown():
    passed = _evidence(evidence_reference="pass")
    failed = _evidence(
        status=SafetyStatus.FAIL,
        evidence_reference="fail",
        reason_codes=("NEGATIVE_EVIDENCE",),
        evidence_context={},
    )

    result = evaluate_safety_evidence(
        _collection(passed, failed),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.domain_results[SafetyDomain.LIQUIDITY_QUALITY] is SafetyStatus.UNKNOWN
    assert "CONTRADICTORY_EVIDENCE" in result.reason_codes


def test_unknown_never_becomes_pass():
    result = evaluate_safety_evidence(
        _collection(
            _evidence(
                status=SafetyStatus.UNKNOWN,
                reason_codes=("NOT_ENOUGH_DATA",),
                quality=DataQuality.INCOMPLETE,
                freshness_status=DataQuality.INCOMPLETE,
                data_age=None,
                evidence_context={},
            )
        ),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert SafetyStatus.PASS not in result.domain_results.values()


def test_missing_evidence_fails_closed():
    result = evaluate_safety_evidence(
        SafetyEvidenceCollection(
            chain_id="solana",
            token_identity="mint-A",
            evidence=(),
        ),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.domain_results == {}
    assert result.reason_codes == ("NO_EVIDENCE",)


def test_stale_evidence_represented_as_unknown_stays_unknown():
    result = evaluate_safety_evidence(
        _collection(
            _evidence(
                status=SafetyStatus.UNKNOWN,
                quality=DataQuality.STALE,
                freshness_status=DataQuality.STALE,
                data_age=timedelta(days=1),
                reason_codes=("STALE_EVIDENCE",),
                evidence_context={},
            )
        ),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.domain_results[SafetyDomain.LIQUIDITY_QUALITY] is SafetyStatus.UNKNOWN


def test_duplicate_evidence_is_preserved():
    first = _evidence(evidence_reference="duplicate", source_id="source-a")
    second = _evidence(evidence_reference="duplicate", source_id="source-b")
    collection = _collection(first, second)

    result = evaluate_safety_evidence(
        collection,
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.evidence_references == ("duplicate", "duplicate")
    assert tuple(item.source_id for item in result.provenance) == (
        "source-a",
        "source-b",
    )
    assert len(result.provenance) == 2


def test_input_collection_is_not_mutated():
    passed = _evidence(evidence_reference="pass")
    failed = _evidence(
        status=SafetyStatus.FAIL,
        evidence_reference="fail",
        reason_codes=("NEGATIVE_EVIDENCE",),
        evidence_context={},
    )
    collection = _collection(passed, failed)
    before = collection.evidence

    evaluate_safety_evidence(collection, evaluation_timestamp=EVALUATED_AT)

    assert collection.evidence is before
    assert collection.evidence == (passed, failed)


def test_p02_reference_is_not_mutated():
    reference = P02StateReference(
        state_version="state",
        state_digest="digest",
        contract_version="p02-t09-v1",
        evaluation_id="evaluation",
    )
    evidence = TokenSafetyEvidence(
        chain_id="solana",
        token_identity="mint-A",
        domain=SafetyDomain.LIQUIDITY_QUALITY,
        status=SafetyStatus.PASS,
        source_id="source",
        observed_at=OBSERVED_AT,
        quality=DataQuality.VALID,
        freshness_status=DataQuality.VALID,
        data_age=timedelta(seconds=5),
        provenance=SafetyProvenance(
            source_id="source",
            method="method",
            observed_at=OBSERVED_AT,
        ),
        evidence_reference="evidence",
        evidence_context={"fact": "qualifying"},
        p02_reference=reference,
    )

    evaluate_safety_evidence(
        _collection(evidence),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert reference == P02StateReference(
        state_version="state",
        state_digest="digest",
        contract_version="p02-t09-v1",
        evaluation_id="evaluation",
    )


def test_provenance_and_evidence_references_remain_traceable():
    item = _evidence(evidence_reference="traceable")
    result = evaluate_safety_evidence(
        _collection(item),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert result.evidence_references == ("traceable",)
    assert result.provenance == (item.provenance,)
    assert result.input_evidence_digest


def test_reference_and_provenance_sorting_preserves_traceability():
    first = _evidence(
        evidence_reference="z-reference",
        source_id="a-source",
    )
    second = _evidence(
        evidence_reference="a-reference",
        source_id="z-source",
    )

    result = evaluate_safety_evidence(
        _collection(first, second),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert tuple(
        zip(
            result.evidence_references,
            (item.source_id for item in result.provenance),
        )
    ) == (
        ("a-reference", "z-source"),
        ("z-reference", "a-source"),
    )


def test_equivalent_inputs_produce_identical_output_digests():
    left = _evidence(
        evidence_reference="same",
        evidence_context={"z": 1, "a": {"b": 2, "a": 1}},
    )
    right = _evidence(
        evidence_reference="same",
        evidence_context={"a": {"a": 1, "b": 2}, "z": 1},
    )

    first = evaluate_safety_evidence(
        _collection(left),
        evaluation_timestamp=EVALUATED_AT,
    )
    second = evaluate_safety_evidence(
        _collection(right),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert first.representation_digest == second.representation_digest


def test_timezone_equivalent_evaluation_inputs_have_identical_digests():
    utc_result = evaluate_safety_evidence(
        _collection(_evidence()),
        evaluation_timestamp=EVALUATED_AT,
    )
    offset_result = evaluate_safety_evidence(
        _collection(
            _evidence(
                observed_at=datetime(
                    2026,
                    8,
                    12,
                    8,
                    0,
                    tzinfo=timezone(timedelta(hours=-4)),
                )
            )
        ),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert utc_result.representation_digest == offset_result.representation_digest


def test_input_order_does_not_change_logical_output_digest():
    passed = _evidence(
        domain=SafetyDomain.LIQUIDITY_QUALITY,
        evidence_reference="pass",
    )
    failed = _evidence(
        domain=SafetyDomain.TOP_HOLDER_CONCENTRATION,
        evidence_reference="fail",
        status=SafetyStatus.FAIL,
        reason_codes=("NEGATIVE_EVIDENCE",),
        evidence_context={},
    )

    first = evaluate_safety_evidence(
        _collection(passed, failed),
        evaluation_timestamp=EVALUATED_AT,
    )
    reordered = evaluate_safety_evidence(
        _collection(failed, passed),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert first.domain_results == reordered.domain_results
    assert first.representation_digest == reordered.representation_digest


def test_different_domain_results_are_distinguishable():
    liquidity = evaluate_safety_evidence(
        _collection(
            _evidence(
                domain=SafetyDomain.LIQUIDITY_QUALITY,
                evidence_reference="liquidity",
            )
        ),
        evaluation_timestamp=EVALUATED_AT,
    )
    holders = evaluate_safety_evidence(
        _collection(
            _evidence(
                domain=SafetyDomain.TOP_HOLDER_CONCENTRATION,
                evidence_reference="holders",
            )
        ),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert liquidity.domain_results != holders.domain_results
    assert liquidity.representation_digest != holders.representation_digest


def test_output_is_immutable_and_non_authoritative():
    result = evaluate_safety_evidence(
        _collection(_evidence()),
        evaluation_timestamp=EVALUATED_AT,
    )

    assert isinstance(result.domain_results, MappingProxyType)
    assert result.is_authoritative is False
    assert P03_T02_CONTRACT_VERSION == result.contract_version
    assert not any(
        name in result.__dataclass_fields__
        for name in (
            "authorization",
            "buy",
            "sell",
            "trade_intent",
            "execution_permission",
            "wallet_action",
        )
    )