"""Authenticated read-only review transport for process-local OAF prepared cases."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from backend.api.operator_access import OperatorAccessDenied, require_operator_bearer
from backend.api.operator_prepare_transport import (
    OperatorPrepareDecodeError,
    OperatorPrepareRequest,
    OperatorPrepareResponse,
    decode_operator_prepare_request,
)
from backend.application.oaf_operator_paper_intent import OafOperatorPaperIntentError
from backend.application.operator_paper_case_persist import (
    OperatorPaperPersistOutcome,
)
from backend.application.operator_paper_case_registry import (
    OperatorPaperCaseRecord,
    OperatorPaperCaseRegistry,
)
from backend.application.operator_paper_case_run import (
    OperatorPaperRunOutcome,
)
from backend.core.request_id import get_request_id
from core.data.solana_oaf_source import SolanaSourceUnavailable


NO_STORE_HEADERS = {"Cache-Control": "no-store"}


class OperatorPersistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_digest: str
    oci_digest: str
    osc_digest: str
    lifecycle_result_digest: str
    confirm_persist: bool


class OperatorPersistResponse(BaseModel):
    contract_version: str
    handle: str
    case_digest: str
    state: str
    outcome: str
    reason_codes: list[str]
    persistence_outcome: str | None
    persistence_digest: str | None
    lifecycle_result_digest: str | None
    artifact_count: int | None
    readback_path: str | None
    simulation_only: bool = True


class OperatorRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_digest: str
    confirm_run: bool


class OperatorRunResponse(BaseModel):
    contract_version: str
    handle: str
    case_digest: str
    state: str
    outcome: str
    reason_codes: list[str]
    oci_outcome: str | None
    oci_digest: str | None
    osc_outcome: str | None
    osc_digest: str | None
    osc_terminal_stage: str | None
    lifecycle_result_digest: str | None
    persist_eligible: bool
    simulation_only: bool = True


class OperatorCaseReviewResponse(BaseModel):
    contract_version: str
    handle: str
    case_digest: str
    state: str
    created_at: str
    expires_at: str
    candidate_id: str
    chain_id: str
    token_mint: str
    pool_address: str
    eligibility: str
    pfx_outcome: str
    pfs_outcome: str
    cip_outcome: str
    cip_digest: str
    oci_outcome: str | None
    oci_digest: str | None
    osc_outcome: str | None
    osc_digest: str | None
    lifecycle_result_digest: str | None
    persistence_outcome: str | None
    persistence_digest: str | None
    persistence_artifact_count: int | None
    readback_path: str | None
    simulation_only: bool
    source_label: str


def get_operator_case_registry(request: Request) -> OperatorPaperCaseRegistry:
    return request.app.state.operator_case_registry


def authorize_operator(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    try:
        require_operator_bearer(
            authorization=authorization,
            configured_token=request.app.state.operator_bearer_token,
        )
    except OperatorAccessDenied as exc:
        code = str(exc)
        http_status = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if code == "OPERATOR_ACCESS_UNAVAILABLE"
            else status.HTTP_401_UNAUTHORIZED
        )
        raise OperatorHttpError(http_status, code) from None


class OperatorHttpError(Exception):
    def __init__(self, status_code: int, code: str) -> None:
        self.status_code = status_code
        self.code = code
        super().__init__(code)


router = APIRouter(prefix="/api/v1/operator/paper-cases", tags=["operator-paper-cases"])


@router.post(
    "",
    dependencies=[Depends(authorize_operator)],
)
async def prepare_operator_case(
    payload: OperatorPrepareRequest,
    request: Request,
) -> JSONResponse:
    service = getattr(request.app.state, "operator_prepare_service", None)
    if service is None:
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "operator_prepare_unavailable",
            "Trusted prepare source is not configured",
        )
    try:
        invocation = decode_operator_prepare_request(payload)
        result = service.prepare(invocation)
    except OperatorPrepareDecodeError:
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "operator_prepare_invalid",
            "Operator prepare payload is invalid",
        )
    except OafOperatorPaperIntentError as exc:
        if exc.reason_codes:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                headers=NO_STORE_HEADERS,
                content={
                    "contract_version": "p01-oaf-01-post-prepare-v1",
                    "state": "PREPARATION_STOPPED",
                    "reason_codes": list(exc.reason_codes),
                    "simulation_only": True,
                },
            )
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "operator_prepare_invalid",
            "Operator paper intent could not be linked",
        )
    except SolanaSourceUnavailable:
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "operator_prepare_source_unavailable",
            "Trusted Solana source is unavailable",
        )
    except RuntimeError:
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "operator_prepare_unavailable",
            "Operator prepare service is unavailable",
        )
    except ValueError:
        return _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "operator_prepare_invalid",
            "Operator prepare request failed canonical validation",
        )

    record = result.record
    prepared = result.prepared
    rti11 = prepared.request.rti11_result
    target = rti11.request.target
    response = OperatorPrepareResponse(
        contract_version=result.contract_version,
        handle=record.handle,
        case_digest=record.case_digest,
        state=record.state.value,
        candidate_id=rti11.request.candidate_id,
        chain_id=target.chain_id,
        token_mint=target.token_mint,
        pool_address=target.pool_address,
        eligibility=rti11.request.eligibility.status.value,
        pfx_outcome=prepared.pfx_result.outcome.value,
        pfs_outcome=prepared.pfs_result.outcome.value,
        cip_outcome=prepared.cip_result.outcome.value,
        cip_digest=prepared.cip_result.result_digest,
        review_path=f"/api/v1/operator/paper-cases/{record.handle}",
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        headers=NO_STORE_HEADERS,
        content=response.model_dump(mode="json"),
    )


@router.post(
    "/{handle}/run",
    dependencies=[Depends(authorize_operator)],
)
async def run_operator_case(
    handle: str,
    payload: OperatorRunRequest,
    request: Request,
) -> JSONResponse:
    if payload.confirm_run is not True:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "operator_run_confirmation_required",
            "Explicit run confirmation is required",
        )
    service = getattr(request.app.state, "operator_run_service", None)
    if service is None:
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "operator_run_unavailable",
            "Operator run service is unavailable",
        )

    result = service.run_once(
        handle=handle,
        case_digest=payload.case_digest,
    )
    if result.outcome is OperatorPaperRunOutcome.CASE_NOT_FOUND:
        return _error(
            status.HTTP_404_NOT_FOUND,
            "operator_case_not_found",
            "Prepared paper case was not found or has expired",
        )
    if result.outcome is OperatorPaperRunOutcome.CASE_DIGEST_MISMATCH:
        return _error(
            status.HTTP_409_CONFLICT,
            "operator_case_digest_mismatch",
            "Prepared paper case digest does not match reviewed case",
        )
    if result.outcome is OperatorPaperRunOutcome.CASE_NOT_RUNNABLE:
        return _error(
            status.HTTP_409_CONFLICT,
            "operator_case_not_runnable",
            "Prepared paper case is not in a runnable state",
        )

    record = result.record
    if record is None:
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "operator_run_unavailable",
            "Operator run result is unavailable",
        )
    oci = record.oci_result
    osc = oci.osc02_result if oci is not None else None
    lifecycle = osc.lifecycle_result if osc is not None else None
    response = OperatorRunResponse(
        contract_version=result.contract_version,
        handle=record.handle,
        case_digest=record.case_digest,
        state=record.state.value,
        outcome=result.outcome.value,
        reason_codes=list(result.reason_codes),
        oci_outcome=oci.outcome.value if oci is not None else None,
        oci_digest=oci.result_digest if oci is not None else None,
        osc_outcome=osc.outcome.value if osc is not None else None,
        osc_digest=osc.result_digest if osc is not None else None,
        osc_terminal_stage=osc.terminal_stage if osc is not None else None,
        lifecycle_result_digest=lifecycle.digest if lifecycle is not None else None,
        persist_eligible=(
            osc is not None
            and osc.outcome.value == "LIFECYCLE_RETURNED"
            and lifecycle is not None
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        headers=NO_STORE_HEADERS,
        content=response.model_dump(mode="json"),
    )


@router.post(
    "/{handle}/persist",
    dependencies=[Depends(authorize_operator)],
)
async def persist_operator_case(
    handle: str,
    payload: OperatorPersistRequest,
    request: Request,
) -> JSONResponse:
    if payload.confirm_persist is not True:
        return _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "operator_persist_confirmation_required",
            "Explicit persistence confirmation is required",
        )
    service = getattr(request.app.state, "operator_persist_service", None)
    if service is None:
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "operator_persist_unavailable",
            "Operator persistence service is unavailable",
        )

    result = await service.persist_once(
        handle=handle,
        case_digest=payload.case_digest,
        oci_digest=payload.oci_digest,
        osc_digest=payload.osc_digest,
        lifecycle_result_digest=payload.lifecycle_result_digest,
    )
    if result.outcome is OperatorPaperPersistOutcome.CASE_NOT_FOUND:
        return _error(
            status.HTTP_404_NOT_FOUND,
            "operator_case_not_found",
            "Prepared paper case was not found or has expired",
        )
    conflict_codes = {
        OperatorPaperPersistOutcome.CASE_DIGEST_MISMATCH: "operator_case_digest_mismatch",
        OperatorPaperPersistOutcome.OCI_DIGEST_MISMATCH: "operator_oci_digest_mismatch",
        OperatorPaperPersistOutcome.OSC_DIGEST_MISMATCH: "operator_osc_digest_mismatch",
        OperatorPaperPersistOutcome.LIFECYCLE_DIGEST_MISMATCH: "operator_lifecycle_digest_mismatch",
        OperatorPaperPersistOutcome.CASE_NOT_PERSISTABLE: "operator_case_not_persistable",
    }
    if result.outcome in conflict_codes:
        return _error(
            status.HTTP_409_CONFLICT,
            conflict_codes[result.outcome],
            "Prepared paper case does not satisfy the persistence precondition",
        )

    record = result.record
    if record is None:
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "operator_persist_unavailable",
            "Operator persistence result is unavailable",
        )
    owner = record.persistence_result
    lifecycle_digest = (
        owner.lifecycle_result_digest
        if owner is not None and owner.lifecycle_result_digest is not None
        else payload.lifecycle_result_digest
    )
    response = OperatorPersistResponse(
        contract_version=result.contract_version,
        handle=record.handle,
        case_digest=record.case_digest,
        state=record.state.value,
        outcome=result.outcome.value,
        reason_codes=list(result.reason_codes),
        persistence_outcome=owner.outcome.value if owner is not None else None,
        persistence_digest=owner.result_digest if owner is not None else None,
        lifecycle_result_digest=lifecycle_digest,
        artifact_count=owner.artifact_count if owner is not None else None,
        readback_path=(
            f"/api/v1/paper-lifecycle-results/{lifecycle_digest}"
            if lifecycle_digest is not None
            else None
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        headers=NO_STORE_HEADERS,
        content=response.model_dump(mode="json"),
    )


@router.get(
    "/{handle}",
    response_model=OperatorCaseReviewResponse,
    dependencies=[Depends(authorize_operator)],
)
async def review_operator_case(
    handle: str,
    registry: Annotated[OperatorPaperCaseRegistry, Depends(get_operator_case_registry)],
) -> JSONResponse:
    record = registry.get(handle)
    if record is None:
        return _error(
            status.HTTP_404_NOT_FOUND,
            "operator_case_not_found",
            "Prepared paper case was not found or has expired",
        )
    response = _project(record)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        headers=NO_STORE_HEADERS,
        content=response.model_dump(mode="json"),
    )


def _project(record: OperatorPaperCaseRecord) -> OperatorCaseReviewResponse:
    prepared = record.prepared
    rti11 = prepared.request.rti11_result
    target = rti11.request.target
    oci = record.oci_result
    osc = oci.osc02_result if oci is not None else None
    lifecycle = osc.lifecycle_result if osc is not None else None
    persistence = record.persistence_result
    lifecycle_digest = (
        persistence.lifecycle_result_digest
        if persistence is not None and persistence.lifecycle_result_digest is not None
        else (lifecycle.digest if lifecycle is not None else None)
    )
    return OperatorCaseReviewResponse(
        contract_version=record.contract_version,
        handle=record.handle,
        case_digest=record.case_digest,
        state=record.state.value,
        created_at=record.created_at.isoformat(),
        expires_at=record.expires_at.isoformat(),
        candidate_id=rti11.request.candidate_id,
        chain_id=target.chain_id,
        token_mint=target.token_mint,
        pool_address=target.pool_address,
        eligibility=rti11.request.eligibility.status.value,
        pfx_outcome=prepared.pfx_result.outcome.value,
        pfs_outcome=prepared.pfs_result.outcome.value,
        cip_outcome=prepared.cip_result.outcome.value,
        cip_digest=prepared.cip_result.result_digest,
        oci_outcome=oci.outcome.value if oci is not None else None,
        oci_digest=oci.result_digest if oci is not None else None,
        osc_outcome=osc.outcome.value if osc is not None else None,
        osc_digest=osc.result_digest if osc is not None else None,
        lifecycle_result_digest=lifecycle_digest,
        persistence_outcome=persistence.outcome.value if persistence is not None else None,
        persistence_digest=persistence.result_digest if persistence is not None else None,
        persistence_artifact_count=persistence.artifact_count if persistence is not None else None,
        readback_path=(
            f"/api/v1/paper-lifecycle-results/{lifecycle_digest}"
            if lifecycle_digest is not None
            else None
        ),
        simulation_only=True,
        source_label="historical_price_proxy_and_explicit_simulation_assumptions",
    )


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    request_id = get_request_id()
    return JSONResponse(
        status_code=status_code,
        headers=NO_STORE_HEADERS,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


async def operator_http_error_handler(_request: Request, exc: OperatorHttpError) -> JSONResponse:
    message = {
        "OPERATOR_AUTH_REQUIRED": "Operator bearer authorization is required",
        "OPERATOR_AUTH_INVALID": "Operator bearer authorization is invalid",
        "OPERATOR_ACCESS_UNAVAILABLE": "Operator access is not configured",
    }.get(exc.code, "Operator access denied")
    return _error(exc.status_code, exc.code.lower(), message)


__all__ = [
    "OperatorCaseReviewResponse",
    "OperatorPersistRequest",
    "OperatorPersistResponse",
    "OperatorRunRequest",
    "OperatorRunResponse",
    "prepare_operator_case",
    "persist_operator_case",
    "run_operator_case",
    "OperatorHttpError",
    "authorize_operator",
    "get_operator_case_registry",
    "operator_http_error_handler",
    "router",
]
