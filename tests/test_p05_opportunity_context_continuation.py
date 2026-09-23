from dataclasses import replace
import ast
from pathlib import Path

import pytest

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionOutcome,
    MarketToOpportunityCompositionService,
    P01Rti11CompositionResult,
)
from backend.application.p05_opportunity_context_continuation import (
    P01_RTI_12_CONTRACT_VERSION,
    OpportunityContextContinuationOutcome,
    P05OpportunityContextContinuationService,
)
from core.data.coingecko_onchain_orchestration import (
    ControlledDiagnosticOutcome,
    ControlledDiagnosticResult,
)
from core.opportunity import (
    OpportunityRecordHistory,
    OpportunityRecordHistoryOutcome,
    OpportunityRecordHistoryResult,
    materialize_opportunity_context,
    materialize_opportunity_record,
)
from tests.test_coingecko_onchain_ohlcv import request as ohlcv_request
from tests.test_market_to_opportunity_composition import (
    _nested_failure,
    _produced,
    _request,
    _target,
)


def _composed():
    return MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: _produced(),
    ).compose(_request())


def _token_not_current():
    controlled = ControlledDiagnosticResult(
        outcome=ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT,
        reason_codes=("TOKEN_NOT_CURRENT",),
        target=_target(),
        request=ohlcv_request(),
    )
    return MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: controlled,
    ).compose(_request())


def _diagnostic_not_produced():
    controlled = _nested_failure()
    return MarketToOpportunityCompositionService(
        controlled_diagnostic=lambda **kwargs: controlled,
    ).compose(_request())


def _composition_unavailable():
    return P01Rti11CompositionResult(
        request=_request(),
        outcome=MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE,
        reason_codes=("CONTROLLED_DIAGNOSTIC_UNAVAILABLE",),
    )


def test_success_materializes_exact_t06_t07_t08_chain_once():
    upstream = _composed()
    record_calls = []
    context_calls = []
    histories = []

    def record_materializer(score):
        record_calls.append(score)
        return materialize_opportunity_record(score)

    def history_factory():
        history = OpportunityRecordHistory()
        histories.append(history)
        return history

    def context_materializer(record, history):
        context_calls.append((record, history))
        return materialize_opportunity_context(record, history)

    result = P05OpportunityContextContinuationService(
        record_materializer=record_materializer,
        history_factory=history_factory,
        context_materializer=context_materializer,
    ).continue_to_context(upstream)

    assert result.outcome is OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED
    assert result.contract_version == P01_RTI_12_CONTRACT_VERSION
    assert result.reason_codes == ()
    assert record_calls == [upstream.composition.score]
    assert len(histories) == 1
    assert histories[0] is result.history
    assert result.history.record_count == 1
    assert result.history.records == (result.record,)
    assert result.history_result.outcome is OpportunityRecordHistoryOutcome.STORED
    assert result.history_result.accepted is True
    assert result.history_result.reason_codes == ()
    assert result.history_result.record is result.record
    assert result.history_result.history_digest == result.history.digest
    assert context_calls == [(result.record, result.history)]
    assert result.context.opportunity_record is result.record
    assert result.context.record_history is result.history
    assert result.context.opportunity_score is upstream.composition.score
    assert len(result.result_digest) == 64


@pytest.mark.parametrize(
    "factory",
    [_token_not_current, _diagnostic_not_produced, _composition_unavailable],
)
def test_all_valid_non_composed_outcomes_stop_before_p05_owners(factory):
    upstream = factory()
    calls = {"record": 0, "history": 0, "context": 0}

    def record_materializer(score):
        calls["record"] += 1
        raise AssertionError("P05-T06 must not run")

    def history_factory():
        calls["history"] += 1
        raise AssertionError("P05-T07 must not run")

    def context_materializer(record, history):
        calls["context"] += 1
        raise AssertionError("P05-T08 must not run")

    result = P05OpportunityContextContinuationService(
        record_materializer=record_materializer,
        history_factory=history_factory,
        context_materializer=context_materializer,
    ).continue_to_context(upstream)

    assert result.outcome is OpportunityContextContinuationOutcome.UPSTREAM_NOT_COMPOSED
    assert result.reason_codes == ("UPSTREAM_NOT_COMPOSED",)
    assert result.upstream_result is upstream
    assert result.upstream_result.result_digest == upstream.result_digest
    assert result.record is None
    assert result.history_result is None
    assert result.history is None
    assert result.context is None
    assert calls == {"record": 0, "history": 0, "context": 0}


@pytest.mark.parametrize("invalid", [None, object(), "upstream"])
def test_invalid_upstream_type_is_validation_failure(invalid):
    with pytest.raises(ValueError, match="P01Rti11CompositionResult"):
        P05OpportunityContextContinuationService().continue_to_context(invalid)


def test_tampered_upstream_digest_is_validation_failure():
    upstream = _composed()
    object.__setattr__(upstream, "result_digest", "0" * 64)

    with pytest.raises(ValueError, match="canonical"):
        P05OpportunityContextContinuationService().continue_to_context(upstream)


def test_t06_value_error_remains_safe_validation_failure():
    upstream = _composed()

    def invalid(score):
        raise ValueError("private owner detail")

    with pytest.raises(ValueError, match=r"^P05-T06 validation failed$"):
        P05OpportunityContextContinuationService(
            record_materializer=invalid,
        ).continue_to_context(upstream)


def test_t08_value_error_remains_safe_validation_failure():
    upstream = _composed()

    def invalid(record, history):
        raise ValueError("private owner detail")

    with pytest.raises(ValueError, match=r"^P05-T08 validation failed$"):
        P05OpportunityContextContinuationService(
            context_materializer=invalid,
        ).continue_to_context(upstream)


