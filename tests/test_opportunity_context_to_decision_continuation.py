from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import ast

import pytest

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionOutcome,
    P01Rti11CompositionResult,
)
from backend.application.p05_opportunity_context_continuation import (
    OpportunityContextContinuationOutcome,
    P05OpportunityContextContinuationService,
)
from backend.application.opportunity_context_to_decision_continuation import (
    P01_RTI_13_CONTRACT_VERSION,
    OpportunityContextToDecisionContinuationService,
    OpportunityContextToDecisionOutcome,
)
from core.decision import (
    DecisionAction,
    DecisionEvaluationRuleset,
    P06_T02_EVALUATOR_VERSION,
    P06_T02_RULESET_VERSION,
    create_decision_intent,
    evaluate_decision_intent,
)
from core.opportunity import materialize_opportunity_context
from tests.test_market_to_opportunity_composition import _request
from tests.test_p05_opportunity_context_continuation import _composed


def _materialized():
    return P05OpportunityContextContinuationService().continue_to_context(_composed())


def _not_materialized():
    rti11 = P01Rti11CompositionResult(
        request=_request(),
        outcome=MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE,
        reason_codes=("CONTROLLED_DIAGNOSTIC_UNAVAILABLE",),
    )
    return P05OpportunityContextContinuationService().continue_to_context(rti11)


def _ruleset():
    return DecisionEvaluationRuleset()


def test_exact_success_calls_p06_once_and_preserves_context_identity():
    upstream = _materialized()
    ruleset = _ruleset()
    decision_time = upstream.context.reference_time
    calls = []

    def evaluator(context, *, ruleset, decision_time):
        calls.append((context, ruleset, decision_time))
        return evaluate_decision_intent(
            context,
            ruleset=ruleset,
            decision_time=decision_time,
        )

    result = OpportunityContextToDecisionContinuationService(
        decision_evaluator=evaluator,
    ).continue_to_decision(upstream, ruleset, decision_time)

    assert result.outcome is OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED
    assert result.contract_version == P01_RTI_13_CONTRACT_VERSION
    assert result.reason_codes == ()
    assert len(calls) == 1
    assert calls[0][0] is upstream.context
    assert calls[0][1] is ruleset
    assert calls[0][2] == decision_time
    assert result.upstream_result is upstream
    assert result.decision_ruleset is ruleset
    assert result.decision_intent.context is upstream.context
    assert result.decision_intent.ruleset_version == P06_T02_RULESET_VERSION
    assert result.decision_intent.evaluator_version == P06_T02_EVALUATOR_VERSION
    assert result.decision_intent.is_authorization is False
    assert result.decision_intent.is_order is False
    assert len(result.result_digest) == 64


def test_non_materialized_upstream_stops_before_p06():
    upstream = _not_materialized()
    assert upstream.outcome is OpportunityContextContinuationOutcome.UPSTREAM_NOT_COMPOSED
    calls = 0

    def evaluator(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("P06-T02 must not run")

    result = OpportunityContextToDecisionContinuationService(
        decision_evaluator=evaluator,
    ).continue_to_decision(
        upstream,
        _ruleset(),
        _request().reference_time,
    )

    assert result.outcome is OpportunityContextToDecisionOutcome.UPSTREAM_NOT_MATERIALIZED
    assert result.reason_codes == ("UPSTREAM_NOT_MATERIALIZED",)
    assert result.upstream_result is upstream
    assert result.decision_intent is None
    assert calls == 0


def test_materialization_unavailable_upstream_also_stops_before_p06():
    composed = _composed()
    upstream = P05OpportunityContextContinuationService(
        record_materializer=lambda score: object(),
    ).continue_to_context(composed)
    assert upstream.outcome is OpportunityContextContinuationOutcome.MATERIALIZATION_UNAVAILABLE

    result = OpportunityContextToDecisionContinuationService(
        decision_evaluator=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("P06-T02 must not run")
        ),
    ).continue_to_decision(upstream, _ruleset(), composed.request.reference_time)

    assert result.outcome is OpportunityContextToDecisionOutcome.UPSTREAM_NOT_MATERIALIZED
    assert result.decision_intent is None


