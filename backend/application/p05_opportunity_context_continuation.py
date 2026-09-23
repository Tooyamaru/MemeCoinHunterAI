"""Deterministic P01-RTI-12 P05 opportunity-context continuation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any, Callable, Mapping

from backend.application.market_to_opportunity_composition import (
    P01_RTI_11_CONTRACT_VERSION,
    MarketToOpportunityCompositionOutcome,
    P01Rti11CompositionResult,
)
from core.opportunity.opportunity_context import (
    OpportunityContext,
    P05_T08_CONTRACT_VERSION,
    P05_T08_EVALUATOR_VERSION,
    materialize_opportunity_context,
)
from core.opportunity.opportunity_record import (
    OpportunityRecord,
    P05_T06_CONTRACT_VERSION,
    P05_T06_EVALUATOR_VERSION,
    materialize_opportunity_record,
)
from core.opportunity.opportunity_record_history import (
    OpportunityRecordHistory,
    OpportunityRecordHistoryOutcome,
    OpportunityRecordHistoryResult,
    P05_T07_CONTRACT_VERSION,
)


P01_RTI_12_CONTRACT_VERSION = "p01-rti-12-v1"


class OpportunityContextContinuationOutcome(StrEnum):
    CONTEXT_MATERIALIZED = "CONTEXT_MATERIALIZED"
    UPSTREAM_NOT_COMPOSED = "UPSTREAM_NOT_COMPOSED"
    MATERIALIZATION_UNAVAILABLE = "MATERIALIZATION_UNAVAILABLE"


@dataclass(frozen=True)
class P01Rti12ContinuationResult:
    """Immutable bounded result for one RTI-11 -> P05-T08 continuation."""

    upstream_result: P01Rti11CompositionResult
    outcome: OpportunityContextContinuationOutcome | str
    reason_codes: tuple[str, ...]
    record: OpportunityRecord | None = None
    history_result: OpportunityRecordHistoryResult | None = None
    history: OpportunityRecordHistory | None = None
    context: OpportunityContext | None = None
    contract_version: str = P01_RTI_12_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        _validate_upstream(self.upstream_result)
        try:
            outcome = OpportunityContextContinuationOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported RTI-12 outcome") from error
        object.__setattr__(self, "outcome", outcome)
        if self.contract_version != P01_RTI_12_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-12 contract_version")
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)

        if outcome is OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED:
            if self.upstream_result.outcome is not MarketToOpportunityCompositionOutcome.COMPOSED:
                raise ValueError("CONTEXT_MATERIALIZED requires COMPOSED upstream")
            if reasons:
                raise ValueError("CONTEXT_MATERIALIZED cannot contain reason codes")
            _validate_materialized_chain(
                upstream=self.upstream_result,
                record=self.record,
                history_result=self.history_result,
                history=self.history,
                context=self.context,
            )
        elif outcome is OpportunityContextContinuationOutcome.UPSTREAM_NOT_COMPOSED:
            if self.upstream_result.outcome is MarketToOpportunityCompositionOutcome.COMPOSED:
                raise ValueError("UPSTREAM_NOT_COMPOSED requires non-COMPOSED upstream")
            if not reasons:
                raise ValueError("UPSTREAM_NOT_COMPOSED requires a reason code")
            if any(
                value is not None
                for value in (self.record, self.history_result, self.history, self.context)
            ):
                raise ValueError("UPSTREAM_NOT_COMPOSED cannot contain P05 materialization")
        else:
            if self.upstream_result.outcome is not MarketToOpportunityCompositionOutcome.COMPOSED:
                raise ValueError(
                    "MATERIALIZATION_UNAVAILABLE requires COMPOSED upstream"
                )
            if not reasons:
                raise ValueError("MATERIALIZATION_UNAVAILABLE requires a reason code")
            _validate_partial_materialization(
                record=self.record,
                history_result=self.history_result,
                history=self.history,
                context=self.context,
            )

        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match RTI-12 result")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "upstream_contract_version": self.upstream_result.contract_version,
            "upstream_outcome": self.upstream_result.outcome.value,
            "upstream_result_digest": self.upstream_result.result_digest,
            "record_contract_version": (
                self.record.contract_version if self.record is not None else None
            ),
            "record_digest": self.record.digest if self.record is not None else None,
            "history_contract_version": (
                self.history_result.contract_version
                if self.history_result is not None
                else None
            ),
            "history_outcome": (
                self.history_result.outcome.value
                if self.history_result is not None
                else None
            ),
            "history_digest": (
                self.history_result.history_digest
                if self.history_result is not None
                else (self.history.digest if self.history is not None else None)
            ),
            "context_contract_version": (
                self.context.contract_version if self.context is not None else None
            ),
            "context_digest": (
                self.context.digest if self.context is not None else None
            ),
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


RecordMaterializer = Callable[[Any], OpportunityRecord]
HistoryFactory = Callable[[], OpportunityRecordHistory]
ContextMaterializer = Callable[[OpportunityRecord, OpportunityRecordHistory], OpportunityContext]


class P05OpportunityContextContinuationService:
    """Bounded local continuation from one canonical RTI-11 result to P05-T08."""

    def __init__(
        self,
        *,
        record_materializer: RecordMaterializer = materialize_opportunity_record,
        history_factory: HistoryFactory = OpportunityRecordHistory,
        context_materializer: ContextMaterializer = materialize_opportunity_context,
    ) -> None:
        for value, name in (
            (record_materializer, "record_materializer"),
            (history_factory, "history_factory"),
            (context_materializer, "context_materializer"),
        ):
            if not callable(value):
                raise ValueError(f"{name} must be callable")
        self._record_materializer = record_materializer
        self._history_factory = history_factory
        self._context_materializer = context_materializer

    def continue_to_context(
        self,
        upstream_result: P01Rti11CompositionResult,
    ) -> P01Rti12ContinuationResult:
        _validate_upstream(upstream_result)

        if upstream_result.outcome is not MarketToOpportunityCompositionOutcome.COMPOSED:
            return P01Rti12ContinuationResult(
                upstream_result=upstream_result,
                outcome=OpportunityContextContinuationOutcome.UPSTREAM_NOT_COMPOSED,
                reason_codes=("UPSTREAM_NOT_COMPOSED",),
            )

        composition = upstream_result.composition
        if composition is None:
            raise ValueError("RTI-11 COMPOSED result is missing composition")

        try:
            record = self._record_materializer(composition.score)
        except ValueError:
            raise ValueError("P05-T06 validation failed") from None
        except Exception:
            return _unavailable(
                upstream_result,
                "P05_T06_UNAVAILABLE",
            )
        if not _valid_record_output(record, composition.score):
            return _unavailable(
                upstream_result,
                "P05_T06_INVALID_RESULT",
            )

        try:
            history = self._history_factory()
        except Exception:
            return _unavailable(
                upstream_result,
                "P05_T07_HISTORY_UNAVAILABLE",
                record=record,
            )
        if not isinstance(history, OpportunityRecordHistory) or history.record_count != 0:
            return _unavailable(
                upstream_result,
                "P05_T07_INVALID_HISTORY",
                record=record,
            )

        try:
            history_result = history.append(record)
        except Exception:
            return _unavailable(
                upstream_result,
                "P05_T07_UNAVAILABLE",
                record=record,
                history=history,
            )
        if not isinstance(history_result, OpportunityRecordHistoryResult):
            return _unavailable(
                upstream_result,
                "P05_T07_INVALID_RESULT",
                record=record,
                history=history,
            )
        if history_result.outcome is OpportunityRecordHistoryOutcome.INVALID_INPUT:
            return _unavailable(
                upstream_result,
                "P05_T07_INVALID_INPUT",
                record=record,
                history_result=history_result,
                history=history,
            )
        if history_result.outcome is OpportunityRecordHistoryOutcome.DUPLICATE:
            return _unavailable(
                upstream_result,
                "P05_T07_DUPLICATE",
                record=record,
                history_result=history_result,
                history=history,
            )
        if not _valid_stored_history_result(history_result, history, record):
            return _unavailable(
                upstream_result,
                "P05_T07_INVALID_RESULT",
                record=record,
                history_result=history_result,
                history=history,
            )

        try:
            context = self._context_materializer(record, history)
        except ValueError:
            raise ValueError("P05-T08 validation failed") from None
        except Exception:
            return _unavailable(
                upstream_result,
                "P05_T08_UNAVAILABLE",
                record=record,
                history_result=history_result,
                history=history,
            )
        if not _valid_context_output(context, record, history):
            return _unavailable(
                upstream_result,
                "P05_T08_INVALID_RESULT",
                record=record,
                history_result=history_result,
                history=history,
            )

        return P01Rti12ContinuationResult(
            upstream_result=upstream_result,
            outcome=OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED,
            reason_codes=(),
            record=record,
            history_result=history_result,
            history=history,
            context=context,
        )

    materialize = continue_to_context


def _unavailable(
    upstream_result: P01Rti11CompositionResult,
    reason: str,
    *,
    record: OpportunityRecord | None = None,
    history_result: OpportunityRecordHistoryResult | None = None,
    history: OpportunityRecordHistory | None = None,
) -> P01Rti12ContinuationResult:
    return P01Rti12ContinuationResult(
        upstream_result=upstream_result,
        outcome=OpportunityContextContinuationOutcome.MATERIALIZATION_UNAVAILABLE,
        reason_codes=(reason,),
        record=record,
        history_result=history_result,
        history=history,
    )


def _validate_upstream(value: Any) -> None:
    if not isinstance(value, P01Rti11CompositionResult):
        raise ValueError("upstream_result must be a P01Rti11CompositionResult")
    if value.contract_version != P01_RTI_11_CONTRACT_VERSION:
        raise ValueError("unsupported RTI-11 contract version")
    try:
        validated = P01Rti11CompositionResult(
            request=value.request,
            outcome=value.outcome,
            reason_codes=value.reason_codes,
            diagnostic=value.diagnostic,
            composition=value.composition,
            contract_version=value.contract_version,
            result_digest=value.result_digest,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("upstream_result is not canonical") from error
    if validated != value or validated.result_digest != value.result_digest:
        raise ValueError("upstream_result is not canonical")


def _valid_record_output(record: Any, score: Any) -> bool:
    if not isinstance(record, OpportunityRecord):
        return False
    if (
        record.contract_version != P05_T06_CONTRACT_VERSION
        or record.evaluator_version != P05_T06_EVALUATOR_VERSION
        or record.opportunity_score is not score
        or record.input_score_digest != score.digest
    ):
        return False
    try:
        validated = OpportunityRecord(
            candidate_id=record.candidate_id,
            chain_id=record.chain_id,
            token_identity=record.token_identity,
            reference_time=record.reference_time,
            input_score_digest=record.input_score_digest,
            opportunity_score=record.opportunity_score,
            feature_evaluation=record.feature_evaluation,
            risk_evaluation=record.risk_evaluation,
            signal_snapshot=record.signal_snapshot,
            evaluator_version=record.evaluator_version,
            contract_version=record.contract_version,
        )
    except (AttributeError, TypeError, ValueError):
        return False
    return validated == record and validated.digest == record.digest


def _valid_stored_history_result(
    result: OpportunityRecordHistoryResult,
    history: OpportunityRecordHistory,
    record: OpportunityRecord,
) -> bool:
    return (
        result.contract_version == P05_T07_CONTRACT_VERSION
        and result.outcome is OpportunityRecordHistoryOutcome.STORED
        and result.accepted is True
        and result.reason_codes == ()
        and result.record is record
        and result.records == (record,)
        and history.record_count == 1
        and history.records == (record,)
        and any(item is record for item in history.records)
        and result.history_digest == history.digest
    )


def _valid_context_output(
    context: Any,
    record: OpportunityRecord,
    history: OpportunityRecordHistory,
) -> bool:
    if not isinstance(context, OpportunityContext):
        return False
    if (
        context.contract_version != P05_T08_CONTRACT_VERSION
        or context.evaluator_version != P05_T08_EVALUATOR_VERSION
        or context.opportunity_record is not record
        or context.record_history is not history
        or context.record_digest != record.digest
        or context.history_digest != history.digest
    ):
        return False
    try:
        validated = OpportunityContext(
            candidate_id=context.candidate_id,
            chain_id=context.chain_id,
            token_identity=context.token_identity,
            reference_time=context.reference_time,
            record_digest=context.record_digest,
            history_digest=context.history_digest,
            opportunity_record=context.opportunity_record,
            record_history=context.record_history,
            risk_evaluation=context.risk_evaluation,
            feature_evaluation=context.feature_evaluation,
            signal_snapshot=context.signal_snapshot,
            opportunity_score=context.opportunity_score,
            evaluator_version=context.evaluator_version,
            contract_version=context.contract_version,
        )
    except (AttributeError, TypeError, ValueError):
        return False
    return validated == context and validated.digest == context.digest


def _validate_materialized_chain(
    *,
    upstream: P01Rti11CompositionResult,
    record: OpportunityRecord | None,
    history_result: OpportunityRecordHistoryResult | None,
    history: OpportunityRecordHistory | None,
    context: OpportunityContext | None,
) -> None:
    if upstream.composition is None:
        raise ValueError("materialized result requires upstream composition")
    if not _valid_record_output(record, upstream.composition.score):
        raise ValueError("materialized record is invalid")
    if not isinstance(history, OpportunityRecordHistory):
        raise ValueError("materialized history is invalid")
    if not isinstance(history_result, OpportunityRecordHistoryResult) or not (
        _valid_stored_history_result(history_result, history, record)
    ):
        raise ValueError("materialized history result is invalid")
    if not _valid_context_output(context, record, history):
        raise ValueError("materialized context is invalid")


def _validate_partial_materialization(
    *,
    record: OpportunityRecord | None,
    history_result: OpportunityRecordHistoryResult | None,
    history: OpportunityRecordHistory | None,
    context: OpportunityContext | None,
) -> None:
    if context is not None:
        raise ValueError("unavailable result cannot contain context")
    if history_result is not None and history is None:
        raise ValueError("history_result requires history")
    if history is not None and record is None:
        raise ValueError("history requires record")


def _reason_codes(value: Any) -> tuple[str, ...]:
    if not isinstance(value, tuple) or any(
        not isinstance(item, str) or not item or item != item.strip()
        for item in value
    ):
        raise ValueError("reason_codes must be canonical non-empty tuple values")
    return tuple(sorted(set(value)))


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("canonical mapping keys must be strings")
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    raise ValueError(f"unsupported canonical value: {type(value).__name__}")


__all__ = [
    "P01_RTI_12_CONTRACT_VERSION",
    "OpportunityContextContinuationOutcome",
    "P01Rti12ContinuationResult",
    "P05OpportunityContextContinuationService",
]
