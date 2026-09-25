"""Authenticated read-only review transport for process-local OAF prepared cases."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.api.operator_access import OperatorAccessDenied, require_operator_bearer
from backend.application.operator_paper_case_registry import (
    OperatorPaperCaseRecord,
    OperatorPaperCaseRegistry,
)
from backend.core.request_id import get_request_id


NO_STORE_HEADERS = {"Cache-Control": "no-store"}


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
        simulation_only=True,
        source_label="historical_price_proxy_and_explicit_simulation_assumptions",
    )


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    request_id = get_request_id()
    return JSONResponse(
        status_code=status_code,
        headers={**NO_STORE_HEADERS, "X-Request-ID": request_id},
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
    "OperatorHttpError",
    "authorize_operator",
    "get_operator_case_registry",
    "operator_http_error_handler",
    "router",
]
