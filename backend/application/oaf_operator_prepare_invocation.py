"""Operator prepare invocation binding explicit paper intent after RTI-11."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.application.oaf_operator_paper_intent import (
    OafOperatorPaperIntent,
    OafOperatorPaperIntentBuilder,
)
from backend.application.oaf_paper_request_factory import OafPaperRequestFactory
from backend.application.oaf_trusted_prepare import (
    OafTrustedPrepareCommand,
    OafTrustedPrepareResult,
    OafTrustedPrepareService,
)


P01_OAF_OPERATOR_PREPARE_INVOCATION_VERSION = (
    "p01-oaf-01-operator-prepare-invocation-v1"
)


class OafOperatorPrepareInvocationError(ValueError):
    pass


@dataclass(frozen=True)
class OafOperatorPrepareInvocation:
    command: OafTrustedPrepareCommand
    paper_intent: OafOperatorPaperIntent
    contract_version: str = P01_OAF_OPERATOR_PREPARE_INVOCATION_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_OPERATOR_PREPARE_INVOCATION_VERSION:
            raise OafOperatorPrepareInvocationError(
                "unsupported operator prepare invocation contract"
            )
        if not isinstance(self.command, OafTrustedPrepareCommand):
            raise OafOperatorPrepareInvocationError("trusted prepare command is required")
        if not isinstance(self.paper_intent, OafOperatorPaperIntent):
            raise OafOperatorPrepareInvocationError("operator paper intent is required")
        self.command.__post_init__()
        self.paper_intent.__post_init__()


class OafOperatorPrepareInvocationService:
    """Run one trusted prepare and resolve the paper observation post-RTI-11."""

    def __init__(
        self,
        *,
        solana_source: Any,
        registry: Any,
        upstream: Any = None,
        rti11: Any = None,
        prepare_case: Any = None,
        intent_builder: OafOperatorPaperIntentBuilder | None = None,
        paper_factory: OafPaperRequestFactory | None = None,
    ) -> None:
        self._solana_source = solana_source
        self._registry = registry
        self._upstream = upstream
        self._rti11 = rti11
        self._prepare_case = prepare_case
        self._intent_builder = intent_builder or OafOperatorPaperIntentBuilder()
        self._paper_factory = paper_factory or OafPaperRequestFactory()

    def prepare(
        self, invocation: OafOperatorPrepareInvocation
    ) -> OafTrustedPrepareResult:
        if not isinstance(invocation, OafOperatorPrepareInvocation):
            raise OafOperatorPrepareInvocationError("invalid operator prepare invocation")
        invocation.__post_init__()
        command = invocation.command
        intent = invocation.paper_intent

        def factory(rti11_result, received_command):
            if received_command is not command:
                raise OafOperatorPrepareInvocationError(
                    "trusted prepare did not preserve exact command identity"
                )
            explicit = self._intent_builder.build(rti11_result, intent)
            return self._paper_factory.build(rti11_result, explicit)

        return OafTrustedPrepareService(
            solana_source=self._solana_source,
            prepare_request_factory=factory,
            upstream=self._upstream,
            rti11=self._rti11,
            prepare_case=self._prepare_case,
            registry=self._registry,
        ).prepare(command)


__all__ = [
    "OafOperatorPrepareInvocation",
    "OafOperatorPrepareInvocationError",
    "OafOperatorPrepareInvocationService",
    "P01_OAF_OPERATOR_PREPARE_INVOCATION_VERSION",
]
