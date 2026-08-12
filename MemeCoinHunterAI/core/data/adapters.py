"""Provider-neutral source adapter contract for P02-T03.

This module defines the boundary between a future provider-specific adapter and
the P02-T02 ingestion orchestrator. It contains no provider SDK, network,
retry, persistence, or source-health implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from core.data.contracts import SequenceValue
from core.data.orchestration import AdapterObservation, ObservationKind


class AdapterCapability(StrEnum):
    """Provider-neutral capabilities an adapter may explicitly declare."""

    STREAM = "STREAM"
    BATCH = "BATCH"
    CURSOR = "CURSOR"
    ORDERING = "ORDERING"
    RESYNCHRONIZATION = "RESYNCHRONIZATION"


class AdapterLifecycleState(StrEnum):
    """Adapter process lifecycle, independent from source health."""

    CREATED = "CREATED"
    STARTED = "STARTED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class AdapterHealthStatus(StrEnum):
    """Adapter-observed health; STARTED does not imply AVAILABLE."""

    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"


class UnsupportedCapabilityError(ValueError):
    """Raised when an adapter operation needs an undeclared capability."""


@dataclass(frozen=True)
class AdapterIdentity:
    """Stable identity and contract metadata for one adapter instance."""

    adapter_id: str
    source_id: str
    contract_version: str

    def __post_init__(self) -> None:
        for name, value in (
            ("adapter_id", self.adapter_id),
            ("source_id", self.source_id),
            ("contract_version", self.contract_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class AdapterCapabilities:
    """Immutable, provider-neutral capability declaration."""

    values: frozenset[AdapterCapability] = frozenset()

    def __post_init__(self) -> None:
        if not all(isinstance(value, AdapterCapability) for value in self.values):
            raise ValueError("capabilities must contain only AdapterCapability values")

    def supports(self, capability: AdapterCapability) -> bool:
        return capability in self.values

    def require(self, capability: AdapterCapability) -> None:
        if not self.supports(capability):
            raise UnsupportedCapabilityError(
                f"adapter does not declare capability {capability.value}"
            )


@dataclass(frozen=True)
class AdapterHealth:
    """Explicit adapter health observation, separate from source health."""

    status: AdapterHealthStatus
    observed_time: datetime | None = None
    reason: str | None = None


@dataclass(frozen=True)
class AdapterLifecycleResult:
    """Auditable result of an explicit adapter lifecycle transition."""

    identity: AdapterIdentity
    state: AdapterLifecycleState
    health: AdapterHealth
    observed_time: datetime
    cursor: SequenceValue = None
    reason: str | None = None


@runtime_checkable
class ProviderNeutralSourceAdapter(Protocol):
    """Contract implemented by future provider-specific adapter wrappers."""

    @property
    def identity(self) -> AdapterIdentity:
        ...

    @property
    def capabilities(self) -> AdapterCapabilities:
        ...

    @property
    def lifecycle_state(self) -> AdapterLifecycleState:
        ...

    @property
    def health(self) -> AdapterHealth:
        ...

    def start(self, *, observed_time: datetime) -> AdapterLifecycleResult:
        """Start adapter processing without claiming source availability."""

    def stop(self, *, observed_time: datetime) -> AdapterLifecycleResult:
        """Stop adapter processing explicitly."""

    def observe(self) -> tuple[AdapterObservation, ...]:
        """Return provider-neutral observations for the current batch."""


class DeterministicFakeAdapter:
    """Small local adapter fixture with no clock, network, or retry behavior."""

    def __init__(
        self,
        *,
        identity: AdapterIdentity,
        capabilities: AdapterCapabilities,
        observations: tuple[AdapterObservation, ...] = (),
    ) -> None:
        self._identity = identity
        self._capabilities = capabilities
        self._observations = self._validate_observations(observations)
        self._lifecycle_state = AdapterLifecycleState.CREATED
        self._health = AdapterHealth(AdapterHealthStatus.UNKNOWN)

    @property
    def identity(self) -> AdapterIdentity:
        return self._identity

    @property
    def capabilities(self) -> AdapterCapabilities:
        return self._capabilities

    @property
    def lifecycle_state(self) -> AdapterLifecycleState:
        return self._lifecycle_state

    @property
    def health(self) -> AdapterHealth:
        return self._health

    def start(self, *, observed_time: datetime) -> AdapterLifecycleResult:
        _require_aware_datetime(observed_time)
        if self._lifecycle_state is AdapterLifecycleState.FAILED:
            raise RuntimeError("failed adapter requires explicit replacement")
        if self._lifecycle_state is AdapterLifecycleState.STARTED:
            raise RuntimeError("adapter is already started")
        self._lifecycle_state = AdapterLifecycleState.STARTED
        return self._lifecycle_result(observed_time)

    def stop(self, *, observed_time: datetime) -> AdapterLifecycleResult:
        _require_aware_datetime(observed_time)
        if self._lifecycle_state is AdapterLifecycleState.FAILED:
            raise RuntimeError("failed adapter cannot be stopped as a healthy adapter")
        if self._lifecycle_state is AdapterLifecycleState.STOPPED:
            raise RuntimeError("adapter is already stopped")
        self._lifecycle_state = AdapterLifecycleState.STOPPED
        return self._lifecycle_result(observed_time)

    def observe(self) -> tuple[AdapterObservation, ...]:
        if self._lifecycle_state is not AdapterLifecycleState.STARTED:
            raise RuntimeError("adapter must be started before observation")
        return self._observations

    def failure_observation(
        self,
        *,
        observed_time: datetime,
        reason: str,
        cursor: SequenceValue = None,
    ) -> AdapterObservation:
        """Create an explicit failure observation for P02-T02."""

        _require_aware_datetime(observed_time)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string")
        return AdapterObservation(
            source_id=self.identity.source_id,
            kind=ObservationKind.FAILURE,
            observed_time=observed_time,
            cursor=cursor,
            failure_reason=reason,
        )

    def mark_health(
        self,
        *,
        status: AdapterHealthStatus,
        observed_time: datetime,
        reason: str | None = None,
    ) -> AdapterHealth:
        """Record explicit adapter health without changing source health."""

        _require_aware_datetime(observed_time)
        if not isinstance(status, AdapterHealthStatus):
            raise ValueError("status must be an AdapterHealthStatus")
        if status is AdapterHealthStatus.FAILED and (
            not isinstance(reason, str) or not reason.strip()
        ):
            raise ValueError("failed health requires a reason")
        self._health = AdapterHealth(status, observed_time, reason)
        if status is AdapterHealthStatus.FAILED:
            self._lifecycle_state = AdapterLifecycleState.FAILED
        return self._health

    def _lifecycle_result(self, observed_time: datetime) -> AdapterLifecycleResult:
        return AdapterLifecycleResult(
            identity=self.identity,
            state=self.lifecycle_state,
            health=self.health,
            observed_time=observed_time,
        )

    def _validate_observations(
        self,
        observations: tuple[AdapterObservation, ...],
    ) -> tuple[AdapterObservation, ...]:
        if not isinstance(observations, tuple):
            raise TypeError("observations must be a tuple of AdapterObservation values")
        if not all(isinstance(item, AdapterObservation) for item in observations):
            raise TypeError("provider-specific values cannot cross the adapter boundary")
        if any(item.source_id != self.identity.source_id for item in observations):
            raise ValueError("observation source_id must match adapter source_id")
        return observations


def _require_aware_datetime(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("observed_time must be a timezone-aware datetime")