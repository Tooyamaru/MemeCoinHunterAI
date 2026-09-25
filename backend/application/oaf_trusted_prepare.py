"""Bounded server-side OAF trusted prepare orchestration.

This service owns the one-shot server sequence from an explicit controller
candidate/target through trusted Solana evidence, canonical RTI-11, exact
server-built PFX/PFS requests, CIP preparation, and opaque case registration.

It does not expose HTTP, run OCI/OSC, persist lifecycle output, retry, poll,
schedule, discover candidates, sign, or trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

from backend.application.oaf_prepare_case import (
    OafPrepareCaseRequest,
    OafPrepareCaseResult,
    OafPrepareCaseService,
)
from backend.application.oaf_rti11_integration import (
    OafRti11IntegrationRequest,
    OafRti11IntegrationService,
)
from backend.application.oaf_solana_upstream_composition import (
    OafCanonicalUpstreamResult,
    OafSolanaCanonicalComposer,
)
from backend.application.operator_paper_case_registry import (
    OperatorPaperCaseRecord,
    OperatorPaperCaseRegistry,
)
from core.data.coingecko_onchain_orchestration import ExactPoolDiagnosticTarget
from core.data.contracts import FreshnessPolicy
from core.data.solana_oaf_source import SolanaMintSnapshot


P01_OAF_TRUSTED_PREPARE_VERSION = "p01-oaf-01-trusted-prepare-v1"


class OafTrustedPrepareError(ValueError):
    """Fail-closed trusted-prepare orchestration error."""


@dataclass(frozen=True)
class OafTrustedPrepareCommand:
    candidate_id: str
    token_mint: str
    target: ExactPoolDiagnosticTarget
    processing_time: datetime
    reference_time: datetime
    evaluation_time: datetime
    freshness_policy: FreshnessPolicy
    max_top_holder_fraction: float
    rti11_timeout: timedelta
    rti11_max_response_bytes: int
    evaluation_id: str
    contract_version: str = P01_OAF_TRUSTED_PREPARE_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_TRUSTED_PREPARE_VERSION:
            raise OafTrustedPrepareError("unsupported trusted-prepare contract")
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise OafTrustedPrepareError("candidate_id is required")
        if not isinstance(self.token_mint, str) or not self.token_mint.strip():
            raise OafTrustedPrepareError("token_mint is required")
        if not isinstance(self.target, ExactPoolDiagnosticTarget):
            raise OafTrustedPrepareError("exact target is required")
        if self.target.chain_id != "solana" or self.target.token_mint != self.token_mint:
            raise OafTrustedPrepareError("target identity mismatch")
        for name in ("processing_time", "reference_time", "evaluation_time"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                raise OafTrustedPrepareError(f"{name} must be timezone-aware")
        if not isinstance(self.freshness_policy, FreshnessPolicy):
            raise OafTrustedPrepareError("freshness_policy is required")
        if not isinstance(self.evaluation_id, str) or not self.evaluation_id.strip():
            raise OafTrustedPrepareError("evaluation_id is required")


@dataclass(frozen=True)
class OafTrustedPrepareResult:
    command: OafTrustedPrepareCommand
    snapshot: SolanaMintSnapshot
    upstream: OafCanonicalUpstreamResult
    prepared: OafPrepareCaseResult
    record: OperatorPaperCaseRecord
    contract_version: str = P01_OAF_TRUSTED_PREPARE_VERSION


PrepareRequestFactory = Callable[[Any, OafTrustedPrepareCommand], OafPrepareCaseRequest]


class OafTrustedPrepareService:
    """Execute exactly one trusted prepare chain and register the exact case."""

    def __init__(
        self,
        *,
        solana_source: Any,
        prepare_request_factory: PrepareRequestFactory,
        upstream: Any = None,
        rti11: Any = None,
        prepare_case: Any = None,
        registry: OperatorPaperCaseRegistry,
    ) -> None:
        if not callable(getattr(solana_source, "snapshot_mint", None)):
            raise OafTrustedPrepareError("invalid Solana source seam")
        if not callable(prepare_request_factory):
            raise OafTrustedPrepareError("invalid prepare request factory")
        self._solana = solana_source
        self._factory = prepare_request_factory
        self._upstream = upstream or OafSolanaCanonicalComposer()
        self._rti11 = rti11 or OafRti11IntegrationService()
        self._prepare = prepare_case or OafPrepareCaseService()
        self._registry = registry

    def prepare(self, command: OafTrustedPrepareCommand) -> OafTrustedPrepareResult:
        if not isinstance(command, OafTrustedPrepareCommand):
            raise OafTrustedPrepareError("invalid trusted-prepare command")
        command.__post_init__()

        snapshot = self._solana.snapshot_mint(command.token_mint)
        if not isinstance(snapshot, SolanaMintSnapshot) or snapshot.token_mint != command.token_mint:
            raise OafTrustedPrepareError("Solana source returned invalid snapshot")

        upstream = self._upstream.compose(
            snapshot=snapshot,
            processing_time=command.processing_time,
            reference_time=command.reference_time,
            evaluation_time=command.evaluation_time,
            freshness_policy=command.freshness_policy,
            evaluation_id=command.evaluation_id,
            max_top_holder_fraction=command.max_top_holder_fraction,
        )
        if not isinstance(upstream, OafCanonicalUpstreamResult):
            raise OafTrustedPrepareError("upstream composer returned noncanonical result")

        rti11_result = self._rti11.compose(
            OafRti11IntegrationRequest(
                candidate_id=command.candidate_id,
                upstream=upstream,
                target=command.target,
                reference_time=command.reference_time,
                timeout=command.rti11_timeout,
                max_response_bytes=command.rti11_max_response_bytes,
                freshness_policy=command.freshness_policy,
                processing_time=command.processing_time,
                evaluated_at=command.evaluation_time,
                evaluation_id=command.evaluation_id,
                analytical_context={"source": "operator-facade-trusted-prepare"},
            )
        )

        prepare_request = self._factory(rti11_result, command)
        if not isinstance(prepare_request, OafPrepareCaseRequest):
            raise OafTrustedPrepareError("prepare factory returned noncanonical request")
        if prepare_request.rti11_result is not rti11_result:
            raise OafTrustedPrepareError("prepare factory did not preserve exact RTI-11 identity")

        prepared = self._prepare.prepare(prepare_request)
        if not isinstance(prepared, OafPrepareCaseResult) or prepared.request is not prepare_request:
            raise OafTrustedPrepareError("prepare owner returned noncanonical result")

        record = self._registry.put(prepared)
        if record.prepared is not prepared:
            raise OafTrustedPrepareError("registry did not preserve exact prepared case")
        return OafTrustedPrepareResult(command, snapshot, upstream, prepared, record)


__all__ = [
    "OafTrustedPrepareCommand",
    "OafTrustedPrepareError",
    "OafTrustedPrepareResult",
    "OafTrustedPrepareService",
    "P01_OAF_TRUSTED_PREPARE_VERSION",
]
