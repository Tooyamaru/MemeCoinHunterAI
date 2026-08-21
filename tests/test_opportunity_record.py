from dataclasses import FrozenInstanceError, replace

import pytest

from core.opportunity import (
    OpportunityRecord,
    P05_T06_CONTRACT_VERSION,
    P05_T06_EVALUATOR_VERSION,
    create_opportunity_record,
    materialize_opportunity_record,
)
from tests.test_opportunity_score import _evaluation


def test_materializes_one_score_and_preserves_complete_provenance():
    score = __import__(
        "core.opportunity",
        fromlist=["evaluate_opportunity_score"],
    ).evaluate_opportunity_score(_evaluation())

    record = materialize_opportunity_record(score)

    assert isinstance(record, OpportunityRecord)
    assert record.opportunity_score is score
    assert record.input_score_digest == score.digest
    assert record.candidate_id == score.candidate_id
    assert record.reference_time == score.reference_time
    assert record.feature_evaluation is score.feature_evaluation
    assert record.risk_evaluation is score.feature_evaluation.risk_evaluation
    assert record.signal_snapshot is score.feature_evaluation.signal_snapshot
    assert record.contract_version == P05_T06_CONTRACT_VERSION
    assert record.evaluator_version == P05_T06_EVALUATOR_VERSION


def test_alias_is_deterministic_and_preserves_nested_score():
    from core.opportunity import evaluate_opportunity_score

    score = evaluate_opportunity_score(_evaluation())
    first = create_opportunity_record(score)
    second = create_opportunity_record(score)

    assert first == second
    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest
    assert first.opportunity_score is score


@pytest.mark.parametrize("invalid", [None, object(), "score"])
def test_invalid_input_fails_closed(invalid):
    with pytest.raises(ValueError, match="OpportunityScore"):
        materialize_opportunity_record(invalid)


def test_tampered_score_digest_and_identity_fail_closed():
    score = __import__(
        "core.opportunity",
        fromlist=["evaluate_opportunity_score"],
    ).evaluate_opportunity_score(_evaluation())

    with pytest.raises(ValueError):
        materialize_opportunity_record(
            replace(score, score=score.score + score.price_velocity)
        )


def test_direct_record_construction_rejects_mismatched_identity():
    from core.opportunity import evaluate_opportunity_score

    score = evaluate_opportunity_score(_evaluation())

    with pytest.raises(ValueError, match="identity"):
        OpportunityRecord(
            candidate_id="different-candidate",
            chain_id=score.chain_id,
            token_identity=score.token_identity,
            reference_time=score.reference_time,
            input_score_digest=score.digest,
            opportunity_score=score,
        )


def test_record_is_immutable_and_has_no_action_or_ranking_fields():
    from core.opportunity import evaluate_opportunity_score

    record = materialize_opportunity_record(evaluate_opportunity_score(_evaluation()))

    with pytest.raises(FrozenInstanceError):
        record.candidate_id = "changed"
    assert not hasattr(record, "ranking")
    assert not hasattr(record, "decision")
    assert not hasattr(record, "action")
    assert not hasattr(record, "authorization")


def test_tampered_nested_score_provenance_fails_closed():
    from core.opportunity import evaluate_opportunity_score

    score = evaluate_opportunity_score(_evaluation())
    tampered = replace(score.feature_evaluation)
    object.__setattr__(tampered, "input_candidate_digest", "tampered")
    object.__setattr__(score, "feature_evaluation", tampered)

    with pytest.raises(ValueError):
        materialize_opportunity_record(score)


def test_unsupported_extra_feature_identity_fails_closed():
    from dataclasses import replace
    from core.opportunity import evaluate_opportunity_score

    score = evaluate_opportunity_score(_evaluation())
    tampered_evaluation = replace(score.feature_evaluation)
    extra = replace(tampered_evaluation.feature_snapshots[0])
    object.__setattr__(extra, "feature_id", "unsupported_feature")
    object.__setattr__(
        tampered_evaluation,
        "feature_snapshots",
        (*tampered_evaluation.feature_snapshots, extra),
    )
    object.__setattr__(score, "feature_evaluation", tampered_evaluation)

    with pytest.raises(ValueError):
        materialize_opportunity_record(score)