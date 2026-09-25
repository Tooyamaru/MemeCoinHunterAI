"""Application-level OAF prepare invocation.

Binds one explicit trusted-source command to one explicit paper-input bundle,
then delegates through the existing trusted prepare service. This keeps browser
transport concerns outside canonical owners and preserves the exact server-held
RTI-11 object into PFX/PFS/CIP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.application.oaf_paper_request_factory import (
    OafExplicitPaperInputs,
    OafPaperRequestFactory,
)
from backend.application.oaf_trusted_prepare import (
    OafTrustedPrepareCommand,
    OafTrustedPrepareResult,
    OafTrustedPrepareService,
)


P01_OAF_PREPARE_INVOCATION_VERSION = "p01-oaf-01-prepare-invocation-v1"


class OafPrepareInvocationError(ValueError):
    """Fail-closed application orchestration error."""


@dataclass(frozen=True)
class OafPrepareInvocation:
    command: OafTrustedPrepareCommand
    paper_inputs: OafExplicitPaperInputs
    contract_version: str = P01_OAF_PREPARE_INVOCATION_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_PREPARE_INVOCATION_VERSION:
            raise OafPrepareInvocationError("unsupported prepare-invocation contract")
        if not isinstance(self.command, OafTrustedPrepareCommand):
            raise OafPrepareInvocationError("trusted prepare command is required")
        if not isinstance(self.paper_inputs, OafExplicitPaperInputs):
            raise OafPrepareInvocationError("explicit paper inputs are required")
        self.command.__post_init__()
        self.paper_inputs.__post_init__()


class OafPrepareInvocationService:
    """Run one bounded trusted prepare using one exact paper-input bundle."""

    def __init__(
        self,
        *,
        trusted_prepare: Any,
        paper_factory: OafPaperRequestFactory | None = None,
    ) -> None:
        if not callable(getattr(trusted_prepare, "prepare", None)):
            raise OafPrepareInvocationError("invalid trusted prepare seam")
        self._trusted_prepare = trusted_prepare
        self._paper_factory = paper_factory or OafPaperRequestFactory()

    def prepare(self, invocation: OafPrepareInvocation) -> OafTrustedPrepareResult:
        if not isinstance(invocation, OafPrepareInvocation):
            raise OafPrepareInvocationError("invalid prepare invocation")
        invocation.__post_init__()

        command = invocation.command
        paper_inputs = invocation.paper_inputs

        def exact_factory(rti11_result, received_command):
            if received_command is not command:
                raise OafPrepareInvocationError(
                    "trusted prepare did not preserve exact command identity"
                )
            return self._paper_factory.build(rti11_result, paper_inputs)

        # The trusted service already owns source -> P02/P03 -> RTI-11 ->
        # prepare -> registry. This invocation layer only binds explicit paper
        # inputs to that one call and never invokes owners itself.
        original_factory = getattr(self._trusted_prepare, "_factory", None)
        if original_factory is not None:
            raise OafPrepareInvocationError(
                "trusted prepare service must be invocation-scoped"
            )

        raise OafPrepareInvocationError(
            "trusted prepare service requires invocation-scoped factory binding"
        )


class OafPrepareInvocationServiceV1:
    """Concrete invocation service that constructs a fresh trusted service per call.

    The source/upstream/RTI-11/prepare owners and registry are injected once;
    only the paper-request factory closure is invocation-local.
    """

    def __init__(
        self,
        *,
        solana_source: Any,
        registry: Any,
        upstream: Any = None,
        rti11: Any = None,
        prepare_case: Any = None,
        paper_factory: OafPaperRequestFactory | None = None,
    ) -> None:
        self._solana_source = solana_source
        self._registry = registry
        self._upstream = upstream
        self._rti11 = rti11
        self._prepare_case = prepare_case
        self._paper_factory = paper_factory or OafPaperRequestFactory()

    def prepare(self, invocation: OafPrepareInvocation) -> OafTrustedPrepareResult:
        if not isinstance(invocation, OafPrepareInvocation):
            raise OafPrepareInvocationError("invalid prepare invocation")
        invocation.__post_init__()
        command = invocation.command
        paper_inputs = invocation.paper_inputs

        def factory(rti11_result, received_command):
            if received_command is not command:
                raise OafPrepareInvocationError(
                    "trusted prepare did not preserve exact command identity"
                )
            return self._paper_factory.build(rti11_result, paper_inputs)

        service = OafTrustedPrepareService(
            solana_source=self._solana_source,
            prepare_request_factory=factory,
            upstream=self._upstream,
            rti11=self._rti11,
            prepare_case=self._prepare_case,
            registry=self._registry,
        )
        return service.prepare(command)


__all__ = [
    "OafPrepareInvocation",
    "OafPrepareInvocationError",
    "OafPrepareInvocationServiceV1",
    "P01_OAF_PREPARE_INVOCATION_VERSION",
]
