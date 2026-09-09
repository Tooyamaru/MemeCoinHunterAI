"""Pure Authority B correction/supersession lineage boundary.

This module deliberately owns only immutable lineage facts, their canonical
representations, explicit comparison snapshots, and lifecycle-scoped graph
validation.  It has no persistence, clock, provider, network, T07-internal,
economic, or execution dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping
import unicodedata


AUTHORITY_B_CONTRACT_VERSION = "p08-authority-b-lineage-v1"
AUTHORITY_B_POLICY_VERSION = "p08-authority-b-policy-v1"
AUTHORITY_B_SNAPSHOT_CONTRACT_VERSION = "p08-authority-b-lineage-snapshot-v1"

PROVENANCE_STAGES = (
    "p06_decision_intent",
    "p07_simulation_input",
    "p07_simulation_result",
    "p07_history",
    "p08_t01_observation",
    "p08_t02_dataset",
    "p08_t03_interpretation",
    "p08_t04_evaluation",
    "p08_t05_snapshot",
    "p08_t06_readiness",
    "authority_a_identity",
)

_FACT_DOMAIN = b"p08-authority-b:fact:v1\0"
_EDGE_DOMAIN = b"p08-authority-b:edge:v1\0"
_SNAPSHOT_DOMAIN = b"p08-authority-b:snapshot:v1\0"
_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z", re.ASCII)
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class LineageType(str, Enum):
    CORRECTION = "correction"
    SUPERSESSION = "supersession"


class AuthorityBFailure(str, Enum):
    MALFORMED_FACT = "MALFORMED_FACT"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    INVALID_LIFECYCLE = "INVALID_LIFECYCLE"
    MISSING_ENDPOINT = "MISSING_ENDPOINT"
    CROSS_LIFECYCLE_REFERENCE = "CROSS_LIFECYCLE_REFERENCE"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"
    LINEAGE_SELF_REFERENCE = "LINEAGE_SELF_REFERENCE"
    LINEAGE_CYCLE = "LINEAGE_CYCLE"
    MERGE_UNSUPPORTED = "MERGE_UNSUPPORTED"
    LINEAGE_BRANCH_CONFLICT = "LINEAGE_BRANCH_CONFLICT"
    CONTRADICTORY_LINEAGE = "CONTRADICTORY_LINEAGE"
    PROVENANCE_FAILURE = "PROVENANCE_FAILURE"
    DETERMINISM_FAILURE = "DETERMINISM_FAILURE"
    DIGEST_FAILURE = "DIGEST_FAILURE"


AuthorityBFailureReason = AuthorityBFailure

class DuplicateStatus(str, Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"


_FAILURE_PRECEDENCE = (
    AuthorityBFailure.MALFORMED_FACT,
    AuthorityBFailure.INVALID_IDENTITY,
    AuthorityBFailure.INVALID_LIFECYCLE,
    AuthorityBFailure.MISSING_ENDPOINT,
    AuthorityBFailure.CROSS_LIFECYCLE_REFERENCE,
    AuthorityBFailure.CONFLICTING_DUPLICATE,
    AuthorityBFailure.LINEAGE_SELF_REFERENCE,
    AuthorityBFailure.LINEAGE_CYCLE,
    AuthorityBFailure.MERGE_UNSUPPORTED,
    AuthorityBFailure.LINEAGE_BRANCH_CONFLICT,
    AuthorityBFailure.CONTRADICTORY_LINEAGE,
    AuthorityBFailure.PROVENANCE_FAILURE,
    AuthorityBFailure.DETERMINISM_FAILURE,
    AuthorityBFailure.DIGEST_FAILURE,
)

T07_FAILURE_REASON_BY_AUTHORITY_B_FAILURE = {
    AuthorityBFailure.MALFORMED_FACT: "MISSING_REQUIRED_INPUT",
    AuthorityBFailure.INVALID_IDENTITY: "MISSING_REQUIRED_INPUT",
    AuthorityBFailure.INVALID_LIFECYCLE: "CONFLICTING_INPUT",
    AuthorityBFailure.MISSING_ENDPOINT: "MISSING_REQUIRED_INPUT",
    AuthorityBFailure.CROSS_LIFECYCLE_REFERENCE: "CONFLICTING_INPUT",
    AuthorityBFailure.CONFLICTING_DUPLICATE: "CONFLICTING_INPUT",
    AuthorityBFailure.LINEAGE_SELF_REFERENCE: "CONFLICTING_INPUT",
    AuthorityBFailure.LINEAGE_CYCLE: "CONFLICTING_INPUT",
    AuthorityBFailure.MERGE_UNSUPPORTED: "UNRESOLVED_RESIDUAL",
    AuthorityBFailure.LINEAGE_BRANCH_CONFLICT: "CONFLICTING_INPUT",
    AuthorityBFailure.CONTRADICTORY_LINEAGE: "CONFLICTING_INPUT",
    AuthorityBFailure.PROVENANCE_FAILURE: "PROVENANCE_LINKAGE_FAILURE",
    AuthorityBFailure.DETERMINISM_FAILURE: "UNRESOLVED_RESIDUAL",
    AuthorityBFailure.DIGEST_FAILURE: "DIGEST_FAILURE",
}


class _Malformed(ValueError):
    pass


def _nfc(value: str) -> str:
    if not isinstance(value, str):
        raise _Malformed("text is required")
    normalized = unicodedata.normalize("NFC", value)
    for character in normalized:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise _Malformed("unpaired surrogate is invalid")
    return normalized


def _identity(value: Any, name: str) -> str:
    normalized = _nfc(value)
    if not normalized:
        raise _Malformed(f"{name} must be non-empty")
    return normalized


def _version(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise _Malformed(f"{name} is not a valid VersionId")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise _Malformed(f"{name} is not a lowercase SHA-256 digest")
    return value


def _lineage_type(value: Any) -> str:
    if isinstance(value, LineageType):
        value = value.value
    if value not in (LineageType.CORRECTION.value, LineageType.SUPERSESSION.value):
        raise _Malformed("lineage_type must be correction or supersession")
    return value


def _normalize_json(value: Any, *, allow_null: bool, reject_numbers: bool) -> Any:
    if value is None:
        if not allow_null:
            raise _Malformed("semantic null is not permitted")
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if reject_numbers:
            raise _Malformed("numeric JSON tokens are not permitted")
        return value
    if isinstance(value, str):
        return _nfc(value)
    if isinstance(value, Enum):
        return _normalize_json(
            value.value, allow_null=allow_null, reject_numbers=reject_numbers
        )
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, child in value.items():
            normalized_key = _nfc(key) if isinstance(key, str) else _nfc(str(key))
            if normalized_key in normalized:
                raise _Malformed("canonical key collision")
            normalized[normalized_key] = _normalize_json(
                child, allow_null=allow_null, reject_numbers=reject_numbers
            )
        return {
            key: normalized[key]
            for key in sorted(normalized, key=lambda item: tuple(map(ord, item)))
        }
    if isinstance(value, (list, tuple)):
        return [
            _normalize_json(item, allow_null=allow_null, reject_numbers=reject_numbers)
            for item in value
        ]
    if isinstance(value, MappingProxyType):
        return _normalize_json(
            dict(value), allow_null=allow_null, reject_numbers=reject_numbers
        )
    raise _Malformed(f"{type(value).__name__} cannot be serialized canonically")


def canonical_json(value: Any, *, allow_null: bool = True) -> str:
    """Return the locked compact JSON text for a value.

    Authority B calls this with ``allow_null=False`` and rejects numeric
    tokens.  The public default is useful for inspecting canonical JSON
    primitives, including the required lowercase ``null`` token.
    """

    normalized = _normalize_json(
        value, allow_null=allow_null, reject_numbers=True
    )
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
        allow_nan=False,
    )


def canonical_json_bytes(value: Any, *, allow_null: bool = True) -> bytes:
    return canonical_json(value, allow_null=allow_null).encode("utf-8")


def _b_json(value: Any) -> str:
    return canonical_json(value, allow_null=False)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(canonical_json_bytes(value, allow_null=False))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


@dataclass(frozen=True, slots=True)
class ProvenanceLink:
    stage: str
    record_identity: str
    record_digest: str
    authority_identity: str

    def __post_init__(self) -> None:
        if self.stage not in PROVENANCE_STAGES:
            raise _Malformed("unsupported provenance stage")
        object.__setattr__(self, "record_identity", _identity(
            self.record_identity, "record_identity"
        ))
        object.__setattr__(self, "record_digest", _digest(
            self.record_digest, "record_digest"
        ))
        object.__setattr__(self, "authority_identity", _identity(
            self.authority_identity, "authority_identity"
        ))

    @property
    def canonical_representation(self) -> Mapping[str, str]:
        return _freeze({
            "stage": self.stage,
            "record_identity": self.record_identity,
            "record_digest": self.record_digest,
            "authority_identity": self.authority_identity,
        })

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProvenanceLink":
        if set(value) != {
            "stage", "record_identity", "record_digest", "authority_identity"
        }:
            raise _Malformed("provenance link fields are not exact")
        return cls(**dict(value))


def _provenance(value: Any) -> tuple[ProvenanceLink, ...]:
    if not isinstance(value, (list, tuple)) or len(value) != len(PROVENANCE_STAGES):
        raise _Malformed("complete provenance is required")
    links = tuple(
        link if isinstance(link, ProvenanceLink) else ProvenanceLink.from_mapping(link)
        for link in value
    )
    if tuple(link.stage for link in links) != PROVENANCE_STAGES:
        raise _Malformed("provenance stages must be complete and ordered")
    return links


def _identity_projection(
    contract_version: str,
    policy_version: str,
    lifecycle_identity: str,
    predecessor_result_identity: str,
    successor_result_identity: str,
    lineage_type: str,
) -> list[str]:
    return [
        contract_version,
        policy_version,
        lifecycle_identity,
        predecessor_result_identity,
        successor_result_identity,
        lineage_type,
    ]


def derive_lineage_fact_identity(
    *,
    contract_version: str,
    lineage_policy_version: str,
    lifecycle_identity: str,
    predecessor_result_identity: str,
    successor_result_identity: str,
    lineage_type: str | LineageType,
) -> str:
    projection = _identity_projection(
        _version(contract_version, "contract_version"),
        _version(lineage_policy_version, "lineage_policy_version"),
        _identity(lifecycle_identity, "lifecycle_identity"),
        _identity(predecessor_result_identity, "predecessor_result_identity"),
        _identity(successor_result_identity, "successor_result_identity"),
        _lineage_type(lineage_type),
    )
    return _sha256_bytes(_FACT_DOMAIN + canonical_json_bytes(projection, allow_null=False))


def derive_lineage_edge_identity(**kwargs: Any) -> str:
    projection = _identity_projection(
        _version(kwargs["contract_version"], "contract_version"),
        _version(kwargs["lineage_policy_version"], "lineage_policy_version"),
        _identity(kwargs["lifecycle_identity"], "lifecycle_identity"),
        _identity(kwargs["predecessor_result_identity"], "predecessor_result_identity"),
        _identity(kwargs["successor_result_identity"], "successor_result_identity"),
        _lineage_type(kwargs["lineage_type"]),
    )
    return _sha256_bytes(_EDGE_DOMAIN + canonical_json_bytes(projection, allow_null=False))


@dataclass(frozen=True, slots=True)
class LineageFact:
    contract_version: str
    lineage_policy_version: str
    lifecycle_identity: str
    predecessor_result_identity: str
    successor_result_identity: str
    lineage_type: str | LineageType
    authority_identity: str
    provenance: tuple[ProvenanceLink, ...]
    lineage_fact_identity: str | None = None

    def __post_init__(self) -> None:
        if self.contract_version != AUTHORITY_B_CONTRACT_VERSION:
            raise _Malformed("unsupported contract version")
        if self.lineage_policy_version != AUTHORITY_B_POLICY_VERSION:
            raise _Malformed("unsupported policy version")
        for name in (
            "lifecycle_identity",
            "predecessor_result_identity",
            "successor_result_identity",
            "authority_identity",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))
        object.__setattr__(self, "lineage_type", _lineage_type(self.lineage_type))
        object.__setattr__(self, "provenance", _provenance(self.provenance))
        expected = derive_lineage_fact_identity(
            contract_version=self.contract_version,
            lineage_policy_version=self.lineage_policy_version,
            lifecycle_identity=self.lifecycle_identity,
            predecessor_result_identity=self.predecessor_result_identity,
            successor_result_identity=self.successor_result_identity,
            lineage_type=self.lineage_type,
        )
        if self.lineage_fact_identity is not None:
            supplied = _digest(self.lineage_fact_identity, "lineage_fact_identity")
            if supplied != expected:
                raise _Malformed("lineage fact identity does not match")
        object.__setattr__(self, "lineage_fact_identity", expected)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LineageFact":
        required = {
            "contract_version", "lineage_policy_version", "lifecycle_identity",
            "predecessor_result_identity", "successor_result_identity",
            "lineage_type", "authority_identity", "provenance",
        }
        allowed = required | {"lineage_fact_identity"}
        if set(value) != allowed and set(value) != required:
            raise _Malformed("fact fields are not exact")
        return cls(**dict(value))

    @property
    def identity_projection(self) -> tuple[str, ...]:
        return (
            self.contract_version,
            self.lineage_policy_version,
            self.lifecycle_identity,
            self.predecessor_result_identity,
            self.successor_result_identity,
            self.lineage_type,
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({
            "contract_version": self.contract_version,
            "lineage_policy_version": self.lineage_policy_version,
            "lifecycle_identity": self.lifecycle_identity,
            "predecessor_result_identity": self.predecessor_result_identity,
            "successor_result_identity": self.successor_result_identity,
            "lineage_type": self.lineage_type,
            "authority_identity": self.authority_identity,
            "provenance": tuple(
                link.canonical_representation for link in self.provenance
            ),
            "lineage_fact_identity": self.lineage_fact_identity,
        })

    @property
    def canonical_bytes(self) -> bytes:
        return _b_json(self.canonical_representation).encode("utf-8")


@dataclass(frozen=True, slots=True)
class LineageEdge:
    contract_version: str
    lineage_policy_version: str
    lifecycle_identity: str
    predecessor_result_identity: str
    successor_result_identity: str
    lineage_type: str | LineageType
    lineage_fact_identity: str
    authority_identity: str
    provenance: tuple[ProvenanceLink, ...]
    lineage_edge_identity: str | None = None
    edge_digest: str | None = None

    def __post_init__(self) -> None:
        fact = LineageFact(
            contract_version=self.contract_version,
            lineage_policy_version=self.lineage_policy_version,
            lifecycle_identity=self.lifecycle_identity,
            predecessor_result_identity=self.predecessor_result_identity,
            successor_result_identity=self.successor_result_identity,
            lineage_type=self.lineage_type,
            authority_identity=self.authority_identity,
            provenance=self.provenance,
            lineage_fact_identity=self.lineage_fact_identity,
        )
        object.__setattr__(self, "contract_version", fact.contract_version)
        object.__setattr__(self, "lineage_policy_version", fact.lineage_policy_version)
        object.__setattr__(self, "lifecycle_identity", fact.lifecycle_identity)
        object.__setattr__(
            self, "predecessor_result_identity", fact.predecessor_result_identity
        )
        object.__setattr__(
            self, "successor_result_identity", fact.successor_result_identity
        )
        object.__setattr__(self, "lineage_type", fact.lineage_type)
        object.__setattr__(self, "lineage_fact_identity", fact.lineage_fact_identity)
        object.__setattr__(self, "authority_identity", fact.authority_identity)
        object.__setattr__(self, "provenance", fact.provenance)
        expected_identity = derive_lineage_edge_identity(
            contract_version=fact.contract_version,
            lineage_policy_version=fact.lineage_policy_version,
            lifecycle_identity=fact.lifecycle_identity,
            predecessor_result_identity=fact.predecessor_result_identity,
            successor_result_identity=fact.successor_result_identity,
            lineage_type=fact.lineage_type,
        )
        if self.lineage_edge_identity is not None and (
            _digest(self.lineage_edge_identity, "lineage_edge_identity")
            != expected_identity
        ):
            raise _Malformed("lineage edge identity does not match")
        object.__setattr__(self, "lineage_edge_identity", expected_identity)
        expected_digest = _sha256_json(self._digest_representation())
        if self.edge_digest is not None and (
            _digest(self.edge_digest, "edge_digest") != expected_digest
        ):
            raise _Malformed("edge digest does not match")
        object.__setattr__(self, "edge_digest", expected_digest)

    @classmethod
    def from_fact(cls, fact: LineageFact) -> "LineageEdge":
        return cls(
            contract_version=fact.contract_version,
            lineage_policy_version=fact.lineage_policy_version,
            lifecycle_identity=fact.lifecycle_identity,
            predecessor_result_identity=fact.predecessor_result_identity,
            successor_result_identity=fact.successor_result_identity,
            lineage_type=fact.lineage_type,
            lineage_fact_identity=fact.lineage_fact_identity,
            authority_identity=fact.authority_identity,
            provenance=fact.provenance,
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({
            "contract_version": self.contract_version,
            "lineage_policy_version": self.lineage_policy_version,
            "lifecycle_identity": self.lifecycle_identity,
            "predecessor_result_identity": self.predecessor_result_identity,
            "successor_result_identity": self.successor_result_identity,
            "lineage_type": self.lineage_type,
            "lineage_fact_identity": self.lineage_fact_identity,
            "authority_identity": self.authority_identity,
            "provenance": tuple(
                link.canonical_representation for link in self.provenance
            ),
            "lineage_edge_identity": self.lineage_edge_identity,
            "edge_digest": self.edge_digest,
        })

    def _digest_representation(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "lineage_policy_version": self.lineage_policy_version,
            "lifecycle_identity": self.lifecycle_identity,
            "predecessor_result_identity": self.predecessor_result_identity,
            "successor_result_identity": self.successor_result_identity,
            "lineage_type": self.lineage_type,
            "lineage_fact_identity": self.lineage_fact_identity,
            "authority_identity": self.authority_identity,
            "provenance": tuple(
                link.canonical_representation for link in self.provenance
            ),
            "lineage_edge_identity": self.lineage_edge_identity,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return _b_json(self.canonical_representation).encode("utf-8")


def _coerce_fact(value: Any) -> LineageFact:
    if isinstance(value, LineageFact):
        return value
    if isinstance(value, Mapping):
        return LineageFact.from_mapping(value)
    raise _Malformed("LineageFact is required")


def _fact_integrity(fact: LineageFact) -> AuthorityBFailure | None:
    try:
        expected_identity = derive_lineage_fact_identity(
            contract_version=fact.contract_version,
            lineage_policy_version=fact.lineage_policy_version,
            lifecycle_identity=fact.lifecycle_identity,
            predecessor_result_identity=fact.predecessor_result_identity,
            successor_result_identity=fact.successor_result_identity,
            lineage_type=fact.lineage_type,
        )
        if fact.lineage_fact_identity != expected_identity:
            return AuthorityBFailure.INVALID_IDENTITY
        _b_json(fact.canonical_representation)
        return None
    except (TypeError, ValueError, UnicodeError):
        return AuthorityBFailure.DIGEST_FAILURE


@dataclass(frozen=True, slots=True)
class AuthoritativeLineageFactSetSnapshot:
    snapshot_contract_version: str
    lifecycle_identity: str
    members: tuple[LineageFact, ...]
    snapshot_identity: str | None = None
    snapshot_digest: str | None = None

    def __post_init__(self) -> None:
        if self.snapshot_contract_version != AUTHORITY_B_SNAPSHOT_CONTRACT_VERSION:
            raise _Malformed("unsupported snapshot contract version")
        object.__setattr__(
            self, "lifecycle_identity", _identity(self.lifecycle_identity, "lifecycle_identity")
        )
        raw_members = tuple(
            member if isinstance(member, LineageFact) else _coerce_fact(member)
            for member in self.members
        )
        if any(member.lifecycle_identity != self.lifecycle_identity for member in raw_members):
            raise _Malformed("snapshot contains mixed lifecycle scope")
        ordered = tuple(sorted(raw_members, key=lambda item: item.lineage_fact_identity))
        if len({item.lineage_fact_identity for item in ordered}) != len(ordered):
            raise _Malformed("snapshot contains duplicate member identities")
        if raw_members != ordered:
            raise _Malformed("snapshot members are not canonically ordered")
        object.__setattr__(self, "members", ordered)
        expected_identity = _sha256_bytes(
            _SNAPSHOT_DOMAIN
            + canonical_json_bytes(self.identity_projection, allow_null=False)
        )
        if self.snapshot_identity is not None and (
            _digest(self.snapshot_identity, "snapshot_identity") != expected_identity
        ):
            raise _Malformed("snapshot identity does not match")
        object.__setattr__(self, "snapshot_identity", expected_identity)
        expected_digest = _sha256_json(self._digest_representation())
        if self.snapshot_digest is not None and (
            _digest(self.snapshot_digest, "snapshot_digest") != expected_digest
        ):
            raise _Malformed("snapshot digest does not match")
        object.__setattr__(self, "snapshot_digest", expected_digest)

    @classmethod
    def from_facts(
        cls, lifecycle_identity: str, facts: Iterable[LineageFact]
    ) -> "AuthoritativeLineageFactSetSnapshot":
        return cls(
            snapshot_contract_version=AUTHORITY_B_SNAPSHOT_CONTRACT_VERSION,
            lifecycle_identity=lifecycle_identity,
            members=tuple(sorted(facts, key=lambda item: item.lineage_fact_identity)),
        )

    @property
    def identity_projection(self) -> Mapping[str, Any]:
        return {
            "snapshot_contract_version": self.snapshot_contract_version,
            "lifecycle_identity": self.lifecycle_identity,
            "members": [
                member.canonical_representation for member in self.members
            ],
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({
            "snapshot_contract_version": self.snapshot_contract_version,
            "lifecycle_identity": self.lifecycle_identity,
            "members": tuple(member.canonical_representation for member in self.members),
            "snapshot_identity": self.snapshot_identity,
            "snapshot_digest": self.snapshot_digest,
        })

    def _digest_representation(self) -> Mapping[str, Any]:
        return {
            "snapshot_contract_version": self.snapshot_contract_version,
            "lifecycle_identity": self.lifecycle_identity,
            "members": tuple(member.canonical_representation for member in self.members),
            "snapshot_identity": self.snapshot_identity,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return _b_json(self.canonical_representation).encode("utf-8")


@dataclass(frozen=True, slots=True)
class T07LineageProjection:
    correction_lineage: tuple[Mapping[str, Any], ...] | None
    supersession_lineage: tuple[Mapping[str, Any], ...] | None

    @property
    def destination_field(self) -> str:
        if self.correction_lineage is not None:
            return "correction_lineage"
        return "supersession_lineage"

    @classmethod
    def from_edge(cls, edge: LineageEdge) -> "T07LineageProjection":
        representation = _freeze(edge.canonical_representation)
        if edge.lineage_type == LineageType.CORRECTION.value:
            return cls((representation,), None)
        return cls(None, (representation,))


@dataclass(frozen=True, slots=True)
class LineageValidationResult:
    accepted: bool
    failure: AuthorityBFailure | None = None
    duplicate_status: DuplicateStatus | None = None
    fact: LineageFact | None = None
    edge: LineageEdge | None = None
    projection: T07LineageProjection | None = None
    terminal_candidate: str | None = None

    @property
    def t07_status(self) -> str:
        return "VALID" if self.accepted else "INVALID_INPUT"

    @property
    def t07_failure_reason(self) -> str | None:
        return (
            None
            if self.failure is None
            else T07_FAILURE_REASON_BY_AUTHORITY_B_FAILURE[self.failure]
        )

    @property
    def failure_reason(self) -> AuthorityBFailure | None:
        return self.failure


@dataclass(frozen=True, slots=True)
class LineageGraphInput:
    lifecycle_identity: str
    result_identities: Mapping[str, str] | tuple[str, ...]
    lineage_facts: tuple[LineageFact, ...]
    snapshot: AuthoritativeLineageFactSetSnapshot
    contract_version: str = AUTHORITY_B_CONTRACT_VERSION
    lineage_policy_version: str = AUTHORITY_B_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "lifecycle_identity", _identity(self.lifecycle_identity, "lifecycle_identity")
        )
        if self.contract_version != AUTHORITY_B_CONTRACT_VERSION:
            raise _Malformed("unsupported contract version")
        if self.lineage_policy_version != AUTHORITY_B_POLICY_VERSION:
            raise _Malformed("unsupported policy version")
        identities = self.result_identities
        if isinstance(identities, Mapping):
            normalized = {
                _identity(key, "result_identity"): _identity(value, "lifecycle_identity")
                for key, value in identities.items()
            }
            object.__setattr__(self, "result_identities", _freeze(normalized))
        else:
            normalized = tuple(_identity(item, "result_identity") for item in identities)
            if len(set(normalized)) != len(normalized):
                raise _Malformed("duplicate result identity")
            object.__setattr__(self, "result_identities", normalized)
        object.__setattr__(
            self,
            "lineage_facts",
            tuple(
                item if isinstance(item, LineageFact) else _coerce_fact(item)
                for item in self.lineage_facts
            ),
        )

    def endpoint_lifecycle(self, identity: str) -> str | None:
        if isinstance(self.result_identities, Mapping):
            return self.result_identities.get(identity)
        return self.lifecycle_identity if identity in self.result_identities else None


def _failure(failure: AuthorityBFailure, *, fact: LineageFact | None = None) -> LineageValidationResult:
    return LineageValidationResult(accepted=False, failure=failure, fact=fact)


def _validate_snapshot(
    snapshot: AuthoritativeLineageFactSetSnapshot | None,
) -> AuthorityBFailure | None:
    if snapshot is None:
        return AuthorityBFailure.DETERMINISM_FAILURE
    try:
        expected_identity = _sha256_bytes(
            _SNAPSHOT_DOMAIN
            + canonical_json_bytes(snapshot.identity_projection, allow_null=False)
        )
        if snapshot.snapshot_identity != expected_identity:
            return AuthorityBFailure.INVALID_IDENTITY
        if snapshot.snapshot_digest != _sha256_json(snapshot._digest_representation()):
            return AuthorityBFailure.DIGEST_FAILURE
        for member in snapshot.members:
            issue = _fact_integrity(member)
            if issue is not None:
                return issue
            if member.lifecycle_identity != snapshot.lifecycle_identity:
                return AuthorityBFailure.CROSS_LIFECYCLE_REFERENCE
        if tuple(member.lineage_fact_identity for member in snapshot.members) != tuple(
            sorted(member.lineage_fact_identity for member in snapshot.members)
        ):
            return AuthorityBFailure.DETERMINISM_FAILURE
        return None
    except (TypeError, ValueError, UnicodeError):
        return AuthorityBFailure.DIGEST_FAILURE


def validate_lineage_fact(
    candidate: LineageFact | Mapping[str, Any],
    snapshot: AuthoritativeLineageFactSetSnapshot | None,
    *,
    lifecycle_identity: str | None = None,
) -> LineageValidationResult:
    try:
        fact = _coerce_fact(candidate)
    except (TypeError, ValueError, UnicodeError):
        return _failure(AuthorityBFailure.MALFORMED_FACT)

    issue = _fact_integrity(fact)
    if issue is not None:
        return _failure(issue, fact=fact)
    if lifecycle_identity is not None:
        try:
            expected_lifecycle = _identity(lifecycle_identity, "lifecycle_identity")
        except (TypeError, ValueError, UnicodeError):
            return _failure(AuthorityBFailure.INVALID_LIFECYCLE, fact=fact)
        if fact.lifecycle_identity != expected_lifecycle:
            return _failure(AuthorityBFailure.INVALID_LIFECYCLE, fact=fact)

    snapshot_issue = _validate_snapshot(snapshot)
    if snapshot_issue is not None:
        return _failure(snapshot_issue, fact=fact)
    assert snapshot is not None
    if fact.lifecycle_identity != snapshot.lifecycle_identity:
        return _failure(AuthorityBFailure.CROSS_LIFECYCLE_REFERENCE, fact=fact)

    matches = [
        member for member in snapshot.members
        if member.lineage_fact_identity == fact.lineage_fact_identity
    ]
    if len(matches) > 1:
        return _failure(AuthorityBFailure.DETERMINISM_FAILURE, fact=fact)
    if matches:
        if matches[0].canonical_bytes != fact.canonical_bytes:
            return LineageValidationResult(
                accepted=False,
                failure=AuthorityBFailure.CONFLICTING_DUPLICATE,
                duplicate_status=DuplicateStatus.CONFLICTING_DUPLICATE,
                fact=fact,
            )
        edge = LineageEdge.from_fact(matches[0])
        return LineageValidationResult(
            accepted=True,
            duplicate_status=DuplicateStatus.EXACT_DUPLICATE,
            fact=matches[0],
            edge=edge,
            projection=T07LineageProjection.from_edge(edge),
        )

    edge = LineageEdge.from_fact(fact)
    return LineageValidationResult(
        accepted=True,
        fact=fact,
        edge=edge,
        projection=T07LineageProjection.from_edge(edge),
    )


def _choose_failure(failures: set[AuthorityBFailure]) -> AuthorityBFailure | None:
    for failure in _FAILURE_PRECEDENCE:
        if failure in failures:
            return failure
    return None


def _detect_cycle(edges: Mapping[str, str]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        successor = edges.get(node)
        if successor is not None and visit(successor):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in set(edges) | set(edges.values()))


def validate_lineage_graph(graph: LineageGraphInput) -> LineageValidationResult:
    try:
        snapshot_issue = _validate_snapshot(graph.snapshot)
    except (TypeError, ValueError, UnicodeError):
        return _failure(AuthorityBFailure.DETERMINISM_FAILURE)
    if snapshot_issue is not None:
        return _failure(snapshot_issue)

    failures: set[AuthorityBFailure] = set()
    facts: list[LineageFact] = []
    by_identity: dict[str, LineageFact] = {}
    for candidate in graph.lineage_facts:
        try:
            fact = _coerce_fact(candidate)
        except (TypeError, ValueError, UnicodeError):
            failures.add(AuthorityBFailure.MALFORMED_FACT)
            continue
        facts.append(fact)
        if fact.lineage_fact_identity in by_identity:
            if by_identity[fact.lineage_fact_identity].canonical_bytes != fact.canonical_bytes:
                failures.add(AuthorityBFailure.CONFLICTING_DUPLICATE)
            else:
                failures.add(AuthorityBFailure.DETERMINISM_FAILURE)
        else:
            by_identity[fact.lineage_fact_identity] = fact
        issue = _fact_integrity(fact)
        if issue is not None:
            failures.add(issue)
        if fact.lifecycle_identity != graph.lifecycle_identity:
            failures.add(AuthorityBFailure.INVALID_LIFECYCLE)

    if graph.snapshot.lifecycle_identity != graph.lifecycle_identity:
        failures.add(AuthorityBFailure.CROSS_LIFECYCLE_REFERENCE)

    endpoint_lifecycles = graph.result_identities
    successors: dict[str, list[str]] = {}
    predecessors: dict[str, list[str]] = {}
    edge_by_pair: dict[tuple[str, str], LineageFact] = {}
    for fact in facts:
        predecessor = fact.predecessor_result_identity
        successor = fact.successor_result_identity
        predecessor_lifecycle = graph.endpoint_lifecycle(predecessor)
        successor_lifecycle = graph.endpoint_lifecycle(successor)
        if predecessor_lifecycle is None or successor_lifecycle is None:
            failures.add(AuthorityBFailure.MISSING_ENDPOINT)
        else:
            if (
                predecessor_lifecycle != graph.lifecycle_identity
                or successor_lifecycle != graph.lifecycle_identity
            ):
                failures.add(AuthorityBFailure.CROSS_LIFECYCLE_REFERENCE)
        if predecessor == successor:
            failures.add(AuthorityBFailure.LINEAGE_SELF_REFERENCE)
        successors.setdefault(predecessor, []).append(successor)
        predecessors.setdefault(successor, []).append(predecessor)
        pair = (predecessor, successor)
        previous = edge_by_pair.get(pair)
        if previous is not None and (
            previous.lineage_type != fact.lineage_type
            or previous.canonical_bytes != fact.canonical_bytes
        ):
            failures.add(AuthorityBFailure.CONTRADICTORY_LINEAGE)
        else:
            edge_by_pair[pair] = fact

    direct_successor_edges = [
        successor_list for successor_list in successors.values()
        if len(set(successor_list)) > 1
    ]
    if direct_successor_edges:
        failures.add(AuthorityBFailure.LINEAGE_BRANCH_CONFLICT)
    if any(len(set(items)) > 1 for items in predecessors.values()):
        failures.add(AuthorityBFailure.MERGE_UNSUPPORTED)

    unique_successors = {
        predecessor: values[0]
        for predecessor, values in successors.items()
        if len(set(values)) == 1
    }
    if _detect_cycle(unique_successors):
        failures.add(AuthorityBFailure.LINEAGE_CYCLE)

    # Snapshot comparison is explicit and contextual.  It never changes fact
    # identity; it only contributes duplicate/conflict status.
    for fact in facts:
        result = validate_lineage_fact(fact, graph.snapshot, lifecycle_identity=graph.lifecycle_identity)
        if result.failure is not None:
            failures.add(result.failure)

    selected_failure = _choose_failure(failures)
    if selected_failure is not None:
        return _failure(selected_failure)

    identities = (
        set(endpoint_lifecycles)
        if isinstance(endpoint_lifecycles, Mapping)
        else set(endpoint_lifecycles)
    )
    terminal_candidates = sorted(identities - set(unique_successors))
    if len(terminal_candidates) != 1:
        return _failure(AuthorityBFailure.DETERMINISM_FAILURE)

    edges = tuple(LineageEdge.from_fact(fact) for fact in facts)
    return LineageValidationResult(
        accepted=True,
        fact=facts[0] if len(facts) == 1 else None,
        edge=edges[0] if len(edges) == 1 else None,
        projection=(
            T07LineageProjection.from_edge(edges[0]) if len(edges) == 1 else None
        ),
        terminal_candidate=terminal_candidates[0],
    )


def project_t07_lineage(
    fact: LineageFact | Mapping[str, Any],
    snapshot: AuthoritativeLineageFactSetSnapshot,
) -> T07LineageProjection | None:
    result = validate_lineage_fact(fact, snapshot)
    return result.projection if result.accepted else None


def create_lineage_edge(fact: LineageFact) -> LineageEdge:
    return LineageEdge.from_fact(fact)


validate_authority_b_fact = validate_lineage_fact
validate_authority_b_graph = validate_lineage_graph


__all__ = [
    "AUTHORITY_B_CONTRACT_VERSION",
    "AUTHORITY_B_POLICY_VERSION",
    "AUTHORITY_B_SNAPSHOT_CONTRACT_VERSION",
    "AuthorityBFailure",
    "AuthorityBFailureReason",
    "AuthoritativeLineageFactSetSnapshot",
    "DuplicateStatus",
    "LineageEdge",
    "LineageFact",
    "LineageGraphInput",
    "LineageType",
    "LineageValidationResult",
    "PROVENANCE_STAGES",
    "ProvenanceLink",
    "T07_FAILURE_REASON_BY_AUTHORITY_B_FAILURE",
    "T07LineageProjection",
    "canonical_json",
    "canonical_json_bytes",
    "create_lineage_edge",
    "derive_lineage_edge_identity",
    "derive_lineage_fact_identity",
    "project_t07_lineage",
    "validate_authority_b_fact",
    "validate_authority_b_graph",
    "validate_lineage_fact",
    "validate_lineage_graph",
]