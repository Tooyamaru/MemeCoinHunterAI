"""P01-PFX-01: deterministic RTI-11 -> RTI-14 prevalidated prefix preparation."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Callable, Mapping

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionOutcome,
    P01Rti11CompositionResult,
)
from backend.application.p05_opportunity_context_continuation import (
    OpportunityContextContinuationOutcome,
    P01Rti12ContinuationResult,
    P05OpportunityContextContinuationService,
)
from backend.application.opportunity_context_to_decision_continuation import (
    OpportunityContextToDecisionContinuationService,
    OpportunityContextToDecisionOutcome,
    P01Rti13DecisionContinuationResult,
)
from backend.application.decision_to_risk_capital_continuation import (
    DecisionToRiskCapitalContinuationService,
    DecisionToRiskCapitalOutcome,
    P01Rti14RiskCapitalContinuationResult,
)
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from core.risk.paper_risk_capital_authorization import (
    P08_AUTHORITY_EVALUATOR_VERSION,
    PaperCapitalState,
    PaperExposureState,
    PaperRiskCapitalPolicySnapshot,
    RiskState,
)


P01_PFX_01_CONTRACT_VERSION = "p01-pfx-01-v1"


class PrevalidatedPrefixOutcome(StrEnum):
    PREFIX_MATERIALIZED = "PREFIX_MATERIALIZED"
    UPSTREAM_STOPPED = "UPSTREAM_STOPPED"
    OWNER_UNAVAILABLE = "OWNER_UNAVAILABLE"


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be canonical non-empty text")
    return value


def _positive_decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int)):
        raise ValueError(f"{name} must be Decimal or int")
    result = Decimal(value)
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return result.normalize()


def _canonical(value: Any, expected_type: type) -> bool:
    if type(value) is not expected_type:
        return False
    try:
        rebuilt = _rebuild_preserving_links(value)
        return type(rebuilt) is expected_type and rebuilt == value
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _rebuild_preserving_links(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            _rebuild_preserving_links(getattr(value, field.name))
        rebuilt = replace(value)
        if rebuilt != value:
            raise ValueError("nested owner is not canonical")
        return rebuilt
    if isinstance(value, tuple):
        for child in value:
            _rebuild_preserving_links(child)
    return value


def _digest(value: Any) -> str:
    def encode(item: Any) -> Any:
        if isinstance(item, datetime):
            return item.astimezone(timezone.utc).isoformat()
        if isinstance(item, Decimal):
            return format(Decimal("0") if item == 0 else item.normalize(), "f")
        if isinstance(item, StrEnum):
            return item.value
        if isinstance(item, Mapping):
            return {str(key): encode(item[key]) for key in sorted(item)}
        if isinstance(item, (tuple, list)):
            return [encode(child) for child in item]
        return item

    return hashlib.sha256(
        json.dumps(
            encode(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class PaperRiskCapitalPolicySeed:
    policy_snapshot_id: str
    risk_governor_version: str
    capital_authorization_version: str
    evaluator_version: str
    paper_lifecycle_id: str
    paper_portfolio_id: str
    simulation_reference_time: datetime
    policy_cutoff_time: datetime
    risk_state_max_age_seconds: Decimal | int
    paper_capital_state_max_age_seconds: Decimal | int
    paper_exposure_state_max_age_seconds: Decimal | int
    valid_from: datetime
    valid_until: datetime
    risk_state: RiskState
    paper_capital_state: PaperCapitalState
    paper_exposure_state: PaperExposureState
    provenance_source: str | None
    seed_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "policy_snapshot_id",
            "risk_governor_version",
            "capital_authorization_version",
            "evaluator_version",
            "paper_lifecycle_id",
            "paper_portfolio_id",
        ):
            _text(getattr(self, name), name)
        if self.evaluator_version != P08_AUTHORITY_EVALUATOR_VERSION:
            raise ValueError("unsupported policy evaluator version")
        for name in (
            "simulation_reference_time",
            "policy_cutoff_time",
            "valid_from",
            "valid_until",
        ):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.valid_until < self.valid_from:
            raise ValueError("valid_until cannot precede valid_from")
        for name in (
            "risk_state_max_age_seconds",
            "paper_capital_state_max_age_seconds",
            "paper_exposure_state_max_age_seconds",
        ):
            object.__setattr__(self, name, _positive_decimal(getattr(self, name), name))
        for value, expected, name in (
            (self.risk_state, RiskState, "risk_state"),
            (self.paper_capital_state, PaperCapitalState, "paper_capital_state"),
            (self.paper_exposure_state, PaperExposureState, "paper_exposure_state"),
        ):
            if not _canonical(value, expected):
                raise ValueError(f"noncanonical {name}")
        if self.provenance_source is not None:
            _text(self.provenance_source, "provenance_source")
        expected = _digest(self._without_digest())
        if self.seed_digest is not None and self.seed_digest != expected:
            raise ValueError("seed_digest mismatch")
        object.__setattr__(self, "seed_digest", expected)

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "policy_snapshot_id": self.policy_snapshot_id,
            "risk_governor_version": self.risk_governor_version,
            "capital_authorization_version": self.capital_authorization_version,
            "evaluator_version": self.evaluator_version,
            "paper_lifecycle_id": self.paper_lifecycle_id,
            "paper_portfolio_id": self.paper_portfolio_id,
            "simulation_reference_time": self.simulation_reference_time,
            "policy_cutoff_time": self.policy_cutoff_time,
            "risk_state_max_age_seconds": self.risk_state_max_age_seconds,
            "paper_capital_state_max_age_seconds": self.paper_capital_state_max_age_seconds,
            "paper_exposure_state_max_age_seconds": self.paper_exposure_state_max_age_seconds,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "risk_state": self.risk_state.canonical_representation,
            "paper_capital_state": self.paper_capital_state.canonical_representation,
            "paper_exposure_state": self.paper_exposure_state.canonical_representation,
            "provenance_source": self.provenance_source,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "seed_digest": self.seed_digest}

    @property
    def digest(self) -> str:
        return self.seed_digest  # type: ignore[return-value]


@dataclass(frozen=True)
class P01Pfx01Request:
    invocation_id: str
    rti11_result: P01Rti11CompositionResult
    decision_ruleset: DecisionEvaluationRuleset
    decision_time: datetime
    policy_seed: PaperRiskCapitalPolicySeed
    contract_version: str = P01_PFX_01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_PFX_01_CONTRACT_VERSION:
            raise ValueError("unsupported PFX-01 contract version")
        if type(self.invocation_id) is not str or not re.fullmatch(
            r"[A-Za-z0-9._:-]{1,128}", self.invocation_id
        ):
            raise ValueError("invalid invocation identity")
        if not _canonical(self.rti11_result, P01Rti11CompositionResult):
            raise ValueError("noncanonical rti11_result")
        if not _canonical(self.decision_ruleset, DecisionEvaluationRuleset):
            raise ValueError("noncanonical decision_ruleset")
        if not _canonical(self.policy_seed, PaperRiskCapitalPolicySeed):
            raise ValueError("noncanonical policy_seed")
        canonical_time = _utc(self.decision_time, "decision_time")
        if canonical_time < self.rti11_result.request.reference_time:
            raise ValueError("decision_time precedes RTI-11 reference")
        object.__setattr__(self, "decision_time", canonical_time)

    @property
    def input_digests(self) -> Mapping[str, str]:
        return {
            "rti11_result": self.rti11_result.result_digest,
            "decision_ruleset": self.decision_ruleset.digest,
            "decision_time": _digest(self.decision_time),
            "policy_seed": self.policy_seed.digest,
        }


@dataclass(frozen=True)
class P01Pfx01Result:
    request: P01Pfx01Request
    outcome: PrevalidatedPrefixOutcome | str
    reason_codes: tuple[str, ...]
    terminal_stage: str
    rti12_result: P01Rti12ContinuationResult | None = None
    rti13_result: P01Rti13DecisionContinuationResult | None = None
    policy_snapshot: PaperRiskCapitalPolicySnapshot | None = None
    rti14_result: P01Rti14RiskCapitalContinuationResult | None = None
    contract_version: str = P01_PFX_01_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not P01Pfx01Request:
            raise ValueError("invalid PFX-01 request")
        self.request.__post_init__()
        if self.contract_version != P01_PFX_01_CONTRACT_VERSION:
            raise ValueError("unsupported PFX-01 result contract")
        try:
            outcome = PrevalidatedPrefixOutcome(self.outcome)
        except (TypeError, ValueError):
            raise ValueError("unsupported PFX-01 outcome") from None
        object.__setattr__(self, "outcome", outcome)
        if type(self.reason_codes) is not tuple or any(
            type(reason) is not str or not reason for reason in self.reason_codes
        ):
            raise ValueError("invalid PFX-01 reasons")
        if self.terminal_stage not in ("RTI-11", "RTI-12", "RTI-13", "POLICY", "RTI-14"):
            raise ValueError("invalid PFX-01 terminal stage")

        if self.rti12_result is not None and not _valid_rti12(self.rti12_result, self.request):
            raise ValueError("invalid exact RTI-12 result")
        if self.rti13_result is not None and not _valid_rti13(
            self.rti13_result, self.rti12_result, self.request
        ):
            raise ValueError("invalid exact RTI-13 result")
        if self.policy_snapshot is not None and not _valid_policy(
            self.policy_snapshot, self.rti13_result, self.request.policy_seed
        ):
            raise ValueError("invalid exact policy snapshot")
        if self.rti14_result is not None and not _valid_rti14(
            self.rti14_result, self.rti13_result, self.policy_snapshot
        ):
            raise ValueError("invalid exact RTI-14 result")

        if outcome is PrevalidatedPrefixOutcome.PREFIX_MATERIALIZED:
            if (
                self.terminal_stage != "RTI-14"
                or self.reason_codes
                or self.rti12_result is None
                or self.rti13_result is None
                or self.policy_snapshot is None
                or self.rti14_result is None
                or self.rti14_result.outcome
                is not DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
            ):
                raise ValueError("invalid materialized prefix")
        elif outcome is PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE:
            expected = {
                "RTI-11": ("RTI-12_UNAVAILABLE",),
                "RTI-12": ("RTI-13_UNAVAILABLE",),
                "RTI-13": ("POLICY_SNAPSHOT_UNAVAILABLE",),
                "POLICY": ("RTI-14_UNAVAILABLE",),
            }.get(self.terminal_stage)
            if expected is None or self.reason_codes != expected:
                raise ValueError("invalid unavailable prefix result")
        else:
            if not self.reason_codes:
                raise ValueError("upstream stop requires reason codes")
            if self.terminal_stage == "RTI-11":
                if self.rti12_result is not None:
                    raise ValueError("RTI-11 stop cannot contain RTI-12")
            elif self.terminal_stage == "RTI-12":
                if self.rti12_result is None or self.rti13_result is not None:
                    raise ValueError("invalid RTI-12 stop")
            elif self.terminal_stage == "RTI-13":
                if (
                    self.rti12_result is None
                    or self.rti13_result is None
                    or self.policy_snapshot is not None
                ):
                    raise ValueError("invalid RTI-13 stop")
            elif self.terminal_stage == "RTI-14":
                if (
                    self.rti12_result is None
                    or self.rti13_result is None
                    or self.policy_snapshot is None
                    or self.rti14_result is None
                    or self.rti14_result.outcome
                    is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
                ):
                    raise ValueError("invalid RTI-14 stop")

        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("PFX-01 result digest mismatch")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> Mapping[str, Any]:
        authorization = (
            self.rti14_result.authorization_result
            if self.rti14_result is not None
            else None
        )
        return {
            "contract_version": self.contract_version,
            "invocation_id": self.request.invocation_id,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "terminal_stage": self.terminal_stage,
            "input_digests": self.request.input_digests,
            "rti12_digest": self.rti12_result.digest if self.rti12_result else None,
            "rti13_digest": self.rti13_result.digest if self.rti13_result else None,
            "policy_snapshot_digest": self.policy_snapshot.digest if self.policy_snapshot else None,
            "rti14_digest": self.rti14_result.digest if self.rti14_result else None,
            "authorization_status": authorization.status.value if authorization else None,
            "authorization_digest": authorization.digest if authorization else None,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


PolicyFactory = Callable[..., PaperRiskCapitalPolicySnapshot]


class PrevalidatedDecisionRiskCapitalPrefixService:
    def __init__(
        self,
        *,
        rti12: Any = None,
        rti13: Any = None,
        policy_factory: PolicyFactory = PaperRiskCapitalPolicySnapshot,
        rti14: Any = None,
    ) -> None:
        self._rti12 = rti12 if rti12 is not None else P05OpportunityContextContinuationService()
        self._rti13 = (
            rti13 if rti13 is not None else OpportunityContextToDecisionContinuationService()
        )
        self._policy_factory = policy_factory
        self._rti14 = (
            rti14 if rti14 is not None else DecisionToRiskCapitalContinuationService()
        )
        if not callable(getattr(self._rti12, "continue_to_context", None)):
            raise ValueError("invalid PFX-01 RTI-12 owner seam")
        if not callable(getattr(self._rti13, "continue_to_decision", None)):
            raise ValueError("invalid PFX-01 RTI-13 owner seam")
        if not callable(self._policy_factory):
            raise ValueError("invalid PFX-01 policy factory")
        if not callable(getattr(self._rti14, "continue_to_risk_capital", None)):
            raise ValueError("invalid PFX-01 RTI-14 owner seam")

    def run(self, request: P01Pfx01Request) -> P01Pfx01Result:
        if type(request) is not P01Pfx01Request:
            raise ValueError("invalid PFX-01 request")
        request.__post_init__()

        if request.rti11_result.outcome is not MarketToOpportunityCompositionOutcome.COMPOSED:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.UPSTREAM_STOPPED,
                reason_codes=request.rti11_result.reason_codes or ("UPSTREAM_NOT_COMPOSED",),
                terminal_stage="RTI-11",
            )

        try:
            rti12 = self._rti12.continue_to_context(request.rti11_result)
        except ValueError:
            raise ValueError("RTI-12 validation failed") from None
        except Exception:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-12_UNAVAILABLE",),
                terminal_stage="RTI-11",
            )
        if not _valid_rti12(rti12, request):
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-12_UNAVAILABLE",),
                terminal_stage="RTI-11",
            )
        if rti12.outcome is not OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.UPSTREAM_STOPPED,
                reason_codes=rti12.reason_codes or ("RTI-12_STOPPED",),
                terminal_stage="RTI-12",
                rti12_result=rti12,
            )

        try:
            rti13 = self._rti13.continue_to_decision(
                rti12,
                request.decision_ruleset,
                request.decision_time,
            )
        except ValueError:
            raise ValueError("RTI-13 validation failed") from None
        except Exception:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-13_UNAVAILABLE",),
                terminal_stage="RTI-12",
                rti12_result=rti12,
            )
        if not _valid_rti13(rti13, rti12, request):
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-13_UNAVAILABLE",),
                terminal_stage="RTI-12",
                rti12_result=rti12,
            )
        if rti13.outcome is not OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.UPSTREAM_STOPPED,
                reason_codes=rti13.reason_codes or ("RTI-13_STOPPED",),
                terminal_stage="RTI-13",
                rti12_result=rti12,
                rti13_result=rti13,
            )

        try:
            policy = self._materialize_policy(rti13, request.policy_seed)
        except ValueError:
            raise ValueError("PFX-01 policy validation failed") from None
        except Exception:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("POLICY_SNAPSHOT_UNAVAILABLE",),
                terminal_stage="RTI-13",
                rti12_result=rti12,
                rti13_result=rti13,
            )
        if not _valid_policy(policy, rti13, request.policy_seed):
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("POLICY_SNAPSHOT_UNAVAILABLE",),
                terminal_stage="RTI-13",
                rti12_result=rti12,
                rti13_result=rti13,
            )

        try:
            rti14 = self._rti14.continue_to_risk_capital(rti13, policy)
        except ValueError:
            raise ValueError("RTI-14 validation failed") from None
        except Exception:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-14_UNAVAILABLE",),
                terminal_stage="POLICY",
                rti12_result=rti12,
                rti13_result=rti13,
                policy_snapshot=policy,
            )
        if not _valid_rti14(rti14, rti13, policy):
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-14_UNAVAILABLE",),
                terminal_stage="POLICY",
                rti12_result=rti12,
                rti13_result=rti13,
                policy_snapshot=policy,
            )
        if rti14.outcome is not DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED:
            return P01Pfx01Result(
                request=request,
                outcome=PrevalidatedPrefixOutcome.UPSTREAM_STOPPED,
                reason_codes=rti14.reason_codes or ("RTI-14_STOPPED",),
                terminal_stage="RTI-14",
                rti12_result=rti12,
                rti13_result=rti13,
                policy_snapshot=policy,
                rti14_result=rti14,
            )
        return P01Pfx01Result(
            request=request,
            outcome=PrevalidatedPrefixOutcome.PREFIX_MATERIALIZED,
            reason_codes=(),
            terminal_stage="RTI-14",
            rti12_result=rti12,
            rti13_result=rti13,
            policy_snapshot=policy,
            rti14_result=rti14,
        )

    def _materialize_policy(
        self,
        rti13: P01Rti13DecisionContinuationResult,
        seed: PaperRiskCapitalPolicySeed,
    ) -> PaperRiskCapitalPolicySnapshot:
        decision = rti13.decision_intent
        if decision is None:
            raise ValueError("missing exact DecisionIntent")
        provenance = {
            "p05_contract_version": decision.risk_evaluation.contract_version,
            "p05_evaluator_version": decision.risk_evaluation.evaluator_version,
            "p06_contract_version": decision.contract_version,
            "p06_ruleset_version": decision.ruleset_version,
            "p06_evaluator_version": decision.evaluator_version,
            "decision_intent_digest": decision.digest,
            "context_digest": decision.context_digest,
            "policy_snapshot_id": seed.policy_snapshot_id,
            "risk_governor_version": seed.risk_governor_version,
            "capital_authorization_version": seed.capital_authorization_version,
            "evaluator_version": seed.evaluator_version,
            "risk_state_digest": seed.risk_state.state_digest,
            "paper_capital_state_digest": seed.paper_capital_state.state_digest,
            "paper_exposure_state_digest": seed.paper_exposure_state.state_digest,
            "paper_lifecycle_id": seed.paper_lifecycle_id,
        }
        if seed.provenance_source is not None:
            provenance["source"] = seed.provenance_source
        return self._policy_factory(
            policy_snapshot_id=seed.policy_snapshot_id,
            risk_governor_version=seed.risk_governor_version,
            capital_authorization_version=seed.capital_authorization_version,
            evaluator_version=seed.evaluator_version,
            scope_identity={
                "paper_lifecycle_id": seed.paper_lifecycle_id,
                "paper_portfolio_id": seed.paper_portfolio_id,
                "candidate_id": decision.candidate_id,
                "chain_id": decision.chain_id,
                "token_identity": decision.token_identity,
            },
            decision_intent_digest=decision.digest,
            context_digest=decision.context_digest,
            simulation_reference_time=seed.simulation_reference_time,
            policy_cutoff_time=seed.policy_cutoff_time,
            risk_state_max_age_seconds=seed.risk_state_max_age_seconds,
            paper_capital_state_max_age_seconds=seed.paper_capital_state_max_age_seconds,
            paper_exposure_state_max_age_seconds=seed.paper_exposure_state_max_age_seconds,
            valid_from=seed.valid_from,
            valid_until=seed.valid_until,
            risk_state=seed.risk_state,
            paper_capital_state=seed.paper_capital_state,
            paper_exposure_state=seed.paper_exposure_state,
            provenance=provenance,
        )


def _valid_rti12(value: Any, request: P01Pfx01Request) -> bool:
    return (
        _canonical(value, P01Rti12ContinuationResult)
        and value.upstream_result is request.rti11_result
    )


def _valid_rti13(
    value: Any,
    rti12: P01Rti12ContinuationResult | None,
    request: P01Pfx01Request,
) -> bool:
    return (
        rti12 is not None
        and _canonical(value, P01Rti13DecisionContinuationResult)
        and value.upstream_result is rti12
        and value.decision_ruleset is request.decision_ruleset
        and value.decision_time == request.decision_time
    )


def _valid_policy(
    value: Any,
    rti13: P01Rti13DecisionContinuationResult | None,
    seed: PaperRiskCapitalPolicySeed,
) -> bool:
    if (
        rti13 is None
        or rti13.decision_intent is None
        or not _canonical(value, PaperRiskCapitalPolicySnapshot)
    ):
        return False
    decision = rti13.decision_intent
    expected_scope = {
        "paper_lifecycle_id": seed.paper_lifecycle_id,
        "paper_portfolio_id": seed.paper_portfolio_id,
        "candidate_id": decision.candidate_id,
        "chain_id": decision.chain_id,
        "token_identity": decision.token_identity,
    }
    return (
        value.policy_snapshot_id == seed.policy_snapshot_id
        and value.risk_governor_version == seed.risk_governor_version
        and value.capital_authorization_version == seed.capital_authorization_version
        and value.evaluator_version == seed.evaluator_version
        and dict(value.scope_identity) == expected_scope
        and value.decision_intent_digest == decision.digest
        and value.context_digest == decision.context_digest
        and value.simulation_reference_time == seed.simulation_reference_time
        and value.policy_cutoff_time == seed.policy_cutoff_time
        and value.risk_state_max_age_seconds == seed.risk_state_max_age_seconds
        and value.paper_capital_state_max_age_seconds
        == seed.paper_capital_state_max_age_seconds
        and value.paper_exposure_state_max_age_seconds
        == seed.paper_exposure_state_max_age_seconds
        and value.valid_from == seed.valid_from
        and value.valid_until == seed.valid_until
        and value.risk_state is seed.risk_state
        and value.paper_capital_state is seed.paper_capital_state
        and value.paper_exposure_state is seed.paper_exposure_state
        and value.provenance["decision_intent_digest"] == decision.digest
        and value.provenance["context_digest"] == decision.context_digest
        and value.provenance["risk_state_digest"] == seed.risk_state.state_digest
        and value.provenance["paper_capital_state_digest"]
        == seed.paper_capital_state.state_digest
        and value.provenance["paper_exposure_state_digest"]
        == seed.paper_exposure_state.state_digest
    )


def _valid_rti14(
    value: Any,
    rti13: P01Rti13DecisionContinuationResult | None,
    policy: PaperRiskCapitalPolicySnapshot | None,
) -> bool:
    return (
        rti13 is not None
        and policy is not None
        and _canonical(value, P01Rti14RiskCapitalContinuationResult)
        and value.upstream_result is rti13
        and value.policy_snapshot is policy
    )


__all__ = [
    "P01_PFX_01_CONTRACT_VERSION",
    "PaperRiskCapitalPolicySeed",
    "P01Pfx01Request",
    "P01Pfx01Result",
    "PrevalidatedPrefixOutcome",
    "PrevalidatedDecisionRiskCapitalPrefixService",
]
