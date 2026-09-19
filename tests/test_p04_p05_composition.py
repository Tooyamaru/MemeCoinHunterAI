from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.features import (
    FeatureCalculationStatus,
    calculate_price_acceleration,
    calculate_price_velocity,
    create_feature_calculation_snapshot,
)
from core.opportunity import (
    CandidateViabilityStatus,
    P05_T04_EVALUATOR_VERSION,
    P05_T05_EVALUATOR_VERSION,
    compose_canonical_p04_to_p05,
)
from core.risk.safety_evidence import EligibilityStatus
from core.signals.signal_snapshot import snapshot_signal_evidence_result
from tests.test_opportunity_candidate import (
    REFERENCE_TIME,
    _context,
    _eligibility,
    _price,
)
from tests.test_signal_snapshot import _aggregation, _evidence


UTC = timezone.utc


def _signal_aggregation():
    return _aggregation(_evidence(observed_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC)))


def _feature_results():
    velocity = calculate_price_velocity(
        [_price(0, 10), _price(2, 14)],
        context=_context(
            reference_time=datetime(2026, 8, 11, 12, 0, 10, tzinfo=UTC)
        ),
    )
    acceleration = calculate_price_acceleration(
        [_price(0, 10), _price(1, 12), _price(2, 15)],
        context=_context(
            reference_time=datetime(2026, 8, 11, 12, 0, 10, tzinfo=UTC)
        ),
    )
    return velocity, acceleration


def _compose(**overrides):
    values = {
        "candidate_id": "canonical-candidate",
        "chain_id": "solana",
        "token_identity": "mint-A",
        "reference_time": REFERENCE_TIME,
        "eligibility": _eligibility(),
        "signal_aggregation": _signal_aggregation(),
        "feature_results": _feature_results(),
    }
    values.update(overrides)
    return compose_canonical_p04_to_p05(**values)


def test_composition_builds_canonical_snapshots_and_executes_real_p05_chain():
    result = _compose()

    assert result.candidate_state == "VALID"
    assert result.risk_evaluation.viability_status is CandidateViabilityStatus.ELIGIBLE
    assert result.feature_evaluation.evaluator_version == P05_T04_EVALUATOR_VERSION
    assert result.score.evaluator_version == P05_T05_EVALUATOR_VERSION
    assert result.score.score == Decimal("80.55555555555555555555555556")
    assert result.score.feature_evaluation is result.feature_evaluation
    assert result.feature_evaluation.signal_snapshot is result.signal_snapshot
    assert result.feature_snapshots == result.candidate.feature_snapshots
    assert result.provenance_digests == result.candidate.upstream_representation_digests
    assert result.candidate.signal_snapshot.aggregation_digest == (
        result.signal_snapshot.aggregation_digest
    )


def test_composition_is_deterministic_and_uses_reference_time_by_default():
    first = _compose()
    second = _compose()

    assert first == second
    assert first.score.evaluated_at == REFERENCE_TIME
    assert first.digest == second.digest


def test_missing_signal_evidence_is_rejected_before_p05():
    empty = _aggregation()
    assert snapshot_signal_evidence_result(empty).valid is False

    with pytest.raises(ValueError, match="EMPTY_INPUT"):
        _compose(signal_aggregation=empty)


@pytest.mark.parametrize("status", [EligibilityStatus.UNKNOWN, EligibilityStatus.INELIGIBLE])
def test_unknown_or_ineligible_safety_never_becomes_a_score(status):
    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _compose(eligibility=_eligibility(status))


def test_identity_mismatch_is_rejected_by_the_candidate_boundary():
    with pytest.raises(ValueError, match="identity"):
        _compose(token_identity="different-token")


def test_invalid_time_ordering_is_preserved_as_a_blocking_feature_result():
    invalid = calculate_price_velocity(
        [
            _price(0, 10),
            _price(
                2,
                14,
                observation_time=datetime(2026, 8, 11, 12, 0, 3, tzinfo=UTC),
                received_time=datetime(2026, 8, 11, 12, 0, 2, tzinfo=UTC),
                data_age=timedelta(seconds=7),
            ),
        ],
        context=_context(
            reference_time=datetime(2026, 8, 11, 12, 0, 10, tzinfo=UTC)
        ),
    )

    assert invalid.status is FeatureCalculationStatus.INVALID
    assert "INVALID_TIMESTAMP_ORDER" in invalid.reason_codes
    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _compose(feature_results=[invalid, _feature_results()[1]])


def test_malformed_numbers_remain_invalid_and_cannot_reach_scoring():
    malformed = calculate_price_velocity(
        [replace(_price(0, 10), value=float("inf")), _price(2, 14)],
        context=_context(
            reference_time=datetime(2026, 8, 11, 12, 0, 10, tzinfo=UTC)
        ),
    )

    assert malformed.status is FeatureCalculationStatus.INVALID
    assert malformed.value is None
    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _compose(feature_results=[malformed, _feature_results()[1]])


def test_altered_feature_digest_or_provenance_is_rejected_by_p04_snapshot():
    result = _feature_results()[0]
    tampered = replace(result, representation_digest="tampered-digest")

    with pytest.raises(ValueError, match="INVALID_CALCULATION_RESULT"):
        _compose(feature_results=[tampered, _feature_results()[1]])


def test_altered_feature_snapshot_provenance_is_rejected_by_p04_snapshot():
    result = _feature_results()[0]
    tampered_linkage = replace(
        result.snapshot_linkage,
        feature_representation_digest="tampered-digest",
    )
    tampered = replace(result, snapshot_linkage=tampered_linkage)

    with pytest.raises(ValueError, match="INVALID_CALCULATION_RESULT"):
        _compose(feature_results=[tampered, _feature_results()[1]])


def test_altered_signal_trace_provenance_is_rejected_by_existing_aggregation_contract():
    aggregation = _signal_aggregation()

    with pytest.raises(ValueError, match="equal lengths"):
        replace(aggregation, evidence_references=())