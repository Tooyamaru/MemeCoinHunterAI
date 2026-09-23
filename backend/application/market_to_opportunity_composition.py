"""Bounded caller-directed market-to-opportunity application composition.

This P01-RTI-11 boundary owns only validation, one P04-LME-03 delegation,
and one delegation to the existing canonical P04/P05 producer. It does not
select a candidate or pool, derive safety or signals, persist, publish, decide,
schedule, retry, or execute anything.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Callable, Mapping

from core.data.coingecko_onchain_diagnostic import run_ohlcv_diagnostic
from core.data.coingecko_onchain_ohlcv import (
    ADAPTER_VERSION,
    ENDPOINT_VERSION,
    PROVIDER_ID,
    OhlcvOutcome,
    OhlcvRequest,
)
from core.data.coingecko_onchain_orchestration import (
    ControlledDiagnosticOutcome,
    ControlledDiagnosticResult,
    ExactPoolDiagnosticTarget,
    run_controlled_ohlcv_diagnostic,
)
from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.market_intelligence import (
    P02_MARKET_INTELLIGENCE_CONTRACT_VERSION,
    AcceptedMarketIntelligenceObservation,
    MarketIntelligenceCategory,
)
from core.data.market_observations import P02T07PredecessorContext
from core.opportunity.canonical_evidence_producer import (
    produce_canonical_p04_to_p05,
)
from core.opportunity.p04_p05_composition import CanonicalP04ToP05Composition
from core.risk.safety_eligibility import P03_T03_EVALUATOR_ID
from core.risk.safety_evaluation import (
    P03_T02_CONTRACT_VERSION,
    SafetyEvaluationResult,
)
from core.risk.safety_evidence import DerivedEligibilityOutput
from core.signals.price_direction_policy import POLICY_VERSION, SIGNAL_TYPE
from core.signals.signal_evidence import (
    P04_T01_CONTRACT_VERSION,
    SignalEvidenceCollection,
)


P01_RTI_11_CONTRACT_VERSION = "p01-rti-11-v1"
P02_T06_CONTRACT_VERSION = "p02-t06-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_CONTRACT_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_MAX_CONTEXT_BYTES = 8192
_MAX_CONTEXT_DEPTH = 8
_MAX_CONTEXT_ITEMS = 64


class MarketToOpportunityCompositionOutcome(StrEnum):
    COMPOSED = "COMPOSED"
    TOKEN_NOT_CURRENT = "TOKEN_NOT_CURRENT"
    DIAGNOSTIC_NOT_PRODUCED = "DIAGNOSTIC_NOT_PRODUCED"
    COMPOSITION_UNAVAILABLE = "COMPOSITION_UNAVAILABLE"


@dataclass(frozen=True)
class P01Rti11CompositionRequest:
    """All caller-owned facts required for one bounded composition."""

    candidate_id: str
    predecessor: P02T07PredecessorContext
    target: ExactPoolDiagnosticTarget
    safety_evaluation: SafetyEvaluationResult
    eligibility: DerivedEligibilityOutput
    reference_time: datetime
    timeout: timedelta
    max_response_bytes: int
    freshness_policy: FreshnessPolicy
    processing_time: datetime
    evaluated_at: datetime
    evaluation_id: str | None = None
    analytical_context: Mapping[str, Any] | None = None
    contract_version: str = P01_RTI_11_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        if self.contract_version != P01_RTI_11_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-11 contract_version")
        if not isinstance(self.predecessor, P02T07PredecessorContext):
            raise ValueError("predecessor must be a P02T07PredecessorContext")
        if self.predecessor.materializer_contract_version != P02_T06_CONTRACT_VERSION:
            raise ValueError("unsupported P02 predecessor contract version")
        if not isinstance(self.target, ExactPoolDiagnosticTarget):
            raise ValueError("target must be an ExactPoolDiagnosticTarget")
        _validate_target_reference(self.target)
        if not isinstance(self.safety_evaluation, SafetyEvaluationResult):
            raise ValueError("safety_evaluation must be a SafetyEvaluationResult")
        if not isinstance(self.eligibility, DerivedEligibilityOutput):
            raise ValueError("eligibility must be a DerivedEligibilityOutput")
        if not isinstance(self.freshness_policy, FreshnessPolicy) or (
            self.freshness_policy.stale_after is None
        ):
            raise ValueError("explicit freshness_policy is required")
        reference_time = _utc(self.reference_time, "reference_time")
        processing_time = _utc(self.processing_time, "processing_time")
        evaluated_at = _utc(self.evaluated_at, "evaluated_at")
        object.__setattr__(self, "reference_time", reference_time)
        object.__setattr__(self, "processing_time", processing_time)
        object.__setattr__(self, "evaluated_at", evaluated_at)
        if self.evaluation_id is not None:
            _require_text(self.evaluation_id, "evaluation_id")
        context = _canonical_context(self.analytical_context)
        object.__setattr__(self, "analytical_context", context)

        # Reuse the existing request contract for target composition and bounds.
        OhlcvRequest(
            chain_id=self.target.chain_id,
            token_mint=self.target.token_mint,
            pool_address=self.target.pool_address,
            base_mint=self.target.base_mint,
            quote_mint=self.target.quote_mint,
            reference_time=reference_time,
            timeout=self.timeout,
            max_response_bytes=self.max_response_bytes,
        )
        _validate_p03_handoff(self)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _request_material(self)


@dataclass(frozen=True)
class P01Rti11CompositionResult:
    """Deterministic bounded result without new domain semantics."""

    request: P01Rti11CompositionRequest
    outcome: MarketToOpportunityCompositionOutcome | str
    reason_codes: tuple[str, ...]
    diagnostic: ControlledDiagnosticResult | None = None
    composition: CanonicalP04ToP05Composition | None = None
    contract_version: str = P01_RTI_11_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request, P01Rti11CompositionRequest):
            raise ValueError("request must be a P01Rti11CompositionRequest")
        try:
            outcome = MarketToOpportunityCompositionOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported RTI-11 outcome") from error
        object.__setattr__(self, "outcome", outcome)
        if self.contract_version != P01_RTI_11_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-11 contract_version")
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        if outcome is MarketToOpportunityCompositionOutcome.COMPOSED:
            if not isinstance(self.diagnostic, ControlledDiagnosticResult) or not isinstance(
                self.composition, CanonicalP04ToP05Composition
            ):
                raise ValueError("COMPOSED requires diagnostic and composition")
            if reasons:
                raise ValueError("COMPOSED cannot contain reason codes")
            if not _diagnostic_success(self.diagnostic, self.request) or not (
                _composition_matches(self.composition, self.request)
            ):
                raise ValueError("COMPOSED payload does not match request")
        elif outcome in {
            MarketToOpportunityCompositionOutcome.TOKEN_NOT_CURRENT,
            MarketToOpportunityCompositionOutcome.DIAGNOSTIC_NOT_PRODUCED,
        }:
            if not isinstance(self.diagnostic, ControlledDiagnosticResult):
                raise ValueError("diagnostic outcome requires controlled result")
            if self.composition is not None or not reasons:
                raise ValueError("non-composed diagnostic result is invalid")
            if outcome is MarketToOpportunityCompositionOutcome.TOKEN_NOT_CURRENT and (
                self.diagnostic.outcome
                is not ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT
            ):
                raise ValueError("TOKEN_NOT_CURRENT requires matching diagnostic")
            if outcome is MarketToOpportunityCompositionOutcome.DIAGNOSTIC_NOT_PRODUCED and (
                self.diagnostic.outcome
                is ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT
                or _diagnostic_success(self.diagnostic, self.request)
            ):
                raise ValueError("DIAGNOSTIC_NOT_PRODUCED requires non-success")
        elif self.diagnostic is not None or self.composition is not None or not reasons:
            raise ValueError("COMPOSITION_UNAVAILABLE must contain only safe reasons")
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match RTI-11 result")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "request": self.request.canonical_representation,
            "diagnostic": _canonical(self.diagnostic),
            "composition_digest": (
                self.composition.digest if self.composition is not None else None
            ),
            "composition_provenance_digests": (
                self.composition.provenance_digests
                if self.composition is not None
                else ()
            ),
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


ControlledDiagnostic = Callable[..., ControlledDiagnosticResult]
CanonicalProducer = Callable[..., CanonicalP04ToP05Composition]


class MarketToOpportunityCompositionService:
    """The sole RTI-11 entry point; it creates no concrete runtime caller."""

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        clock: Callable[[], datetime] | None = None,
        controlled_diagnostic: ControlledDiagnostic = run_controlled_ohlcv_diagnostic,
        diagnostic: Callable[..., Any] = run_ohlcv_diagnostic,
        canonical_producer: CanonicalProducer = produce_canonical_p04_to_p05,
    ) -> None:
        if environment is not None and not isinstance(environment, Mapping):
            raise ValueError("environment must be a mapping")
        if clock is not None and not callable(clock):
            raise ValueError("clock must be callable")
        if not callable(controlled_diagnostic):
            raise ValueError("controlled_diagnostic must be callable")
        if not callable(diagnostic):
            raise ValueError("diagnostic must be callable")
        if not callable(canonical_producer):
            raise ValueError("canonical_producer must be callable")
        self._environment = environment
        self._clock = clock
        self._controlled_diagnostic = controlled_diagnostic
        self._diagnostic = diagnostic
        self._canonical_producer = canonical_producer

    def compose(
        self,
        request: P01Rti11CompositionRequest,
    ) -> P01Rti11CompositionResult:
        if not isinstance(request, P01Rti11CompositionRequest):
            raise ValueError("request must be a P01Rti11CompositionRequest")
        arguments: dict[str, Any] = {
            "target": request.target,
            "predecessor": request.predecessor,
            "reference_time": request.reference_time,
            "timeout": request.timeout,
            "max_response_bytes": request.max_response_bytes,
            "freshness_policy": request.freshness_policy,
            "environment": self._environment,
            "diagnostic": self._diagnostic,
        }
        if self._clock is not None:
            arguments["clock"] = self._clock
        try:
            controlled = self._controlled_diagnostic(**arguments)
        except Exception:
            return _unavailable(request, "CONTROLLED_DIAGNOSTIC_UNAVAILABLE")
        if not isinstance(controlled, ControlledDiagnosticResult):
            return _unavailable(request, "CONTROLLED_DIAGNOSTIC_INVALID_RESULT")
        if not _controlled_identity_matches(controlled, request):
            return _unavailable(request, "CONTROLLED_DIAGNOSTIC_IDENTITY_MISMATCH")
        if controlled.outcome is ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT:
            return P01Rti11CompositionResult(
                request=request,
                outcome=MarketToOpportunityCompositionOutcome.TOKEN_NOT_CURRENT,
                reason_codes=("TOKEN_NOT_CURRENT",),
                diagnostic=controlled,
            )
        if not _diagnostic_success(controlled, request):
            return P01Rti11CompositionResult(
                request=request,
                outcome=MarketToOpportunityCompositionOutcome.DIAGNOSTIC_NOT_PRODUCED,
                reason_codes=("DIAGNOSTIC_NOT_PRODUCED",),
                diagnostic=controlled,
            )
        assert controlled.diagnostic is not None
        signal_evidence = controlled.diagnostic.signal_evidence
        assert signal_evidence is not None
        try:
            composition = self._canonical_producer(
                candidate_id=request.candidate_id,
                chain_id=request.target.chain_id,
                token_identity=request.target.token_mint,
                reference_time=request.reference_time,
                eligibility=request.eligibility,
                signal_evidence=signal_evidence,
                market_observations=controlled.diagnostic.market.observations,
                freshness_policy=request.freshness_policy,
                analytical_context=request.analytical_context,
                evaluation_id=request.evaluation_id,
                processing_time=request.processing_time,
                evaluated_at=request.evaluated_at,
            )
        except Exception:
            return _unavailable(request, "CANONICAL_COMPOSITION_UNAVAILABLE")
        if not isinstance(composition, CanonicalP04ToP05Composition):
            return _unavailable(request, "CANONICAL_COMPOSITION_INVALID_RESULT")
        return P01Rti11CompositionResult(
            request=request,
            outcome=MarketToOpportunityCompositionOutcome.COMPOSED,
            reason_codes=(),
            diagnostic=controlled,
            composition=composition,
        )


def _validate_p03_handoff(request: P01Rti11CompositionRequest) -> None:
    evaluation = request.safety_evaluation
    eligibility = request.eligibility
    if evaluation.contract_version != P03_T02_CONTRACT_VERSION:
        raise ValueError("unsupported P03 safety evaluation contract version")
    if eligibility.contract_version != P03_T02_CONTRACT_VERSION:
        raise ValueError("unsupported P03 eligibility contract version")
    if evaluation.chain_id != request.target.chain_id or (
        evaluation.token_identity != request.target.token_mint
    ):
        raise ValueError("P03 identity does not match exact target")
    if eligibility.evaluator_id != P03_T03_EVALUATOR_ID:
        raise ValueError("unsupported P03 eligibility evaluator")
    if eligibility.evaluated_at != evaluation.evaluation_timestamp:
        raise ValueError("P03 eligibility timestamp does not match evaluation")
    if eligibility.evidence_references != evaluation.evidence_references:
        raise ValueError("P03 eligibility references do not match evaluation")
    if eligibility.evaluated_at > request.reference_time:
        raise ValueError("P03 eligibility is after reference_time")


def _diagnostic_success(
    result: ControlledDiagnosticResult,
    request: P01Rti11CompositionRequest,
) -> bool:
    if result.outcome is not ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED:
        return False
    if result.target != request.target or not isinstance(result.request, OhlcvRequest):
        return False
    expected_request = OhlcvRequest(
        chain_id=request.target.chain_id,
        token_mint=request.target.token_mint,
        pool_address=request.target.pool_address,
        base_mint=request.target.base_mint,
        quote_mint=request.target.quote_mint,
        reference_time=request.reference_time,
        timeout=request.timeout,
        max_response_bytes=request.max_response_bytes,
    )
    if result.request != expected_request or result.diagnostic is None:
        return False
    market = result.diagnostic.market
    if market.outcome is not OhlcvOutcome.PRODUCED or market.provenance is None:
        return False
    provenance = market.provenance
    if (
        provenance.request != result.request
        or provenance.provider_id != PROVIDER_ID
        or provenance.adapter_version != ADAPTER_VERSION
        or provenance.endpoint_version != ENDPOINT_VERSION
        or not isinstance(provenance.response_digest, str)
        or _SHA256.fullmatch(provenance.response_digest) is None
        or provenance.returned_base != result.request.base_mint
        or provenance.returned_quote != result.request.quote_mint
    ):
        return False
    observations = market.observations
    if len(observations) != 3 or not all(
        _valid_observation(value, result.request, provenance.response_digest)
        for value in observations
    ):
        return False
    times = tuple(value.observation_time for value in observations)
    if times != tuple(sorted(times)) or len(set(times)) != 3:
        return False
    observation_ids = tuple(value.observation_id for value in observations)
    fingerprints = tuple(value.fingerprint for value in observations)
    state_digests = tuple(value.upstream.state_digest for value in observations)
    evidence_collection = result.diagnostic.signal_evidence
    if not isinstance(evidence_collection, SignalEvidenceCollection) or (
        evidence_collection.contract_version != P04_T01_CONTRACT_VERSION
        or evidence_collection.chain_id != result.request.chain_id
        or evidence_collection.token_identity != result.request.token_mint
        or len(evidence_collection.evidence) != 1
    ):
        return False
    evidence = evidence_collection.evidence[0]
    metadata = evidence.provenance.metadata
    return (
        evidence.contract_version == P04_T01_CONTRACT_VERSION
        and evidence.chain_id == result.request.chain_id
        and evidence.token_identity == result.request.token_mint
        and evidence.signal_type == SIGNAL_TYPE
        and evidence.source_id == PROVIDER_ID
        and evidence.observed_at == observations[-1].observation_time
        and evidence.provenance.source_id == PROVIDER_ID
        and evidence.provenance.method == POLICY_VERSION
        and evidence.provenance.observed_at == observations[-1].observation_time
        and metadata.get("policy_version") == POLICY_VERSION
        and metadata.get("response_digest") == provenance.response_digest
        and metadata.get("pool_address") == result.request.pool_address
        and tuple(metadata.get("observation_ids", ())) == observation_ids
        and tuple(metadata.get("observation_fingerprints", ())) == fingerprints
        and tuple(metadata.get("upstream_state_digests", ())) == state_digests
    )


def _controlled_identity_matches(
    result: ControlledDiagnosticResult,
    request: P01Rti11CompositionRequest,
) -> bool:
    if result.target != request.target:
        return False
    if result.request is None:
        return result.outcome is ControlledDiagnosticOutcome.INVALID_INPUT
    expected = OhlcvRequest(
        chain_id=request.target.chain_id,
        token_mint=request.target.token_mint,
        pool_address=request.target.pool_address,
        base_mint=request.target.base_mint,
        quote_mint=request.target.quote_mint,
        reference_time=request.reference_time,
        timeout=request.timeout,
        max_response_bytes=request.max_response_bytes,
    )
    return result.request == expected


def _valid_observation(
    value: Any,
    request: OhlcvRequest,
    response_digest: str,
) -> bool:
    return (
        isinstance(value, AcceptedMarketIntelligenceObservation)
        and value.accepted is True
        and value.quality is DataQuality.VALID
        and value.source_id == PROVIDER_ID
        and value.chain_id == request.chain_id
        and value.token_identity == request.token_mint
        and value.market_subject_id == request.pool_address
        and value.intelligence_category is MarketIntelligenceCategory.PRICE
        and value.contract_version == P02_MARKET_INTELLIGENCE_CONTRACT_VERSION
        and value.category_contract_version
        == P02_MARKET_INTELLIGENCE_CONTRACT_VERSION
        and value.provenance.source_id == PROVIDER_ID
        and value.provenance.chain_id == request.chain_id
        and value.provenance.token_identity == request.token_mint
        and value.provenance.market_subject_id == request.pool_address
        and value.provenance.observation_id == value.observation_id
        and value.provenance.observation_time == value.observation_time
        and value.provenance.received_time == value.received_time
        and value.provenance.reference_time == value.reference_time
        and value.provenance.upstream_state_version == value.upstream.state_version
        and value.provenance.upstream_state_digest == value.upstream.state_digest
        and value.provenance.upstream_contract_version == value.upstream.contract_version
        and value.upstream.contract_version == "p02-t08-v1"
        and value.upstream.chain_id == request.chain_id
        and value.upstream.token_identity == request.token_mint
        and value.upstream.market_subject_id == request.pool_address
        and value.provenance.source_metadata.get("adapter_version") == ADAPTER_VERSION
        and value.provenance.source_metadata.get("endpoint_version") == ENDPOINT_VERSION
        and value.provenance.source_metadata.get("response_digest") == response_digest
        and value.provenance.observation_metadata.get("pool_address")
        == request.pool_address
    )


def _composition_matches(
    composition: CanonicalP04ToP05Composition,
    request: P01Rti11CompositionRequest,
) -> bool:
    candidate = composition.candidate
    return (
        candidate.candidate_id == request.candidate_id
        and candidate.chain_id == request.target.chain_id
        and candidate.token_identity == request.target.token_mint
        and candidate.reference_time == request.reference_time
        and candidate.eligibility is request.eligibility
        and composition.score.candidate_id == request.candidate_id
        and composition.score.chain_id == request.target.chain_id
        and composition.score.token_identity == request.target.token_mint
        and composition.score.reference_time == request.reference_time
        and composition.score.evaluated_at == request.evaluated_at
    )


def _unavailable(
    request: P01Rti11CompositionRequest,
    reason: str,
) -> P01Rti11CompositionResult:
    return P01Rti11CompositionResult(
        request=request,
        outcome=MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE,
        reason_codes=(reason,),
    )


def _validate_target_reference(target: ExactPoolDiagnosticTarget) -> None:
    if not isinstance(target.target_reference_id, str) or (
        _REFERENCE_ID.fullmatch(target.target_reference_id) is None
    ):
        raise ValueError("invalid target_reference_id")
    if not isinstance(target.target_reference_digest, str) or (
        _SHA256.fullmatch(target.target_reference_digest) is None
    ):
        raise ValueError("invalid target_reference_digest")
    if not isinstance(target.target_contract_version, str) or (
        _CONTRACT_VERSION.fullmatch(target.target_contract_version) is None
    ):
        raise ValueError("invalid target_contract_version")


def _request_material(request: P01Rti11CompositionRequest) -> Mapping[str, Any]:
    return {
        "contract_version": request.contract_version,
        "candidate_id": request.candidate_id,
        "predecessor": {
            "state_version": request.predecessor.state_version,
            "state_digest": request.predecessor.state_digest,
            "materializer_contract_version": (
                request.predecessor.materializer_contract_version
            ),
            "evaluation_id": request.predecessor.evaluation_id,
        },
        "target": _canonical(request.target),
        "safety_evaluation": {
            "representation_digest": request.safety_evaluation.representation_digest,
            "chain_id": request.safety_evaluation.chain_id,
            "token_identity": request.safety_evaluation.token_identity,
            "input_evidence_digest": request.safety_evaluation.input_evidence_digest,
            "evaluation_timestamp": request.safety_evaluation.evaluation_timestamp,
            "contract_version": request.safety_evaluation.contract_version,
            "evidence_references": request.safety_evaluation.evidence_references,
            "provenance": request.safety_evaluation.provenance,
        },
        "eligibility": _canonical(request.eligibility),
        "reference_time": request.reference_time,
        "timeout": request.timeout,
        "max_response_bytes": request.max_response_bytes,
        "freshness_policy": request.freshness_policy,
        "processing_time": request.processing_time,
        "evaluated_at": request.evaluated_at,
        "evaluation_id": request.evaluation_id,
        "analytical_context": request.analytical_context,
    }


def _canonical_context(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("analytical_context must be a mapping")
    counter = [0]
    result = _canonical_bounded(value, depth=0, counter=counter)
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > _MAX_CONTEXT_BYTES:
        raise ValueError("analytical_context exceeds bounded size")
    return _freeze(result)


def _canonical_bounded(value: Any, *, depth: int, counter: list[int]) -> Any:
    if depth > _MAX_CONTEXT_DEPTH:
        raise ValueError("analytical_context exceeds bounded depth")
    counter[0] += 1
    if counter[0] > _MAX_CONTEXT_ITEMS:
        raise ValueError("analytical_context exceeds bounded items")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("analytical_context contains non-finite number")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("analytical_context keys must be strings")
        return {
            key: _canonical_bounded(value[key], depth=depth + 1, counter=counter)
            for key in sorted(value)
        }
    if isinstance(value, (tuple, list)):
        return tuple(
            _canonical_bounded(item, depth=depth + 1, counter=counter)
            for item in value
        )
    raise ValueError("analytical_context contains unsupported value")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, tuple):
        return tuple(_freeze(child) for child in value)
    return value


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number is not canonical")
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _utc(value, "timestamp").isoformat()
    if isinstance(value, timedelta):
        return format(Decimal(str(value.total_seconds())), "f")
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("canonical mapping keys must be strings")
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical(getattr(value, field.name)) for field in fields(value)}
    raise ValueError(f"unsupported canonical value: {type(value).__name__}")


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _reason_codes(value: Any) -> tuple[str, ...]:
    if not isinstance(value, tuple) or any(
        not isinstance(item, str) or not item or item != item.strip()
        for item in value
    ):
        raise ValueError("reason_codes must be canonical non-empty tuple values")
    return tuple(sorted(set(value)))


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be canonical non-empty text")


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "P01_RTI_11_CONTRACT_VERSION",
    "MarketToOpportunityCompositionOutcome",
    "MarketToOpportunityCompositionService",
    "P01Rti11CompositionRequest",
    "P01Rti11CompositionResult",
]
