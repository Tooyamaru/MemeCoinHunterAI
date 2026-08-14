from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import MappingProxyType

import pytest

from core.features import (
    FeatureCalculationStatus,
    calculate_price_velocity,
    create_feature_calculation_snapshot,
)
from core.opportunity import (
    OpportunityCandidate,
    OpportunityCandidateState,
    OpportunityCandidateResult,
    OpportunityUpstreamKind,
    P05_T01_CONTRACT_VERSION,
    create_opportunity_candidate,
    create_opportunity_candidate_result,
)
from core.risk.safety_eligibility import derive_token_eligibility
from core.risk.safety_evidence import (
    DerivedEligibilityOutput,
    EligibilityStatus,
    SafetyDomain,
    SafetyStatus,
)
from core.risk.safety_evaluation import P03_T02_CONTRACT_VERSION
from core.signals.signal_snapshot import snapshot_signal_evidence
from tests.test_price_features import _context, _price
from tests.test_safety_eligibility import _evaluation
from tests.test_signal_snapshot import _aggregation, _evidence


UTC = timezone.utc
REFERENCE_TIME = datetime(2026, 8, 12, 12, 5, tzinfo=UTC)


def _eligibility(
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
) -> DerivedEligibilityOutput:
    if status is EligibilityStatus.ELIGIBLE:
        domains = {
            SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS,
        }
    elif status is EligibilityStatus.INELIGIBLE:
        domains = {
            SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.FAIL,
        }
    else:
        domains = {
            SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.UNKNOWN,
        }
    return derive_token_eligibility(_evaluation(domains))


def _signal_snapshot(*, observed_at: datetime | None = None):
    evidence = _evidence(
        observed_at=observed_at or datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    )
    return snapshot_signal_evidence(_aggregation(evidence))


def _feature_snapshot(*, reference_time: datetime | None = None):
    result = calculate_price_velocity(
        [_price(0, 10), _price(2, 14)],
        context=_context(
            reference_time=reference_time
            or datetime(2026, 8, 11, 12, 0, 10, tzinfo=UTC)
        ),
    )
    return create_feature_calculation_snapshot(result)


def _candidate(
    *,
    candidate_id: str = "candidate-1",
    reference_time: datetime = REFERENCE_TIME,
    eligibility: DerivedEligibilityOutput | None = None,
    signal_snapshot=None,
    feature_snapshots=(),
    analytical_context=None,
):
    return create_opportunity_candidate(
        candidate_id=candidate_id,
        chain_id="solana",
        token_identity="mint-A",
        reference_time=reference_time,
        eligibility=eligibility or _eligibility(),
        signal_snapshot=signal_snapshot or _signal_snapshot(),
        feature_snapshots=feature_snapshots,
        analytical_context=analytical_context,
    )


def test_valid_candidate_preserves_upstream_contracts_and_provenance():
    feature = _feature_snapshot()

    candidate = _candidate(
        feature_snapshots=[feature],
        analytical_context={"source": "fixture", "window": "point-in-time"},
    )

    assert candidate.state is OpportunityCandidateState.VALID
    assert candidate.is_eligible is True
    assert candidate.candidate_id == "candidate-1"
    assert candidate.chain_id == "solana"
    assert candidate.token_identity == "mint-A"
    assert candidate.reference_time == REFERENCE_TIME
    assert candidate.eligibility.status is EligibilityStatus.ELIGIBLE
    assert candidate.signal_snapshot.token_identity == "mint-A"
    assert candidate.feature_snapshots == (feature,)
    assert candidate.contract_version == P05_T01_CONTRACT_VERSION
    assert tuple(value.kind for value in candidate.upstream_references) == (
        OpportunityUpstreamKind.P03_ELIGIBILITY,
        OpportunityUpstreamKind.P04_SIGNAL_SNAPSHOT,
        OpportunityUpstreamKind.P04_FEATURE_SNAPSHOT,
    )


