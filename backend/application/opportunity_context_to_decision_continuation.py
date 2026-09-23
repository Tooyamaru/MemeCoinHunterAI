"""Deterministic P01-RTI-13 OpportunityContext-to-Decision continuation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from typing import Any, Callable, Mapping

from backend.application.p05_opportunity_context_continuation import (
    P01_RTI_12_CONTRACT_VERSION,
    OpportunityContextContinuationOutcome,
    P01Rti12ContinuationResult,
)
from core.decision.decision_evaluation import (
    DecisionEvaluationRuleset,
    evaluate_decision_intent,
)
from core.decision.decision_intent import (
    DecisionIntent,
    P06_T01_CONTRACT_VERSION,
    P06_T02_EVALUATOR_VERSION,
    P06_T02_RULESET_VERSION,
)
from core.opportunity.opportunity_context import (
    P05_T08_CONTRACT_VERSION,
    P05_T08_EVALUATOR_VERSION,
)


P01_RTI_13_CONTRACT_VERSION = "p01-rti-13-v1"


class OpportunityContextToDecisionOutcome(StrEnum):
    DECISION_MATERIALIZED = "DECISION_MATERIALIZED"
    UPSTREAM_NOT_MATERIALIZED = "UPSTREAM_NOT_MATERIALIZED"
    DECISION_UNAVAILABLE = "DECISION_UNAVAILABLE"


@dataclass(frozen=True)
class P01Rti13DecisionContinuationResult:
    """Immutable bounded wrapper over one RTI-12 -> P06-T02 continuation."""

    upstream_result: P01Rti12ContinuationResult
    decision_ruleset: DecisionEvaluationRuleset
    decision_time: datetime
    outcome: OpportunityContextToDecisionOutcome | str
    reason_codes: tuple[str, ...]
    decision_intent: DecisionIntent | None = None
    contract_version: str = P01_RTI_13_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        _validate_upstream(self.upstream_result)
        _validate_ruleset(self.decision_ruleset)
        decision_time = _canonical_decision_time(
            self.decision_time,
            self.upstream_result,
        )
        object.__setattr__(self, "decision_time", decision_time)

        try:
            outcome = OpportunityContextToDecisionOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported RTI-13 outcome") from error
        object.__setattr__(self, "outcome", outcome)

        if self.contract_version != P01_RTI_13_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-13 contract_version")

        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)

        if outcome is OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED:
            if (
                self.upstream_result.outcome
                is not OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED
            ):
                raise ValueError(
                    "DECISION_MATERIALIZED requires CONTEXT_MATERIALIZED upstream"
                )
            if reasons:
                raise ValueError("DECISION_MATERIALIZED cannot contain reason codes")
            if not _valid_decision_output(
                self.decision_intent,
                self.upstream_result,
                self.decision_ruleset,
                decision_time,
            ):
                raise ValueError("materialized DecisionIntent is invalid")
        elif outcome is OpportunityContextToDecisionOutcome.UPSTREAM_NOT_MATERIALIZED:
            if (
                self.upstream_result.outcome
                is OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED
            ):
                raise ValueError(
                    "UPSTREAM_NOT_MATERIALIZED requires non-materialized upstream"
                )
            if not reasons:
                raise ValueError("UPSTREAM_NOT_MATERIALIZED requires a reason code")
            if self.decision_intent is not None:
                raise ValueError(
                    "UPSTREAM_NOT_MATERIALIZED cannot contain DecisionIntent"
                )
        else:
            if (
                self.upstream_result.outcome
                is not OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED
            ):
                raise ValueError(
                    "DECISION_UNAVAILABLE requires materialized upstream context"
                )
            if not reasons:
                raise ValueError("DECISION_UNAVAILABLE requires a reason code")
            if self.decision_intent is not None:
                raise ValueError("DECISION_UNAVAILABLE cannot contain DecisionIntent")

        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match RTI-13 result")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "upstream_contract_version": self.upstream_result.contract_version,
            "upstream_outcome": self.upstream_result.outcome.value,
            "upstream_result_digest": self.upstream_result.result_digest,
            "decision_ruleset_version": self.decision_ruleset.version,
            "decision_ruleset_digest": self.decision_ruleset.digest,
            "decision_time": self.decision_time.isoformat(),
            "decision_contract_version": (
                self.decision_intent.contract_version
                if self.decision_intent is not None
                else None
            ),
            "decision_ruleset_version_output": (
                self.decision_intent.ruleset_version
                if self.decision_intent is not None
                else None
            ),
            "decision_evaluator_version": (
                self.decision_intent.evaluator_version
                if self.decision_intent is not None
                else None
            ),
            "decision_digest": (
                self.decision_intent.digest
                if self.decision_intent is not None
                else None
            ),
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


DecisionEvaluator = Callable[..., DecisionIntent]


class OpportunityContextToDecisionContinuationService:
    """Bounded analytical continuation from RTI-12 to one P06-T01 intent."""

    def __init__(
        self,
        *,
        decision_evaluator: DecisionEvaluator = evaluate_decision_intent,
    ) -> None:
        if not callable(decision_evaluator):
            raise ValueError("decision_evaluator must be callable")
        self._decision_evaluator = decision_evaluator

    def continue_to_decision(
        self,
        upstream_result: P01Rti12ContinuationResult,
        decision_ruleset: DecisionEvaluationRuleset,
        decision_time: datetime,
    ) -> P01Rti13DecisionContinuationResult:
        _validate_upstream(upstream_result)
        _validate_ruleset(decision_ruleset)
        canonical_time = _canonical_decision_time(decision_time, upstream_result)

        if (
            upstream_result.outcome
            is not OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED
        ):
            return P01Rti13DecisionContinuationResult(
                upstream_result=upstream_result,
                decision_ruleset=decision_ruleset,
                decision_time=canonical_time,
                outcome=(
                    OpportunityContextToDecisionOutcome.UPSTREAM_NOT_MATERIALIZED
                ),
                reason_codes=("UPSTREAM_NOT_MATERIALIZED",),
            )

        context = upstream_result.context
        if context is None:
            raise ValueError(
                "RTI-12 CONTEXT_MATERIALIZED result is missing OpportunityContext"
            )
        if (
            context.contract_version != P05_T08_CONTRACT_VERSION
            or context.evaluator_version != P05_T08_EVALUATOR_VERSION
        ):
            raise ValueError("unsupported P05-T08 context version")

        try:
            decision = self._decision_evaluator(
                context,
                ruleset=decision_ruleset,
                decision_time=canonical_time,
            )
        except ValueError:
            raise ValueError("P06-T02 validation failed") from None
        except Exception:
            return P01Rti13DecisionContinuationResult(
                upstream_result=upstream_result,
                decision_ruleset=decision_ruleset,
                decision_time=canonical_time,
                outcome=OpportunityContextToDecisionOutcome.DECISION_UNAVAILABLE,
                reason_codes=("P06_T02_UNAVAILABLE",),
            )

        if not _valid_decision_output(
            decision,
            upstream_result,
            decision_ruleset,
            canonical_time,
        ):
            return P01Rti13DecisionContinuationResult(
                upstream_result=upstream_result,
                decision_ruleset=decision_ruleset,
                decision_time=canonical_time,
                outcome=OpportunityContextToDecisionOutcome.DECISION_UNAVAILABLE,
                reason_codes=("P06_T02_INVALID_RESULT",),
            )

        return P01Rti13DecisionContinuationResult(
            upstream_result=upstream_result,
            decision_ruleset=decision_ruleset,
            decision_time=canonical_time,
            outcome=OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED,
            reason_codes=(),
            decision_intent=decision,
        )

    materialize = continue_to_decision


def _validate_upstream(value: Any) -> None:
    if not isinstance(value, P01Rti12ContinuationResult):
        raise ValueError("upstream_result must be a P01Rti12ContinuationResult")
    if value.contract_version != P01_RTI_12_CONTRACT_VERSION:
        raise ValueError("unsupported RTI-12 contract version")
    try:
        validated = P01Rti12ContinuationResult(
            upstream_result=value.upstream_result,
            outcome=value.outcome,
            reason_codes=value.reason_codes,
            record=value.record,
            history_result=value.history_result,
            history=value.history,
            context=value.context,
            contract_version=value.contract_version,
            result_digest=value.result_digest,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("upstream_result is not canonical") from error
    if validated != value or validated.result_digest != value.result_digest:
        raise ValueError("upstream_result is not canonical")


def _validate_ruleset(value: Any) -> None:
    if not isinstance(value, DecisionEvaluationRuleset):
        raise ValueError("decision_ruleset must be a DecisionEvaluationRuleset")
    if value.version != P06_T02_RULESET_VERSION:
        raise ValueError("unsupported P06-T02 ruleset version")
    try:
        validated = DecisionEvaluationRuleset(
            buy_score_threshold=value.buy_score_threshold,
            watch_score_threshold=value.watch_score_threshold,
            max_evidence_age_seconds=value.max_evidence_age_seconds,
            version=value.version,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("decision_ruleset is invalid or unsupported") from error
    if (
        validated != value
        or validated.canonical_representation != value.canonical_representation
        or validated.digest != value.digest
    ):
        raise ValueError("decision_ruleset is not canonical")


def _canonical_decision_time(
    value: Any,
    upstream_result: P01Rti12ContinuationResult,
) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("decision_time must be timezone-aware datetime")
    canonical = value.astimezone(timezone.utc)
    context = upstream_result.context
    if context is not None and canonical < context.reference_time:
        raise ValueError("decision_time cannot precede reference_time")
    return canonical


def _valid_decision_output(
    value: Any,
    upstream_result: P01Rti12ContinuationResult,
    ruleset: DecisionEvaluationRuleset,
    decision_time: datetime,
) -> bool:
    if not isinstance(value, DecisionIntent):
        return False
    context = upstream_result.context
    if context is None:
        return False
    if (
        value.contract_version != P06_T01_CONTRACT_VERSION
        or value.ruleset_version != P06_T02_RULESET_VERSION
        or value.evaluator_version != P06_T02_EVALUATOR_VERSION
        or value.context is not context
        or value.context_digest != context.digest
        or value.candidate_id != context.candidate_id
        or value.chain_id != context.chain_id
        or value.token_identity != context.token_identity
        or value.decision_time != decision_time
        or ruleset.version != value.ruleset_version
    ):
        return False
    try:
        validated = DecisionIntent(
            context=value.context,
            action=value.action,
            entry_posture=value.entry_posture,
            expected_edge_assumptions=value.expected_edge_assumptions,
            uncertainty=value.uncertainty,
            invalidation_conditions=value.invalidation_conditions,
            confidence=value.confidence,
            decision_time=value.decision_time,
            ruleset_version=value.ruleset_version,
            evaluator_version=value.evaluator_version,
            contract_version=value.contract_version,
        )
    except (AttributeError, TypeError, ValueError):
        return False
    return (
        validated == value
        and validated.canonical_representation == value.canonical_representation
        and validated.deterministic_representation == value.deterministic_representation
        and validated.digest == value.digest
    )


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
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical datetime must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("canonical mapping keys must be strings")
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    raise ValueError(f"unsupported canonical value: {type(value).__name__}")


__all__ = [
    "P01_RTI_13_CONTRACT_VERSION",
    "OpportunityContextToDecisionOutcome",
    "P01Rti13DecisionContinuationResult",
    "OpportunityContextToDecisionContinuationService",
]
