"""Bounded read-only HTTP transport for persisted paper lifecycle results."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.application.paper_lifecycle_persistence import (
    ControlledPaperPersistenceService,
    PaperLifecycleReadOutcome,
    PaperLifecycleReadResult,
)
from backend.application.paper_lifecycle_query import PaperLifecycleQueryService
from backend.core.request_id import get_request_id


NO_STORE_HEADERS = {"Cache-Control": "no-store"}


class PaperLifecycleRunResponse(BaseModel):
    contract_version: str
    outcome: str
    reason_codes: list[str]
    admission_digest: str
    fill_digest: str | None
    transition_digest: str | None
    ledger_digest: str | None
    reconciliation_digest: str | None
    paper_result_digest: str | None
    history_digest: str | None
    observation_digest: str | None
    lifecycle_result_digest: str
    decision_intent_digest: str | None
    simulation_input_digest: str | None
    artifact_count: int


class PaperLifecycleArtifactResponse(BaseModel):
    artifact_kind: str
    artifact_digest: str
    payload_digest: str
    owner_contract_version: str
    canonical_payload: str
    ordinal: int


class PaperLifecycleReadResponse(BaseModel):
    contract_version: str
    outcome: str
    reason_codes: list[str]
    lifecycle_result_digest: str
    result_digest: str
    run: PaperLifecycleRunResponse | None
    artifacts: list[PaperLifecycleArtifactResponse]

    @classmethod
    def from_result(
        cls,
        result: PaperLifecycleReadResult,
    ) -> PaperLifecycleReadResponse:
        return cls(
            contract_version=result.contract_version,
            outcome=result.outcome.value,
            reason_codes=list(result.reason_codes),
            lifecycle_result_digest=result.lifecycle_result_digest,
            result_digest=result.digest,
            run=(
                PaperLifecycleRunResponse.model_validate(
                    result.run.canonical_representation
                )
                if result.run is not None
                else None
            ),
            artifacts=[
                PaperLifecycleArtifactResponse.model_validate(
                    artifact.canonical_representation
                )
                for artifact in result.artifacts
            ],
        )


class TransportErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class TransportErrorResponse(BaseModel):
    error: TransportErrorDetail


def get_paper_lifecycle_query(request: Request) -> PaperLifecycleQueryService:
    """Build the RTI-05 query over the database runtime owned by this app."""

    persistence = ControlledPaperPersistenceService(request.app.state.database)
    return PaperLifecycleQueryService(persistence)


router = APIRouter(prefix="/api/v1", tags=["paper-lifecycle-results"])


@router.get(
    "/paper-lifecycle-results/{lifecycle_result_digest}",
    response_model=PaperLifecycleReadResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": PaperLifecycleReadResponse},
        status.HTTP_409_CONFLICT: {"model": PaperLifecycleReadResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": TransportErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": TransportErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": PaperLifecycleReadResponse
        },
    },
)
async def read_paper_lifecycle_result(
    lifecycle_result_digest: str,
    query: Annotated[
        PaperLifecycleQueryService,
        Depends(get_paper_lifecycle_query),
    ],
) -> JSONResponse:
    """Return one persisted lifecycle result without invoking any lifecycle."""

    try:
        result = await query.query(lifecycle_result_digest)
    except ValueError as error:
        if str(error) != "lifecycle_result_digest must be a digest":
            raise
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            headers=NO_STORE_HEADERS,
            content={
                "error": {
                    "code": "invalid_lifecycle_result_digest",
                    "message": (
                        "lifecycle_result_digest must be a lowercase "
                        "SHA-256 digest"
                    ),
                    "request_id": get_request_id(),
                }
            },
        )

    status_code = {
        PaperLifecycleReadOutcome.FOUND: status.HTTP_200_OK,
        PaperLifecycleReadOutcome.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        PaperLifecycleReadOutcome.CORRUPT: status.HTTP_409_CONFLICT,
        PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE: (
            status.HTTP_503_SERVICE_UNAVAILABLE
        ),
    }[result.outcome]
    response = PaperLifecycleReadResponse.from_result(result)
    return JSONResponse(
        status_code=status_code,
        headers=NO_STORE_HEADERS,
        content=response.model_dump(mode="json"),
    )