def test_candidate_is_immutable_with_frozen_nested_context():
    context = {"nested": {"value": Decimal("1.25")}, "items": ["a", "b"]}
    candidate = _candidate(analytical_context=context)

    context["nested"]["value"] = Decimal("99")
    context["items"].append("changed")

    with pytest.raises(FrozenInstanceError):
        candidate.candidate_id = "changed"
    with pytest.raises(TypeError):
        candidate.analytical_context["new"] = "value"
    with pytest.raises(TypeError):
        candidate.analytical_context["nested"]["value"] = "changed"
    assert isinstance(candidate.analytical_context, MappingProxyType)
    assert candidate.analytical_context["nested"]["value"] == "1.25"
    assert candidate.analytical_context["items"] == ("a", "b")


def test_equivalent_context_insertion_order_has_same_representation_and_digest():
    left = _candidate(
        analytical_context={"b": 2, "a": ["x", "y"]},
    )
    right = _candidate(
        analytical_context={"a": ["x", "y"], "b": 2},
    )

    assert left.canonical_representation == right.canonical_representation
    assert left.deterministic_representation == right.deterministic_representation
    assert left.digest == right.digest


@pytest.mark.parametrize(
    ("left", "right"),
    [
        pytest.param(
            {"candidate_id": "candidate-1"},
            {"candidate_id": "candidate-2"},
            id="candidate-identity",
        ),
        pytest.param(
            {"analytical_context": {"window": "short"}},
            {"analytical_context": {"window": "long"}},
            id="analytical-context",
        ),
    ],
)
def test_identity_or_context_change_changes_digest(left, right):
    left_candidate = _candidate(**left)
    right_candidate = _candidate(**right)

    assert left_candidate.digest != right_candidate.digest


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"candidate_id": ""}, id="missing-candidate-id"),
        pytest.param({"token_identity": ""}, id="missing-token-identity"),
    ],
)
def test_missing_required_identity_is_rejected(changes):
    values = {
        "candidate_id": "candidate-1",
        "chain_id": "solana",
        "token_identity": "mint-A",
        "reference_time": REFERENCE_TIME,
        "eligibility": _eligibility(),
        "signal_snapshot": _signal_snapshot(),
    }
    values.update(changes)

    with pytest.raises(ValueError):
        OpportunityCandidate(**values)


def test_naive_candidate_reference_time_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        _candidate(reference_time=REFERENCE_TIME.replace(tzinfo=None))


def test_invalid_upstream_timestamp_is_rejected():
    with pytest.raises(ValueError):
        _candidate(
            signal_snapshot=_signal_snapshot(
                observed_at=REFERENCE_TIME + timedelta(seconds=1)
            )
        )


def test_future_feature_snapshot_is_rejected():
    with pytest.raises(ValueError, match="after candidate"):
        _candidate(
            feature_snapshots=[
                _feature_snapshot(
                    reference_time=REFERENCE_TIME + timedelta(seconds=1)
                )
            ]
        )


@pytest.mark.parametrize(
    "upstream",
    ["eligibility", "signal", "feature"],
)
def test_mismatched_upstream_contract_version_is_rejected(upstream):
    eligibility = _eligibility()
    signal = _signal_snapshot()
    feature = _feature_snapshot()
    if upstream == "eligibility":
        eligibility = replace(
            eligibility,
            contract_version="p03-unsupported-v9",
        )
    elif upstream == "signal":
        signal = replace(signal, contract_version="p04-unsupported-v9")
    else:
        feature = replace(feature, contract_version="p04-unsupported-v9")

    with pytest.raises(ValueError, match="contract version"):
        _candidate(
            eligibility=eligibility,
            signal_snapshot=signal,
            feature_snapshots=[feature],
        )