@pytest.mark.parametrize(
    ("owner", "reason"),
    [
        (
            {"record_materializer": lambda score: (_ for _ in ()).throw(RuntimeError("secret"))},
            "P05_T06_UNAVAILABLE",
        ),
        (
            {"history_factory": lambda: (_ for _ in ()).throw(RuntimeError("secret"))},
            "P05_T07_HISTORY_UNAVAILABLE",
        ),
        (
            {"context_materializer": lambda record, history: (_ for _ in ()).throw(RuntimeError("secret"))},
            "P05_T08_UNAVAILABLE",
        ),
    ],
)
def test_unexpected_owner_failures_are_bounded_and_safe(owner, reason):
    result = P05OpportunityContextContinuationService(
        **owner,
    ).continue_to_context(_composed())

    assert result.outcome is OpportunityContextContinuationOutcome.MATERIALIZATION_UNAVAILABLE
    assert result.reason_codes == (reason,)
    assert "secret" not in str(result.canonical_representation)


def test_invalid_t06_owner_output_is_bounded():
    result = P05OpportunityContextContinuationService(
        record_materializer=lambda score: object(),
    ).continue_to_context(_composed())

    assert result.outcome is OpportunityContextContinuationOutcome.MATERIALIZATION_UNAVAILABLE
    assert result.reason_codes == ("P05_T06_INVALID_RESULT",)
    assert result.history is None
    assert result.context is None


class _BoundedFailureHistory(OpportunityRecordHistory):
    def __init__(self, outcome):
        super().__init__()
        self._outcome = outcome

    def append(self, record):
        if self._outcome is OpportunityRecordHistoryOutcome.INVALID_INPUT:
            return OpportunityRecordHistoryResult(
                outcome=self._outcome,
                accepted=False,
                record=None,
                records=(),
                reason_codes=("INVALID_RECORD",),
                history_digest=self.digest,
            )
        return OpportunityRecordHistoryResult(
            outcome=self._outcome,
            accepted=False,
            record=record,
            records=(),
            reason_codes=("RECORD_ALREADY_STORED",),
            history_digest=self.digest,
        )


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        (OpportunityRecordHistoryOutcome.INVALID_INPUT, "P05_T07_INVALID_INPUT"),
        (OpportunityRecordHistoryOutcome.DUPLICATE, "P05_T07_DUPLICATE"),
    ],
)
def test_t07_bounded_owner_failures_remain_distinguishable(outcome, reason):
    result = P05OpportunityContextContinuationService(
        history_factory=lambda: _BoundedFailureHistory(outcome),
    ).continue_to_context(_composed())

    assert result.outcome is OpportunityContextContinuationOutcome.MATERIALIZATION_UNAVAILABLE
    assert result.reason_codes == (reason,)
    assert result.history_result.outcome is outcome
    assert result.context is None


class _InvalidStoredHistory(OpportunityRecordHistory):
    def append(self, record):
        return OpportunityRecordHistoryResult(
            outcome=OpportunityRecordHistoryOutcome.STORED,
            accepted=True,
            record=record,
            records=(record,),
            reason_codes=(),
            history_digest=self.digest,
        )


def test_invalid_t07_stored_output_is_rejected_without_t08():
    context_calls = 0

    def context_materializer(record, history):
        nonlocal context_calls
        context_calls += 1
        raise AssertionError("P05-T08 must not run")

    result = P05OpportunityContextContinuationService(
        history_factory=_InvalidStoredHistory,
        context_materializer=context_materializer,
    ).continue_to_context(_composed())

    assert result.outcome is OpportunityContextContinuationOutcome.MATERIALIZATION_UNAVAILABLE
    assert result.reason_codes == ("P05_T07_INVALID_RESULT",)
    assert context_calls == 0


def test_invalid_t08_owner_output_is_bounded():
    result = P05OpportunityContextContinuationService(
        context_materializer=lambda record, history: object(),
    ).continue_to_context(_composed())

    assert result.outcome is OpportunityContextContinuationOutcome.MATERIALIZATION_UNAVAILABLE
    assert result.reason_codes == ("P05_T08_INVALID_RESULT",)


def test_repeated_equivalent_invocations_use_fresh_history_with_same_digests():
    upstream = _composed()
    service = P05OpportunityContextContinuationService()

    first = service.continue_to_context(upstream)
    second = service.continue_to_context(upstream)

    assert first.history is not second.history
    assert first.context is not second.context
    assert first.record is not second.record
    assert first.history.digest == second.history.digest
    assert first.record.digest == second.record.digest
    assert first.context.digest == second.context.digest
    assert first.result_digest == second.result_digest
    assert not hasattr(service, "_history")


def test_digest_changes_with_bounded_outcome_and_excludes_exception_details():
    upstream = _composed()
    success = P05OpportunityContextContinuationService().continue_to_context(upstream)
    unavailable = P05OpportunityContextContinuationService(
        record_materializer=lambda score: (_ for _ in ()).throw(RuntimeError("private-a")),
    ).continue_to_context(upstream)
    unavailable_again = P05OpportunityContextContinuationService(
        record_materializer=lambda score: (_ for _ in ()).throw(RuntimeError("private-b")),
    ).continue_to_context(upstream)

    assert success.result_digest != unavailable.result_digest
    assert unavailable.result_digest == unavailable_again.result_digest
    assert "private-a" not in str(unavailable.canonical_representation)
    assert "private-b" not in str(unavailable_again.canonical_representation)


def test_forbidden_runtime_boundaries_are_not_imported():
    path = Path("backend/application/p05_opportunity_context_continuation.py")
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
        "core.risk.capital",
    )
    assert not any(
        module.startswith(prefix)
        for module in modules
        for prefix in forbidden_prefixes
    )
