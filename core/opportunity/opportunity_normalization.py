"""Deterministic P05-T02 opportunity-candidate normalization boundary.

This module exposes the already-validated P05-T01 candidate as an immutable,
versioned normalized representation.  It does not score, rank, weight,
predict, decide, authorize, execute, or perform external I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.opportunity.opportunity_candidate import (
    OpportunityCandidate,
    OpportunityCandidateState,
    OpportunityUpstreamReference,
    P05_T01_CONTRACT_VERSION,
)


P05_T02_CONTRACT_VERSION = "p05-t02-v1"


@dataclass(frozen=True)
class NormalizedOpportunityCandidate:
    """Immutable normalized representation of one P05-T01 candidate."""

    candidate: OpportunityCandidate
    contract_version: str = P05_T02_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.candidate, OpportunityCandidate):
                raise ValueError(
                    "candidate must be an OpportunityCandidate value"
                )
            _require_text(self.contract_version, "contract_version")
            if self.contract_version != P05_T02_CONTRACT_VERSION:
                raise ValueError("unsupported P05-T02 contract version")
            if self.candidate.contract_version != P05_T01_CONTRACT_VERSION:
                raise ValueError("candidate requires the P05-T01 contract")

            # Touch the complete source representation and digest so a
            # malformed object cannot cross this boundary silently.
            representation = self.candidate.canonical_representation
            if representation != self.candidate.deterministic_representation:
                raise ValueError("candidate representation is not deterministic")
            _require_text(self.candidate.representation_digest, "candidate digest")
        except (AttributeError, TypeError, ValueError) as error:
            if isinstance(error, ValueError) and str(error).startswith(
                ("candidate must", "unsupported", "candidate requires")
            ):
                raise
            raise ValueError("candidate must be a valid P05-T01 candidate") from error

    @classmethod
    def from_candidate(
        cls,
        candidate: OpportunityCandidate,
    ) -> NormalizedOpportunityCandidate:
        """Normalize one validated P05-T01 candidate without mutating it."""

        return cls(candidate=candidate)

    @property
    def candidate_id(self) -> str:
        return self.candidate.candidate_id

    @property
    def chain_id(self) -> str:
        return self.candidate.chain_id

    @property
    def token_identity(self) -> str:
        return self.candidate.token_identity

    @property
    def reference_time(self) -> datetime:
        return self.candidate.reference_time

    @property
    def state(self) -> OpportunityCandidateState:
        return self.candidate.state

    @property
    def eligibility(self) -> Any:
        return self.candidate.eligibility

    @property
    def signal_snapshot(self) -> Any:
        return self.candidate.signal_snapshot

    @property
    def feature_snapshots(self) -> tuple[Any, ...]:
        return self.candidate.feature_snapshots

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return self.candidate.reason_codes

    @property
    def analytical_context(self) -> Mapping[str, Any]:
        return self.candidate.analytical_context

    @property
    def upstream_references(self) -> tuple[OpportunityUpstreamReference, ...]:
        return self.candidate.upstream_references

    @property
    def source_contract_version(self) -> str:
        """The preserved contract version of the consumed candidate."""

        return self.candidate.contract_version

    @property
    def candidate_representation_digest(self) -> str:
        """The preserved digest of the consumed P05-T01 candidate."""

        return self.candidate.representation_digest

    @property
    def upstream_contract_versions(self) -> tuple[str, ...]:
        return self.candidate.upstream_contract_versions

    @property
    def upstream_representation_digests(self) -> tuple[str, ...]:
        return self.candidate.upstream_representation_digests

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        """Return the immutable representation used for deterministic hashing."""

        candidate = self.candidate.canonical_representation
        return _freeze(
            {
                "candidate_id": candidate["candidate_id"],
                "chain_id": candidate["chain_id"],
                "token_identity": candidate["token_identity"],
                "reference_time": candidate["reference_time"],
                "state": candidate["state"],
                "reason_codes": candidate["reason_codes"],
                "eligibility": candidate["eligibility"],
                "signal_snapshot": candidate["signal_snapshot"],
                "feature_snapshots": candidate["feature_snapshots"],
                "analytical_context": candidate["analytical_context"],
                "upstream_references": candidate["upstream_references"],
                "candidate_representation_digest": self.candidate_representation_digest,
                "source_contract_version": self.source_contract_version,
                "contract_version": self.contract_version,
            }
        )

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.representation_digest


def normalize_opportunity_candidate(
    candidate: OpportunityCandidate,
) -> NormalizedOpportunityCandidate:
    """Normalize a P05-T01 candidate without adding scoring semantics."""

    return NormalizedOpportunityCandidate.from_candidate(candidate)


normalize_candidate = normalize_opportunity_candidate
OpportunityCandidateNormalization = NormalizedOpportunityCandidate


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime values must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(
        f"{type(value).__name__} cannot be deterministically serialized"
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


__all__ = [
    "NormalizedOpportunityCandidate",
    "OpportunityCandidateNormalization",
    "P05_T02_CONTRACT_VERSION",
    "normalize_candidate",
    "normalize_opportunity_candidate",
]