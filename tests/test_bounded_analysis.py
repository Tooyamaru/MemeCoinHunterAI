from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from core.decision import (
    BoundedAnalysisObservation,
    BoundedDeepAnalysis,
    P06_T03_CONTRACT_VERSION,
    create_bounded_deep_analysis,
    evaluate_decision_intent,
)
from core.opportunity import (
    OpportunityRecordHistory,
    evaluate_opportunity_score,
    materialize_opportunity_context,
    materialize_opportunity_record,
)
from tests.test_opportunity_score import _evaluation


def _context():
    record = materialize_opportunity_record(evaluate_opportunity_score(_evaluation()))
    return materialize_opportunity_context(record, OpportunityRecordHistory((record,)))


def _observation(context, **overrides):
    values = {
        "source_id": "supplied-feed",
        "source_version": "feed-v1",
        "evidence_reference": "evidence:123",
        "observed_at": context.reference_time,
        "content": "Observed liquidity remains available.",
    }
    values.update(overrides)
    return BoundedAnalysisObservation(**values)


def _analysis(**overrides):
    context = _context()
    values = {
        "context": context,
        "source_id": "analysis-provider",
        "source_version": "provider-v1",
        "analysis_time": context.reference_time,
        "validation_time": context.reference_time,
        "observations": (_observation(context),),
        "generated_narrative": ("Narrative is non-authoritative.",),
    }
    values.update(overrides)
    return create_bounded_deep_analysis(**values)


def test_valid_construction_preserves_provenance_and_distinguishes_narrative():
    analysis = _analysis()

    assert isinstance(analysis, BoundedDeepAnalysis)
    assert analysis.contract_version == P06_T03_CONTRACT_VERSION
    assert analysis.context_digest == analysis.context.digest
    assert analysis.observations[0].evidence_reference == "evidence:123"
    assert analysis.generated_narrative == ("Narrative is non-authoritative.",)
    assert analysis.is_authoritative is False
    assert analysis.is_generated_analysis is True


def test_analysis_and_observation_are_immutable():
    analysis = _analysis()

    with pytest.raises(FrozenInstanceError):
        analysis.source_id = "tampered"
    with pytest.raises(FrozenInstanceError):
        analysis.observations[0].content = "tampered"


def test_canonical_representation_and_digest_are_deterministic():
    first = _analysis()
    second = _analysis()

    assert first.canonical_representation == second.canonical_representation
    assert first.deterministic_representation == first.canonical_representation
    assert first.digest == second.digest
    assert len(first.digest) == 64


def test_tampered_context_is_rejected():
    context = _context()
    object.__setattr__(context, "candidate_id", "tampered")

    with pytest.raises(ValueError, match="canonical|tampered|invalid"):
        _analysis(context=context)


def test_unsupported_versions_are_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        _analysis(contract_version="unsupported")
    with pytest.raises(ValueError, match="unsupported"):
        _analysis(evaluator_version="unsupported")


def test_stale_and_future_times_are_rejected_without_a_clock():
    context = _context()
    with pytest.raises(ValueError, match="stale"):
        _analysis(
            analysis_time=context.reference_time,
            validation_time=context.reference_time + timedelta(seconds=1),
            max_age_seconds=0,
        )
    with pytest.raises(ValueError, match="future"):
        _analysis(
            analysis_time=context.reference_time + timedelta(seconds=1),
            validation_time=context.reference_time,
        )


def test_incomplete_provenance_and_invalid_observations_are_rejected():
    with pytest.raises(ValueError, match="source_id"):
        _analysis(source_id="")
    with pytest.raises(ValueError, match="evidence_reference"):
        _analysis(observations=(_observation(_context(), evidence_reference=""),))


def test_bounded_size_is_enforced():
    with pytest.raises(ValueError, match="bounded"):
        _analysis(generated_narrative=("x" * 2_049,))
    with pytest.raises(ValueError, match="bounded"):
        _analysis(
            observations=tuple(
                _observation(_context(), evidence_reference=str(index))
                for index in range(33)
            )
        )


def test_no_action_ranking_authorization_or_execution_semantics_exist():
    analysis = _analysis()

    for name in (
        "action",
        "ranking",
        "authorization",
        "capital_allocation",
        "execution",
        "wallet",
        "rpc",
        "dex",
    ):
        assert not hasattr(analysis, name)

    with pytest.raises(TypeError):
        create_bounded_deep_analysis(_context(), action="BUY")


def test_analysis_absence_does_not_change_authoritative_t02_result():
    context = _context()
    authoritative = evaluate_decision_intent(context)
    assert evaluate_decision_intent(context).digest == authoritative.digest
    assert authoritative.action.value == "BUY"


def test_analysis_is_independent_of_wall_clock_and_timezone_canonicalizes():
    context = _context()
    local_time = context.reference_time.astimezone(timezone(timedelta(hours=7)))
    analysis = _analysis(analysis_time=local_time, validation_time=local_time)

    assert analysis.analysis_time == context.reference_time
    assert analysis.digest == _analysis().digest