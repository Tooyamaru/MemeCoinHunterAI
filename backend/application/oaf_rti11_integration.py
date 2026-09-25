"""Bounded OAF handoff from canonical Solana P02/P03 results into RTI-11."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionService,
    P01Rti11CompositionRequest,
    P01Rti11CompositionResult,
)
from backend.application.oaf_solana_upstream_composition import (
    OafCanonicalUpstreamResult,
)
from core.data.coingecko_onchain_orchestration import ExactPoolDiagnosticTarget
from core.data.contracts import FreshnessPolicy


P01_OAF_RTI11_INTEGRATION_VERSION = "p01-oaf-01-rti11-integration-v1"


class OafRti11IntegrationError(ValueError):
    """Fail-closed validation error before RTI-11 delegation."""


@dataclass(frozen=True)
class OafRti11IntegrationRequest:
    candidate_id: str
    upstream: OafCanonicalUpstreamResult
    target: ExactPoolDiagnosticTarget
    reference_time: datetime
    timeout: timedelta
    max_response_bytes: int
    freshness_policy: FreshnessPolicy
    processing_time: datetime
    evaluated_at: datetime
    evaluation_id: str | None = None
    analytical_context: Mapping[str, Any] | None = None
    contract_version: str = P01_OAF_RTI11_INTEGRATION_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_RTI11_INTEGRATION_VERSION:
            raise OafRti11IntegrationError("unsupported integration contract")
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise OafRti11IntegrationError("candidate_id is required")
        if not isinstance(self.upstream, OafCanonicalUpstreamResult):
            raise OafRti11IntegrationError("upstream must be canonical OAF result")
        if not isinstance(self.target, ExactPoolDiagnosticTarget):
            raise OafRti11IntegrationError("target must be ExactPoolDiagnosticTarget")
        if self.target.chain_id != "solana":
            raise OafRti11IntegrationError("target chain must be solana")
        if self.target.token_mint != self.upstream.token_mint:
            raise OafRti11IntegrationError("target token does not match upstream token")
        if not self.upstream.predecessor.contains(
            self.target.chain_id, self.target.token_mint
        ):
            raise OafRti11IntegrationError("upstream predecessor does not contain target")
        if self.upstream.safety_evaluation.token_identity != self.target.token_mint:
            raise OafRti11IntegrationError("safety evaluation token mismatch")
        if self.upstream.safety_evaluation.chain_id != self.target.chain_id:
            raise OafRti11IntegrationError("safety evaluation chain mismatch")


class OafRti11IntegrationService:
    """Construct the exact RTI-11 request and delegate exactly once."""

    def __init__(self, *, rti11: Any = None) -> None:
        self._rti11 = rti11 if rti11 is not None else MarketToOpportunityCompositionService()
        if not callable(getattr(self._rti11, "compose", None)):
            raise OafRti11IntegrationError("invalid RTI-11 owner seam")

    def compose(self, request: OafRti11IntegrationRequest) -> P01Rti11CompositionResult:
        if not isinstance(request, OafRti11IntegrationRequest):
            raise OafRti11IntegrationError("invalid integration request")
        request.__post_init__()
        exact = P01Rti11CompositionRequest(
            candidate_id=request.candidate_id,
            predecessor=request.upstream.predecessor,
            target=request.target,
            safety_evaluation=request.upstream.safety_evaluation,
            eligibility=request.upstream.eligibility,
            reference_time=request.reference_time,
            timeout=request.timeout,
            max_response_bytes=request.max_response_bytes,
            freshness_policy=request.freshness_policy,
            processing_time=request.processing_time,
            evaluated_at=request.evaluated_at,
            evaluation_id=request.evaluation_id,
            analytical_context=request.analytical_context,
        )
        result = self._rti11.compose(exact)
        if not isinstance(result, P01Rti11CompositionResult):
            raise OafRti11IntegrationError("RTI-11 returned noncanonical result")
        if result.request is not exact:
            raise OafRti11IntegrationError("RTI-11 did not preserve exact request identity")
        return result


__all__ = [
    "OafRti11IntegrationError",
    "OafRti11IntegrationRequest",
    "OafRti11IntegrationService",
    "P01_OAF_RTI11_INTEGRATION_VERSION",
]
