"""Deterministic P01-RTI-14 Decision-to-Risk/Capital continuation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any, Callable, Mapping

from backend.application.opportunity_context_to_decision_continuation import (
    P01_RTI_13_CONTRACT_VERSION,
    OpportunityContextToDecisionOutcome,
    P01Rti13DecisionContinuationResult,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY,
    P08_AUTHORITY_CONTRACT_VERSION,
    P08_AUTHORITY_EVALUATOR_VERSION,
    P08_POLICY_CONTRACT_VERSION,
    PaperRiskCapitalAuthorizationResult,
    PaperRiskCapitalPolicySnapshot,
    evaluate_paper_risk_capital_authorization,
)


P01_RTI_14_CONTRACT_VERSION = "p01-rti-14-v1"


class DecisionToRiskCapitalOutcome(StrEnum):
    AUTHORIZATION_MATERIALIZED = "AUTHORIZATION_MATERIALIZED"
    UPSTREAM_NOT_DECIDED = "UPSTREAM_NOT_DECIDED"
    AUTHORIZATION_UNAVAILABLE = "AUTHORIZATION_UNAVAILABLE"


@dataclass(frozen=True)
class P01Rti14RiskCapitalContinuationResult:
    """Immutable wrapper over one RTI-13 -> paper Risk/Capital continuation."""

    upstream_result: P01Rti13DecisionContinuationResult
    policy_snapshot: PaperRiskCapitalPolicySnapshot
    outcome: DecisionToRiskCapitalOutcome | str
    reason_codes: tuple[str, ...]
    authorization_result: PaperRiskCapitalAuthorizationResult | None = None
    contract_version: str = P01_RTI_14_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        _validate_upstream(self.upstream_result)
        _validate_policy(self.policy_snapshot, self.upstream_result)

        try:
            outcome = DecisionToRiskCapitalOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported RTI-14 outcome") from error
        object.__setattr__(self, "outcome", outcome)

        if self.contract_version != P01_RTI_14_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-14 contract_version")
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)

        if outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED:
            if (
                self.upstream_result.outcome
                is not OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED
            ):
                raise ValueError(
                    "AUTHORIZATION_MATERIALIZED requires DECISION_MATERIALIZED upstream"
                )
            if reasons:
                raise ValueError(
                    "AUTHORIZATION_MATERIALIZED cannot contain wrapper reason codes"
                )
            if not _valid_authorization_result(
                self.authorization_result,
                self.upstream_result,
                self.policy_snapshot,
            ):
                raise ValueError("materialized Risk/Capital result is invalid")
        elif outcome is DecisionToRiskCapitalOutcome.UPSTREAM_NOT_DECIDED:
            if (
                self.upstream_result.outcome
                is OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED
            ):
                raise ValueError(
                    "UPSTREAM_NOT_DECIDED requires non-materialized RTI-13 decision"
                )
            if reasons != ("UPSTREAM_NOT_DECIDED",):
                raise ValueError(
                    "UPSTREAM_NOT_DECIDED requires its canonical reason code"
                )
            if self.authorization_result is not None:
                raise ValueError(
                    "UPSTREAM_NOT_DECIDED cannot contain authorization result"
                )
        else:
            if (
                self.upstream_result.outcome
                is not OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED
            ):
                raise ValueError(
                    "AUTHORIZATION_UNAVAILABLE requires DECISION_MATERIALIZED upstream"
                )
            if reasons not in (
                ("RISK_CAPITAL_UNAVAILABLE",),
                ("RISK_CAPITAL_INVALID_RESULT",),
            ):
                raise ValueError(
                    "AUTHORIZATION_UNAVAILABLE requires a canonical reason code"
                )
            if self.authorization_result is not None:
                raise ValueError(
                    "AUTHORIZATION_UNAVAILABLE cannot contain authorization result"
                )

        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match RTI-14 result")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> Mapping[str, Any]:
        authority = self.authorization_result
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "rti13_contract_version": self.upstream_result.contract_version,
            "rti13_outcome": self.upstream_result.outcome.value,
            "rti13_result_digest": self.upstream_result.result_digest,
            "policy_contract_version": self.policy_snapshot.contract_version,
            "policy_evaluator_version": self.policy_snapshot.evaluator_version,
            "policy_snapshot_id": self.policy_snapshot.policy_snapshot_id,
            "policy_snapshot_digest": self.policy_snapshot.digest,
            "authority_contract_version": (
                authority.contract_version if authority is not None else None
            ),
            "authority_evaluator_version": (
                authority.evaluator_version if authority is not None else None
            ),
            "authority_status": (
                authority.status.value if authority is not None else None
            ),
            "authorization_effect": (
                authority.authorization_effect if authority is not None else None
            ),
            "authorization_id": (
                authority.authorization_id if authority is not None else None
            ),
            "authority_result_digest": (
                authority.digest if authority is not None else None
            ),
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


RiskCapitalEvaluator = Callable[
    [Any, PaperRiskCapitalPolicySnapshot],
    PaperRiskCapitalAuthorizationResult,
]


class DecisionToRiskCapitalContinuationService:
    """Bounded paper-only continuation from RTI-13 to Risk/Capital authority."""

    def __init__(
        self,
        *,
        risk_capital_evaluator: RiskCapitalEvaluator = (
            evaluate_paper_risk_capital_authorization
        ),
    ) -> None:
        if not callable(risk_capital_evaluator):
            raise ValueError("risk_capital_evaluator must be callable")
        self._risk_capital_evaluator = risk_capital_evaluator

    def continue_to_risk_capital(
        self,
        upstream_result: P01Rti13DecisionContinuationResult,
        policy_snapshot: PaperRiskCapitalPolicySnapshot,
    ) -> P01Rti14RiskCapitalContinuationResult:
        _validate_upstream(upstream_result)
        _validate_policy(policy_snapshot, upstream_result)

        if (
            upstream_result.outcome
            is not OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED
        ):
            return P01Rti14RiskCapitalContinuationResult(
                upstream_result=upstream_result,
                policy_snapshot=policy_snapshot,
                outcome=DecisionToRiskCapitalOutcome.UPSTREAM_NOT_DECIDED,
                reason_codes=("UPSTREAM_NOT_DECIDED",),
            )

        decision = upstream_result.decision_intent
        if decision is None:
            raise ValueError(
                "RTI-13 DECISION_MATERIALIZED result is missing DecisionIntent"
            )

        try:
            authorization = self._risk_capital_evaluator(
                decision,
                policy_snapshot,
            )
        except ValueError:
            raise ValueError("Risk/Capital authority validation failed") from None
        except Exception:
            return P01Rti14RiskCapitalContinuationResult(
                upstream_result=upstream_result,
                policy_snapshot=policy_snapshot,
                outcome=DecisionToRiskCapitalOutcome.AUTHORIZATION_UNAVAILABLE,
                reason_codes=("RISK_CAPITAL_UNAVAILABLE",),
            )

        if not _valid_authorization_result(
            authorization,
            upstream_result,
            policy_snapshot,
        ):
            return P01Rti14RiskCapitalContinuationResult(
                upstream_result=upstream_result,
                policy_snapshot=policy_snapshot,
                outcome=DecisionToRiskCapitalOutcome.AUTHORIZATION_UNAVAILABLE,
                reason_codes=("RISK_CAPITAL_INVALID_RESULT",),
            )

        return P01Rti14RiskCapitalContinuationResult(
            upstream_result=upstream_result,
            policy_snapshot=policy_snapshot,
            outcome=DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED,
            reason_codes=(),
            authorization_result=authorization,
        )

    materialize = continue_to_risk_capital


def _validate_upstream(value: Any) -> None:
    if not isinstance(value, P01Rti13DecisionContinuationResult):
        raise ValueError(
            "upstream_result must be a P01Rti13DecisionContinuationResult"
        )
    if value.contract_version != P01_RTI_13_CONTRACT_VERSION:
        raise ValueError("unsupported RTI-13 contract version")
    try:
        validated = P01Rti13DecisionContinuationResult(
            upstream_result=value.upstream_result,
            decision_ruleset=value.decision_ruleset,
            decision_time=value.decision_time,
            outcome=value.outcome,
            reason_codes=value.reason_codes,
            decision_intent=value.decision_intent,
            contract_version=value.contract_version,
            result_digest=value.result_digest,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("upstream_result is not canonical") from error
    if (
        validated != value
        or validated.canonical_representation != value.canonical_representation
        or validated.result_digest != value.result_digest
    ):
        raise ValueError("upstream_result is not canonical")


def _validate_policy(
    value: Any,
    upstream_result: P01Rti13DecisionContinuationResult,
) -> None:
    if not isinstance(value, PaperRiskCapitalPolicySnapshot):
        raise ValueError(
            "policy_snapshot must be a PaperRiskCapitalPolicySnapshot"
        )
    if (
        value.contract_version != P08_POLICY_CONTRACT_VERSION
        or value.evaluator_version != P08_AUTHORITY_EVALUATOR_VERSION
    ):
        raise ValueError("unsupported Risk/Capital policy version")
    try:
        validated = PaperRiskCapitalPolicySnapshot.from_mapping(
            value.canonical_representation
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("policy_snapshot is not canonical") from error
    if (
        validated != value
        or validated.canonical_representation != value.canonical_representation
        or validated.digest != value.digest
    ):
        raise ValueError("policy_snapshot is not canonical")

    if (
        upstream_result.outcome
        is OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED
    ):
        decision = upstream_result.decision_intent
        if decision is None:
            raise ValueError(
                "RTI-13 DECISION_MATERIALIZED result is missing DecisionIntent"
            )
        scope = value.scope_identity
        if (
            value.decision_intent_digest != decision.digest
            or value.context_digest != decision.context_digest
            or scope["candidate_id"] != decision.candidate_id
            or scope["chain_id"] != decision.chain_id
            or scope["token_identity"] != decision.token_identity
        ):
            raise ValueError("policy_snapshot does not match DecisionIntent")


def _valid_authorization_result(
    value: Any,
    upstream_result: P01Rti13DecisionContinuationResult,
    policy: PaperRiskCapitalPolicySnapshot,
) -> bool:
    if not isinstance(value, PaperRiskCapitalAuthorizationResult):
        return False
    decision = upstream_result.decision_intent
    if decision is None:
        return False
    if (
        value.contract_version != P08_AUTHORITY_CONTRACT_VERSION
        or value.evaluator_version != P08_AUTHORITY_EVALUATOR_VERSION
        or value.authorization_effect != PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
        or value.status not in (AuthorizationStatus.APPROVED, AuthorizationStatus.REJECTED)
        or value.decision_intent_digest != decision.digest
        or value.context_digest != decision.context_digest
        or value.policy_snapshot_id != policy.policy_snapshot_id
        or value.policy_snapshot_digest != policy.digest
        or value.scope_identity != policy.scope_identity
        or value.paper_lifecycle_id != policy.scope_identity["paper_lifecycle_id"]
    ):
        return False
    try:
        validated = PaperRiskCapitalAuthorizationResult(
            status=value.status,
            paper_lifecycle_id=value.paper_lifecycle_id,
            scope_identity=value.scope_identity,
            decision_intent_digest=value.decision_intent_digest,
            context_digest=value.context_digest,
            policy_snapshot_id=value.policy_snapshot_id,
            policy_snapshot_digest=value.policy_snapshot_digest,
            simulation_reference_time=value.simulation_reference_time,
            valid_from=value.valid_from,
            valid_until=value.valid_until,
            primary_reason_code=value.primary_reason_code,
            reason_codes=value.reason_codes,
            provenance=value.provenance,
            contract_version=value.contract_version,
            evaluator_version=value.evaluator_version,
            authorization_effect=value.authorization_effect,
            authorization_id=value.authorization_id,
            result_digest=value.result_digest,
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
    if len(value) != len(set(value)):
        raise ValueError("reason_codes must not contain duplicates")
    return value


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
    "P01_RTI_14_CONTRACT_VERSION",
    "DecisionToRiskCapitalOutcome",
    "P01Rti14RiskCapitalContinuationResult",
    "DecisionToRiskCapitalContinuationService",
]