@pytest.mark.parametrize("invalid", [None, object(), "upstream"])
def test_invalid_upstream_type_is_validation_failure(invalid):
    with pytest.raises(ValueError, match="P01Rti12ContinuationResult"):
        OpportunityContextToDecisionContinuationService().continue_to_decision(
            invalid,
            _ruleset(),
            _request().reference_time,
        )


def test_tampered_upstream_digest_is_validation_failure_before_p06():
    upstream = _materialized()
    object.__setattr__(upstream, "result_digest", "0" * 64)
    calls = 0

    def evaluator(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("must not run")

    with pytest.raises(ValueError, match="canonical"):
        OpportunityContextToDecisionContinuationService(
            decision_evaluator=evaluator,
        ).continue_to_decision(
            upstream,
            _ruleset(),
            upstream.context.reference_time,
        )
    assert calls == 0


@pytest.mark.parametrize("invalid", [None, object(), "ruleset"])
def test_invalid_ruleset_type_is_validation_failure(invalid):
    upstream = _materialized()
    with pytest.raises(ValueError, match="DecisionEvaluationRuleset"):
        OpportunityContextToDecisionContinuationService().continue_to_decision(
            upstream,
            invalid,
            upstream.context.reference_time,
        )


def test_tampered_ruleset_is_validation_failure_before_p06():
    upstream = _materialized()
    ruleset = _ruleset()
    object.__setattr__(ruleset, "buy_score_threshold", ruleset.watch_score_threshold)
    calls = 0

    def evaluator(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("must not run")

    with pytest.raises(ValueError, match="canonical"):
        OpportunityContextToDecisionContinuationService(
            decision_evaluator=evaluator,
        ).continue_to_decision(upstream, ruleset, upstream.context.reference_time)
    assert calls == 0


def test_decision_time_must_be_explicit_aware_and_not_precede_context():
    upstream = _materialized()
    ruleset = _ruleset()

    with pytest.raises(ValueError, match="timezone-aware"):
        OpportunityContextToDecisionContinuationService().continue_to_decision(
            upstream,
            ruleset,
            upstream.context.reference_time.replace(tzinfo=None),
        )

    with pytest.raises(ValueError, match="precede"):
        OpportunityContextToDecisionContinuationService().continue_to_decision(
            upstream,
            ruleset,
            upstream.context.reference_time - timedelta(seconds=1),
        )


def test_p06_value_error_remains_safe_validation_failure():
    upstream = _materialized()

    def evaluator(*args, **kwargs):
        raise ValueError("private owner detail")

    with pytest.raises(ValueError, match=r"^P06-T02 validation failed$"):
        OpportunityContextToDecisionContinuationService(
            decision_evaluator=evaluator,
        ).continue_to_decision(
            upstream,
            _ruleset(),
            upstream.context.reference_time,
        )


def test_unexpected_p06_failure_is_safe_bounded_unavailable():
    upstream = _materialized()

    def evaluator(*args, **kwargs):
        raise RuntimeError("private owner detail")

    result = OpportunityContextToDecisionContinuationService(
        decision_evaluator=evaluator,
    ).continue_to_decision(
        upstream,
        _ruleset(),
        upstream.context.reference_time,
    )

    assert result.outcome is OpportunityContextToDecisionOutcome.DECISION_UNAVAILABLE
    assert result.reason_codes == ("P06_T02_UNAVAILABLE",)
    assert result.decision_intent is None
    assert "private owner detail" not in str(result.canonical_representation)


def test_invalid_p06_type_is_safe_bounded_unavailable():
    upstream = _materialized()

    result = OpportunityContextToDecisionContinuationService(
        decision_evaluator=lambda *args, **kwargs: object(),
    ).continue_to_decision(
        upstream,
        _ruleset(),
        upstream.context.reference_time,
    )

    assert result.outcome is OpportunityContextToDecisionOutcome.DECISION_UNAVAILABLE
    assert result.reason_codes == ("P06_T02_INVALID_RESULT",)


def test_equivalent_but_not_identical_context_from_owner_is_rejected():
    upstream = _materialized()
    context = upstream.context
    equivalent = materialize_opportunity_context(
        context.opportunity_record,
        context.record_history,
    )
    assert equivalent == context
    assert equivalent is not context

    def evaluator(*args, **kwargs):
        return create_decision_intent(
            equivalent,
            action=DecisionAction.BUY,
            decision_time=context.reference_time,
            ruleset_version=P06_T02_RULESET_VERSION,
            evaluator_version=P06_T02_EVALUATOR_VERSION,
        )

    result = OpportunityContextToDecisionContinuationService(
        decision_evaluator=evaluator,
    ).continue_to_decision(
        upstream,
        _ruleset(),
        context.reference_time,
    )

    assert result.outcome is OpportunityContextToDecisionOutcome.DECISION_UNAVAILABLE
    assert result.reason_codes == ("P06_T02_INVALID_RESULT",)


@pytest.mark.parametrize("action", tuple(DecisionAction))
def test_wrapper_does_not_reinterpret_valid_owner_actions(action):
    upstream = _materialized()
    context = upstream.context
    ruleset = _ruleset()

    def evaluator(*args, **kwargs):
        return create_decision_intent(
            context,
            action=action,
            decision_time=context.reference_time,
            ruleset_version=P06_T02_RULESET_VERSION,
            evaluator_version=P06_T02_EVALUATOR_VERSION,
        )

    result = OpportunityContextToDecisionContinuationService(
        decision_evaluator=evaluator,
    ).continue_to_decision(upstream, ruleset, context.reference_time)

    assert result.outcome is OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED
    assert result.decision_intent.action is action


def test_identical_inputs_are_deterministic_and_do_not_use_hidden_defaults():
    upstream = _materialized()
    ruleset = _ruleset()
    decision_time = upstream.context.reference_time

    first = OpportunityContextToDecisionContinuationService().continue_to_decision(
        upstream,
        ruleset,
        decision_time,
    )
    second = OpportunityContextToDecisionContinuationService().continue_to_decision(
        upstream,
        ruleset,
        decision_time,
    )

    assert first.result_digest == second.result_digest
    assert first.canonical_representation == second.canonical_representation
    assert first.decision_time == decision_time
    assert first.decision_ruleset is ruleset


def test_digest_excludes_exception_details():
    upstream = _materialized()
    ruleset = _ruleset()
    decision_time = upstream.context.reference_time

    def fail_a(*args, **kwargs):
        raise RuntimeError("private-a")

    def fail_b(*args, **kwargs):
        raise RuntimeError("private-b")

    first = OpportunityContextToDecisionContinuationService(
        decision_evaluator=fail_a,
    ).continue_to_decision(upstream, ruleset, decision_time)
    second = OpportunityContextToDecisionContinuationService(
        decision_evaluator=fail_b,
    ).continue_to_decision(upstream, ruleset, decision_time)

    assert first.result_digest == second.result_digest
    assert "private-a" not in str(first.canonical_representation)
    assert "private-b" not in str(second.canonical_representation)


def test_forbidden_downstream_authority_modules_are_not_imported():
    path = Path("backend/application/opportunity_context_to_decision_continuation.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    forbidden_prefixes = (
        "fastapi",
        "backend.api",
        "backend.core.database",
        "backend.core.models",
        "backend.core.repositories",
        "core.execution",
        "core.runtime",
        "core.risk.paper_risk_capital_authorization",
    )
    assert not any(
        module.startswith(prefix)
        for module in modules
        for prefix in forbidden_prefixes
    )