@pytest.mark.parametrize(
    "status",
    [EligibilityStatus.INELIGIBLE, EligibilityStatus.UNKNOWN],
)
def test_ineligible_or_unknown_upstream_produces_blocked_candidate(status):
    result = create_opportunity_candidate_result(
        candidate_id="blocked-candidate",
        chain_id="solana",
        token_identity="mint-A",
        reference_time=REFERENCE_TIME,
        eligibility=_eligibility(status),
        signal_snapshot=_signal_snapshot(),
    )

    assert result.state is OpportunityCandidateState.BLOCKED
    assert result.blocked is True
    assert result.valid is True
    assert result.candidate is not None
    assert "UPSTREAM_NOT_ELIGIBLE" in result.reason_codes


def test_invalid_upstream_produces_explicit_invalid_result():
    result = create_opportunity_candidate_result(
        candidate_id="invalid-candidate",
        chain_id="solana",
        token_identity="mint-A",
        reference_time=REFERENCE_TIME,
        eligibility=_eligibility(),
        signal_snapshot=None,
    )

    assert result == OpportunityCandidateResult(
        state=OpportunityCandidateState.INVALID,
        candidate=None,
        reason_codes=("INVALID_INPUT",),
        representation_digest=None,
    )
    assert result.valid is False


def test_empty_or_invalid_upstream_references_are_rejected():
    empty_eligibility = DerivedEligibilityOutput(
        status=EligibilityStatus.UNKNOWN,
        evaluator_id="evaluator",
        evaluated_at=REFERENCE_TIME,
        evidence_references=(),
        contract_version=P03_T02_CONTRACT_VERSION,
        reason_codes=("NO_EVIDENCE",),
    )

    with pytest.raises(ValueError, match="evidence references"):
        _candidate(eligibility=empty_eligibility)
    with pytest.raises(ValueError):
        _candidate(feature_snapshots=[object()])


def test_upstream_objects_are_not_mutated():
    eligibility = _eligibility()
    signal = _signal_snapshot()
    feature = _feature_snapshot()
    before = (
        eligibility,
        signal.canonical_representation,
        feature.canonical_representation,
    )

    candidate = _candidate(
        eligibility=eligibility,
        signal_snapshot=signal,
        feature_snapshots=[feature],
    )

    assert candidate.eligibility is eligibility
    assert candidate.signal_snapshot is signal
    assert candidate.feature_snapshots == (feature,)
    assert (eligibility, signal.canonical_representation, feature.canonical_representation) == before


def test_contract_requires_no_provider_specific_payload_and_is_not_actionable():
    candidate = _candidate()

    assert candidate.analytical_context == {}
    assert candidate.is_authoritative is False
    assert candidate.is_decision is False
    assert candidate.is_order is False
    assert candidate.is_authorization is False
    assert not hasattr(candidate, "opportunity_score")
    assert not hasattr(candidate, "ranking_score")
    assert not hasattr(candidate, "buy")
    assert not hasattr(candidate, "sell")
    assert {state.value for state in OpportunityCandidateState} == {
        "VALID",
        "BLOCKED",
        "INVALID",
    }


def test_repeated_construction_from_same_inputs_is_stable():
    first = _candidate(
        feature_snapshots=[_feature_snapshot()],
        analytical_context={"threshold": Decimal("1.0")},
    )
    second = _candidate(
        feature_snapshots=[_feature_snapshot()],
        analytical_context={"threshold": Decimal("1.0")},
    )

    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest
    assert first.upstream_representation_digests == second.upstream_representation_digests


def test_future_and_naive_upstream_times_fail_closed_in_result_wrapper():
    future = create_opportunity_candidate_result(
        candidate_id="future",
        chain_id="solana",
        token_identity="mint-A",
        reference_time=REFERENCE_TIME,
        eligibility=_eligibility(),
        signal_snapshot=_signal_snapshot(
            observed_at=REFERENCE_TIME + timedelta(seconds=1)
        ),
    )
    naive = create_opportunity_candidate_result(
        candidate_id="naive",
        chain_id="solana",
        token_identity="mint-A",
        reference_time=REFERENCE_TIME.replace(tzinfo=None),
        eligibility=_eligibility(),
        signal_snapshot=_signal_snapshot(),
    )

    assert future.state is OpportunityCandidateState.INVALID
    assert naive.state is OpportunityCandidateState.INVALID