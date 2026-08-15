from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from core.opportunity import (
    NormalizedOpportunityCandidate,
    OpportunityCandidateState,
    P05_T01_CONTRACT_VERSION,
    P05_T02_CONTRACT_VERSION,
    normalize_opportunity_candidate,
)
from core.features.feature_snapshot import P04_T10_CONTRACT_VERSION
from core.risk.safety_evaluation import P03_T02_CONTRACT_VERSION
from core.signals.signal_snapshot import P04_T06_CONTRACT_VERSION
from core.risk.safety_eligibility import EligibilityStatus
from tests.test_opportunity_candidate import (
    REFERENCE_TIME,
    _candidate,
    _eligibility,
    _feature_snapshot,
    _signal_snapshot,
)


UTC = timezone.utc


def test_valid_candidate_normalization_preserves_identity_and_reference_time():
    candidate = _candidate(
        feature_snapshots=[_feature_snapshot()],
        analytical_context={"window": "point-in-time"},
    )

    normalized = normalize_opportunity_candidate(candidate)

    assert isinstance(normalized, NormalizedOpportunityCandidate)
    assert normalized.candidate is candidate
    assert normalized.candidate_id == candidate.candidate_id
    assert normalized.chain_id == candidate.chain_id
    assert normalized.token_identity == candidate.token_identity
    assert normalized.reference_time == REFERENCE_TIME
    assert normalized.reference_time == candidate.reference_time
    assert normalized.state is OpportunityCandidateState.VALID


def test_normalization_preserves_upstream_provenance_and_versions():
    candidate = _candidate(feature_snapshots=[_feature_snapshot()])

    normalized = normalize_opportunity_candidate(candidate)

    assert normalized.eligibility is candidate.eligibility
    assert normalized.signal_snapshot is candidate.signal_snapshot
    assert normalized.feature_snapshots == candidate.feature_snapshots
    assert normalized.upstream_references == candidate.upstream_references
    assert normalized.upstream_contract_versions == (
        P03_T02_CONTRACT_VERSION,
        P04_T06_CONTRACT_VERSION,
        P04_T10_CONTRACT_VERSION,
    )
    assert normalized.upstream_representation_digests == (
        candidate.upstream_representation_digests
    )
    assert normalized.source_contract_version == P05_T01_CONTRACT_VERSION
    assert normalized.contract_version == P05_T02_CONTRACT_VERSION


def test_equivalent_candidates_have_stable_normalized_representation_and_digest():
    left = normalize_opportunity_candidate(
        _candidate(analytical_context={"b": ["x"], "a": 1})
    )
    right = normalize_opportunity_candidate(
        _candidate(analytical_context={"a": 1, "b": ["x"]})
    )

    assert left.canonical_representation == right.canonical_representation
    assert left.deterministic_representation == right.deterministic_representation
    assert left.representation_digest == right.representation_digest
    assert left.digest == right.digest


def test_repeated_normalization_is_deterministic():
    candidate = _candidate()

    first = normalize_opportunity_candidate(candidate)
    second = normalize_opportunity_candidate(candidate)

    assert first == second
    assert first.representation_digest == second.representation_digest


def test_normalized_output_is_immutable():
    normalized = normalize_opportunity_candidate(
        _candidate(analytical_context={"nested": {"stable": True}})
    )

    with pytest.raises(FrozenInstanceError):
        normalized.candidate = _candidate()
    assert isinstance(normalized.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        normalized.canonical_representation["new"] = "value"
    with pytest.raises(TypeError):
        normalized.canonical_representation["analytical_context"]["new"] = "value"
    with pytest.raises(FrozenInstanceError):
        normalized.candidate.candidate_id = "changed"


@pytest.mark.parametrize("invalid", [None, object(), "candidate"])
def test_invalid_candidate_input_fails_closed(invalid):
    with pytest.raises(ValueError):
        normalize_opportunity_candidate(invalid)


def test_wrong_normalized_contract_version_fails_closed():
    with pytest.raises(ValueError, match="contract version"):
        NormalizedOpportunityCandidate(
            candidate=_candidate(),
            contract_version="p05-t02-unsupported",
        )


def test_future_or_inconsistent_upstream_data_is_rejected_by_p05_t01():
    with pytest.raises(ValueError):
        normalize_opportunity_candidate(
            _candidate(
                signal_snapshot=_signal_snapshot(
                    observed_at=REFERENCE_TIME + timedelta(seconds=1)
                )
            )
        )
    with pytest.raises(ValueError):
        normalize_opportunity_candidate(
            _candidate(
                feature_snapshots=[
                    _feature_snapshot(
                        reference_time=REFERENCE_TIME + timedelta(seconds=1)
                    )
                ]
            )
        )


def test_blocked_state_and_reason_codes_are_preserved_without_action_semantics():
    candidate = _candidate(
        eligibility=_eligibility(EligibilityStatus.INELIGIBLE),
    )
    normalized = normalize_opportunity_candidate(candidate)

    assert normalized.state is OpportunityCandidateState.BLOCKED
    assert normalized.state is candidate.state
    assert normalized.reason_codes == candidate.reason_codes
    assert not hasattr(normalized, "opportunity_score")
    assert not hasattr(normalized, "ranking_score")
    assert not hasattr(normalized, "score")
    assert not hasattr(normalized, "buy")
    assert not hasattr(normalized, "sell")
    assert not hasattr(normalized, "watch")
    assert not hasattr(normalized, "hold")
    assert not hasattr(normalized, "decision")
    assert not hasattr(normalized, "action")