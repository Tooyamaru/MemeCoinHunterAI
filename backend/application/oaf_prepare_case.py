"""Bounded OAF composition from exact RTI-11 result to canonical CIP prepared case."""

from __future__ import annotations

from dataclasses import dataclass, replace

from backend.application.controlled_paper_experiment_input_preparation import (
    ControlledPaperExperimentInputPreparer,
    P01Cip01Request,
    P01Cip01Result,
)
from backend.application.market_to_opportunity_composition import P01Rti11CompositionResult
from backend.application.paper_fact_sourcing import (
    PaperFactSourcingRequest,
    PaperFactSourcingResult,
    PaperFactSourcingService,
)
from backend.application.prevalidated_decision_risk_capital_prefix import (
    P01Pfx01Request,
    P01Pfx01Result,
    PrevalidatedDecisionRiskCapitalPrefixService,
)


P01_OAF_PREPARE_CASE_VERSION = "p01-oaf-01-prepare-case-v1"


class OafPrepareCaseError(ValueError):
    """Fail-closed validation error before/within bounded prepare composition."""


@dataclass(frozen=True)
class OafPrepareCaseRequest:
    invocation_id: str
    rti11_result: P01Rti11CompositionResult
    pfx_request: P01Pfx01Request
    pfs_request: PaperFactSourcingRequest
    contract_version: str = P01_OAF_PREPARE_CASE_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_PREPARE_CASE_VERSION:
            raise OafPrepareCaseError("unsupported prepare-case contract")
        if not isinstance(self.invocation_id, str) or not self.invocation_id.strip():
            raise OafPrepareCaseError("invocation_id is required")
        if not isinstance(self.rti11_result, P01Rti11CompositionResult):
            raise OafPrepareCaseError("rti11_result must be canonical")
        if not isinstance(self.pfx_request, P01Pfx01Request):
            raise OafPrepareCaseError("pfx_request must be canonical")
        if not isinstance(self.pfs_request, PaperFactSourcingRequest):
            raise OafPrepareCaseError("pfs_request must be canonical")
        if self.pfx_request.rti11_result is not self.rti11_result:
            raise OafPrepareCaseError("PFX request must retain exact RTI-11 identity")
        if self.pfs_request.rti11_result is not self.rti11_result:
            raise OafPrepareCaseError("PFS request must retain exact RTI-11 identity")


@dataclass(frozen=True)
class OafPrepareCaseResult:
    request: OafPrepareCaseRequest
    pfx_result: P01Pfx01Result
    pfs_result: PaperFactSourcingResult
    cip_result: P01Cip01Result
    contract_version: str = P01_OAF_PREPARE_CASE_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_PREPARE_CASE_VERSION:
            raise OafPrepareCaseError("unsupported prepare-case result contract")
        if self.pfx_result.request is not self.request.pfx_request:
            raise OafPrepareCaseError("PFX result request identity mismatch")
        if self.pfs_result.request is not self.request.pfs_request:
            raise OafPrepareCaseError("PFS result request identity mismatch")
        if self.cip_result.request.pfx_result is not self.pfx_result:
            raise OafPrepareCaseError("CIP did not preserve exact PFX result")
        if self.cip_result.request.pfs_result is not self.pfs_result:
            raise OafPrepareCaseError("CIP did not preserve exact PFS result")


class OafPrepareCaseService:
    """Run exact PFX and PFS owners once each, then CIP once; no OCI/run occurs."""

    def __init__(self, *, pfx=None, pfs=None, cip=None) -> None:
        self._pfx = pfx if pfx is not None else PrevalidatedDecisionRiskCapitalPrefixService()
        self._pfs = pfs if pfs is not None else PaperFactSourcingService()
        self._cip = cip if cip is not None else ControlledPaperExperimentInputPreparer()
        if not callable(getattr(self._pfx, "run", None)):
            raise OafPrepareCaseError("invalid PFX owner seam")
        if not callable(getattr(self._pfs, "source", None)):
            raise OafPrepareCaseError("invalid PFS owner seam")
        if not callable(getattr(self._cip, "prepare", None)):
            raise OafPrepareCaseError("invalid CIP owner seam")

    def prepare(self, request: OafPrepareCaseRequest) -> OafPrepareCaseResult:
        if not isinstance(request, OafPrepareCaseRequest):
            raise OafPrepareCaseError("invalid prepare-case request")
        request.__post_init__()

        pfx = self._pfx.run(request.pfx_request)
        if not isinstance(pfx, P01Pfx01Result) or pfx.request is not request.pfx_request:
            raise OafPrepareCaseError("PFX returned noncanonical result")

        pfs = self._pfs.source(request.pfs_request)
        if not isinstance(pfs, PaperFactSourcingResult) or pfs.request is not request.pfs_request:
            raise OafPrepareCaseError("PFS returned noncanonical result")

        cip_request = P01Cip01Request(
            invocation_id=request.invocation_id,
            pfx_result=pfx,
            pfs_result=pfs,
        )
        cip = self._cip.prepare(cip_request)
        if not isinstance(cip, P01Cip01Result) or cip.request is not cip_request:
            raise OafPrepareCaseError("CIP returned noncanonical result")

        return OafPrepareCaseResult(request, pfx, pfs, cip)


__all__ = [
    "OafPrepareCaseError",
    "OafPrepareCaseRequest",
    "OafPrepareCaseResult",
    "OafPrepareCaseService",
    "P01_OAF_PREPARE_CASE_VERSION",
]
