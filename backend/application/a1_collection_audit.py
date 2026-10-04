"""Explicit offline A1 audit capture and append-only lifecycle attachment.

Readback returns evidence, never reconstructed active owners or an executable
case. RTI-03 keeps its closed artifact vocabulary and its own transaction.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.application.paper_lifecycle_persistence import (
    PaperLifecyclePersistenceOutcome, _build_bundle, _compare_existing,
    _snapshot_bundle, validate_lifecycle_result_digest,
)
from backend.application.prepared_paper_case_invocation import (
    P01Oci01Result, PreparedPaperInvocationOutcome,
)
from backend.application.market_to_opportunity_composition import _canonical as rti11_canonical
from backend.application.prevalidated_risk_capital_suffix_caller import PrevalidatedSuffixOutcome
from backend.core.database import DatabaseRuntime, DatabaseState
from backend.core.repositories import A1CollectionAuditRepository, PaperLifecycleRepository
from core.data.a1_operational_collection import _digest as collection_digest
from core.data.a1_rti11_collection import (
    DiagnosticCollectionPacket, DiagnosticSafetyReplay, ExactPoolBinding,
    RTI11DiagnosticReplay, ReplayLineageRecord, VERSION as PACKET_VERSION,
    _request_digest,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus, PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY,
)
from core.runtime.controlled_paper_lifecycle import ControlledPaperLifecycleOutcome

CONTRACT_VERSION = "a1-durable-collection-audit-v1"
MAX_PAYLOAD_BYTES = 256 * 1024 * 1024
_IDENTITY_FIELDS = (
    "lifecycle_result_digest", "collection_id", "packet_digest",
    "collection_digest", "selected_rti11_digest",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _encode(value, blobs):
    """Lossless raw bodies, deduplicated separately from owner projections."""
    if type(value) is bytes:
        digest = hashlib.sha256(value).hexdigest()
        blobs[digest] = {"length": len(value), "base64": base64.b64encode(value).decode("ascii")}
        return {"$bytes": digest}
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _encode(getattr(value, f.name), blobs) for f in fields(value)}
    if isinstance(value, datetime):
        _require(value.tzinfo is not None and value.utcoffset() is not None, "naive audit clock")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, timedelta):
        return value // timedelta(microseconds=1)
    if isinstance(value, Decimal):
        _require(value.is_finite(), "nonfinite audit value")
        return format(Decimal(0) if value == 0 else value.normalize(), "f")
    if isinstance(value, Mapping):
        _require(all(type(k) is str and k != "$bytes" for k in value), "invalid audit key")
        return {k: _encode(v, blobs) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_encode(v, blobs) for v in value]
    _require(type(value) in (str, int, float, bool, type(None)), "unsupported audit value")
    return value


def _projection(value, blobs, used):
    if type(value) is dict:
        if "$bytes" in value:
            _require(set(value) == {"$bytes"} and value["$bytes"] in blobs, "missing audit body")
            digest = value["$bytes"]
            used.add(digest)
            return {"sha256": digest, "length": blobs[digest]["length"]}
        return {k: _projection(v, blobs, used) for k, v in value.items()}
    if type(value) is list:
        return [_projection(v, blobs, used) for v in value]
    return value


def _strict_object(pairs):
    result = dict(pairs)
    _require(len(result) == len(pairs), "duplicate audit JSON key")
    return result


def _reject_constant(value):
    raise ValueError("nonfinite audit JSON")


def _digest_text(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "invalid audit digest")


def _manifest(bundle):
    fill = next(a for a in bundle.artifacts if a.artifact_kind.value == "FILL_OUTCOME")
    # The existing PFS/CIP-owned friction provenance anchors the selected
    # RTI-11 result in the already-persisted canonical parent, independently
    # of the new audit table's hashes.
    source_rti11_digest = json.loads(fill.canonical_payload)["friction"]["evidence"]["rti11_digest"]
    return {
        "run": _encode(bundle.run.canonical_representation, {}),
        "source_rti11_digest": source_rti11_digest,
        "artifacts": [{"kind": a.artifact_kind.value, "digest": a.artifact_digest,
                       "payload_digest": a.payload_digest, "ordinal": a.ordinal}
                      for a in bundle.artifacts],
    }


def _document(payload):
    _require(type(payload) is str and 0 < len(payload) <= MAX_PAYLOAD_BYTES,
             "audit payload size")
    _require(len(payload.encode("utf-8")) <= MAX_PAYLOAD_BYTES, "audit payload size")
    doc = json.loads(payload, object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    _require(_json(doc) == payload and type(doc) is dict and set(doc) == {
        "contract_version", "simulation_only", "identity", "packet", "blobs", "discovery",
        "evidence", "pools", "bindings", "replays", "winner", "bridge", "lifecycle",
    }, "audit document shape")
    _require(doc["contract_version"] == CONTRACT_VERSION and doc["simulation_only"] is True,
             "audit authority/version")
    identity = doc["identity"]
    _require(type(identity) is dict and set(identity) == set(_IDENTITY_FIELDS), "audit identity shape")
    for name, value in identity.items():
        if name == "collection_id":
            _require(type(value) is str and 0 < len(value) <= 128, "audit collection identity")
        else:
            _digest_text(value)
    blobs = doc["blobs"]
    _require(type(blobs) is dict and len(blobs) <= 231, "audit blob budget")
    for digest, blob in blobs.items():
        _digest_text(digest)
        _require(type(blob) is dict and set(blob) == {"length", "base64"}
                 and type(blob["length"]) is int and 0 <= blob["length"] <= 1048576
                 and type(blob["base64"]) is str
                 and len(blob["base64"]) <= 4 * ((blob["length"] + 2) // 3), "audit body shape")
        body = base64.b64decode(blob["base64"], validate=True)
        _require(len(body) == blob["length"] and hashlib.sha256(body).hexdigest() == digest
                 and base64.b64encode(body).decode("ascii") == blob["base64"], "audit body integrity")
    used = set()
    # Owner-normalized requests/results contain literal caller context; a
    # "$bytes" context key there is data, never our raw-body marker.
    projected = dict(doc)
    for name in ("packet", "discovery", "evidence", "pools", "replays"):
        projected[name] = _projection(doc[name], blobs, used)
    projected["bindings"] = [
        {**b, "material": _projection(b["material"], blobs, used)} for b in doc["bindings"]
    ]
    _require(used == set(blobs), "unreferenced audit bodies")
    packet = projected["packet"]
    _require(packet["contract_version"] == PACKET_VERSION
             and _hash(packet) == identity["packet_digest"], "audit packet integrity")
    context = packet["a1"]["context"]
    _require(context["collection_id"] == identity["collection_id"]
             and context["collection_digest"] == identity["collection_digest"]
             and _hash({k: v for k, v in context.items() if k != "collection_digest"})
                 == identity["collection_digest"], "audit collection integrity")
    discovery = projected["discovery"]
    _require(_hash(discovery["material"]) == discovery["binding_digest"]
             and discovery["material"]["packet_digest"] == identity["packet_digest"],
             "audit discovery integrity")
    for pool in projected["pools"]:
        _require(_hash(pool["material"]) == pool["binding_digest"]
                 and pool["material"]["discovery_binding_digest"] == discovery["binding_digest"],
                 "audit pool integrity")
    pools = {p["binding_digest"] for p in projected["pools"]}
    evidence = {_hash(e) for e in projected["evidence"]}
    for item in projected["evidence"]:
        _require(item["discovery_binding_digest"] == discovery["binding_digest"], "audit evidence integrity")
    bindings, replays = projected["bindings"], projected["replays"]
    _require(0 < len(bindings) == len(replays) <= 5
             and len({b["binding_digest"] for b in bindings}) == len(bindings), "audit replay coverage")
    for binding, replay in zip(bindings, replays):
        material = binding["material"]
        _require(_hash(material) == binding["binding_digest"] == replay["binding_digest"]
                 and _hash(binding["request"]) == material["request_digest"] == replay["request_digest"]
                 and material["pool_binding_digest"] == replay["pool_binding_digest"] in pools
                 and replay["discovery_binding_digest"] == discovery["binding_digest"]
                 and replay["evidence_binding_digest"] in evidence
                 and _hash(material["fact"]) == replay["fact_digest"]
                 and all(material["fact"][name] == replay[name] for name in
                         ("record_identity", "attempt_identity", "reused_a1")), "audit replay integrity")
    winner = projected["winner"]
    selected = winner["rti11_result"]
    _require(_hash({k: v for k, v in selected.items() if k != "result_digest"})
                 == selected["result_digest"] == identity["selected_rti11_digest"], "audit selected result integrity")
    matching = [(b, r) for b, r in zip(bindings, replays) if b["binding_digest"] == winner["binding_digest"]]
    _require(len(matching) == 1 and matching[0][0]["request"] == selected["request"]
             and matching[0][1]["result_digest"] == identity["selected_rti11_digest"], "audit winner linkage")
    body_digest = matching[0][0]["material"]["fact"]["response"]["body"]["sha256"]
    observations = selected["diagnostic"]["diagnostic"]["market"]["observations"]
    _require(len(observations) == 3 and all(
        o["provenance"]["source_metadata"]["response_digest"] == body_digest for o in observations
    ), "audit winner raw-body linkage")
    bridge = projected["bridge"]
    for value in bridge.values():
        _digest_text(value)
    _require(bridge["rti11_digest"] == identity["selected_rti11_digest"]
             and projected["lifecycle"]["source_rti11_digest"] == identity["selected_rti11_digest"]
             and bridge["lifecycle_digest"] == identity["lifecycle_result_digest"]
             and projected["lifecycle"]["run"]["lifecycle_result_digest"] == identity["lifecycle_result_digest"]
             and projected["lifecycle"]["run"]["decision_intent_digest"] == bridge["decision_digest"],
             "audit lifecycle linkage")
    artifacts = {a["kind"]: a["digest"] for a in projected["lifecycle"]["artifacts"]}
    _require(artifacts["RISK_CAPITAL_AUTHORIZATION"] == bridge["authorization_digest"], "audit risk linkage")
    return doc


@dataclass(frozen=True)
class CollectionAuditSnapshot:
    lifecycle_result_digest: str
    collection_id: str
    packet_digest: str
    collection_digest: str
    selected_rti11_digest: str
    canonical_payload: str
    payload_digest: str
    audit_digest: str
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self):
        doc = _document(self.canonical_payload)
        _require(self.contract_version == CONTRACT_VERSION
                 and all(getattr(self, n) == doc["identity"][n] for n in _IDENTITY_FIELDS), "audit snapshot identity")
        _require(hashlib.sha256(self.canonical_payload.encode("utf-8")).hexdigest() == self.payload_digest
                 and self.audit_digest == _hash({"contract_version": CONTRACT_VERSION,
                     **doc["identity"], "payload_digest": self.payload_digest}), "audit snapshot integrity")

    @property
    def raw_bodies(self):
        """Original bytes for inspection only; no owner/transport is restored."""
        return tuple((digest, base64.b64decode(blob["base64"], validate=True))
                     for digest, blob in sorted(_document(self.canonical_payload)["blobs"].items()))


def _capture(packet, replay, invocation):
    _require(type(packet) is DiagnosticCollectionPacket and type(replay) is RTI11DiagnosticReplay
             and type(invocation) is P01Oci01Result, "canonical audit inputs required")
    packet.validate()
    _require(replay.binding.packet is packet and not replay.binding.stopped
             and replay._pending is None and type(replay.safety) is DiagnosticSafetyReplay
             and type(replay.pools) is ExactPoolBinding
             and replay.pools.binding is replay.binding and replay.pools.safety is replay.safety
             and replay.safety._binding is replay.binding, "connected finished audit graph required")
    invocation.__post_init__()
    _require(invocation.outcome is PreparedPaperInvocationOutcome.OSC_RESULT_RETURNED
             and invocation.osc02_result.outcome is PrevalidatedSuffixOutcome.LIFECYCLE_RETURNED,
             "audit requires returned lifecycle")
    cip = invocation.request.cip_result
    prefix, pfs = cip.request.pfx_result, cip.request.pfs_result
    selected = prefix.request.rti11_result
    rti16 = invocation.osc02_result.rti16_result
    lifecycle = rti16.lifecycle_result
    authorization = prefix.rti14_result.authorization_result
    _require(lifecycle is not None and lifecycle.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED
             and lifecycle.admission.decision_intent is prefix.rti13_result.decision_intent
             and lifecycle.admission.risk_capital_authorization is authorization
             and authorization.status is AuthorizationStatus.APPROVED
             and authorization.authorization_effect == PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY,
             "independent approved paper Risk and completed lifecycle required")
    _require(type(replay.bindings) is tuple and type(replay.lineage) is tuple
             and 0 < len(replay.bindings) == len(replay.lineage) <= 5, "unfinished audit replay")
    for record, lineage in zip(replay.bindings, replay.lineage):
        replay._validate(record)
        evidence = next(e for e in replay.safety.evidence_bindings
                        if e.evidence_digest == record.collection.representation_digest)
        expected = ReplayLineageRecord(record.binding_digest, _request_digest(record.request),
            lineage.result_digest, collection_digest(record.fact), record.fact.record_identity,
            record.fact.attempt_identity, record.fact.reused_a1, replay.binding.record.binding_digest,
            collection_digest(evidence), record.pool_record.binding_digest)
        _require(type(lineage) is ReplayLineageRecord and lineage == expected, "audit lineage mismatch")
        _digest_text(lineage.result_digest)
    matches = [(b, l) for b, l in zip(replay.bindings, replay.lineage) if selected.request is b.request]
    _require(len(matches) == 1 and selected.result_digest == matches[0][1].result_digest,
             "selected result is not the original replay result")
    winner = matches[0][0]
    bundle = _build_bundle(lifecycle)
    blobs = {}
    identity = dict(lifecycle_result_digest=lifecycle.digest, collection_id=packet.context.collection_id,
                    packet_digest=packet.packet_digest, collection_digest=packet.context.collection_digest,
                    selected_rti11_digest=selected.result_digest)
    doc = dict(contract_version=CONTRACT_VERSION, simulation_only=True, identity=identity,
        packet=_encode(packet.material(), blobs), blobs=blobs,
        discovery={"material": _encode(replay.binding.record.material(), blobs),
                   "binding_digest": replay.binding.record.binding_digest},
        evidence=_encode(replay.safety.evidence_bindings, blobs),
        pools=[{"material": _encode(p.material(), blobs), "binding_digest": p.binding_digest}
               for p in replay.pools.records],
        bindings=[{"material": _encode(b.material(), blobs), "binding_digest": b.binding_digest,
                   "request": rti11_canonical(b.request.canonical_representation)} for b in replay.bindings],
        replays=_encode(replay.lineage, blobs),
        winner={"binding_digest": winner.binding_digest,
                "rti11_result": rti11_canonical(selected.canonical_representation)},
        bridge=dict(rti11_digest=selected.result_digest, pfx_digest=prefix.result_digest,
                    pfs_digest=pfs.result_digest, cip_digest=cip.result_digest,
                    oci_digest=invocation.result_digest, osc_digest=invocation.osc02_result.result_digest,
                    rti16_digest=rti16.result_digest, lifecycle_digest=lifecycle.digest,
                    decision_digest=lifecycle.admission.decision_intent.digest,
                    authorization_digest=authorization.digest),
        lifecycle=_manifest(bundle))
    payload = _json(doc)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    snapshot = CollectionAuditSnapshot(**identity, canonical_payload=payload, payload_digest=digest,
        audit_digest=_hash({"contract_version": CONTRACT_VERSION, **identity, "payload_digest": digest}))
    return snapshot, bundle


def capture_collection_audit(packet, replay, invocation) -> CollectionAuditSnapshot:
    """Pure capture of exact live owner objects; no owner service is rerun."""
    return _capture(packet, replay, invocation)[0]


class AuditWriteOutcome(StrEnum):
    STORED = "STORED"
    ALREADY_STORED = "ALREADY_STORED"
    INVALID_INPUT = "INVALID_INPUT"
    LIFECYCLE_NOT_FOUND = "LIFECYCLE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


class AuditReadOutcome(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    CORRUPT = "CORRUPT"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


@dataclass(frozen=True)
class AuditWriteResult:
    outcome: AuditWriteOutcome
    lifecycle_result_digest: str | None = None
    audit_digest: str | None = None


@dataclass(frozen=True)
class AuditReadResult:
    outcome: AuditReadOutcome
    lifecycle_result_digest: str
    snapshot: CollectionAuditSnapshot | None = None


def _values(snapshot):
    return {f.name: getattr(snapshot, f.name) for f in fields(snapshot)}


def _stored_snapshot(record, run, artifacts):
    snapshot = CollectionAuditSnapshot(**{f.name: getattr(record, f.name) for f in fields(CollectionAuditSnapshot)})
    _require(record.run_id == run.id and record.lifecycle_result_digest == run.lifecycle_result_digest,
             "audit foreign lifecycle identity")
    bundle = _snapshot_bundle(run, artifacts)
    _require(_document(snapshot.canonical_payload)["lifecycle"] == _manifest(bundle), "audit lifecycle content disagreement")
    return snapshot


class A1CollectionAuditService:
    """Separate explicit attachment, with one audit write transaction only."""

    def __init__(self, database: DatabaseRuntime, repository=None):
        _require(isinstance(database, DatabaseRuntime), "DatabaseRuntime required")
        self.database = database
        self.repository = repository if repository is not None else A1CollectionAuditRepository()
        self.lifecycle_repository = PaperLifecycleRepository()

    @property
    def _available(self):
        return self.database.state is DatabaseState.CONNECTED and self.database.session_factory is not None

    async def persist(self, packet, replay, invocation) -> AuditWriteResult:
        try:
            snapshot, bundle = _capture(packet, replay, invocation)
        except (ValueError, TypeError, AttributeError, KeyError, StopIteration, ArithmeticError, RecursionError):
            return AuditWriteResult(AuditWriteOutcome.INVALID_INPUT)
        if not self._available:
            return AuditWriteResult(AuditWriteOutcome.STORAGE_UNAVAILABLE, snapshot.lifecycle_result_digest)
        try:
            return await self._store(snapshot, bundle, insert=True)
        except IntegrityError:
            # One read-only race resolution, never a second insertion attempt.
            try:
                return await self._store(snapshot, bundle, insert=False)
            except (SQLAlchemyError, OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
                pass
        except (SQLAlchemyError, OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
            pass
        return AuditWriteResult(AuditWriteOutcome.STORAGE_UNAVAILABLE, snapshot.lifecycle_result_digest)

    async def _store(self, snapshot, bundle, *, insert):
        digest = snapshot.lifecycle_result_digest
        async with self.database.session_scope() as session:
            run = await self.lifecycle_repository.get_run(session, digest)
            if run is None:
                return AuditWriteResult(AuditWriteOutcome.LIFECYCLE_NOT_FOUND, digest)
            artifacts = await self.lifecycle_repository.get_artifacts(session, run.id)
            if _compare_existing(run, artifacts, bundle).outcome is not PaperLifecyclePersistenceOutcome.ALREADY_STORED:
                return AuditWriteResult(AuditWriteOutcome.CONFLICT, digest)
            existing = await self.repository.get(session, digest)
            if existing is not None:
                try:
                    stored = _stored_snapshot(existing, run, artifacts)
                except (ValueError, TypeError, AttributeError, KeyError):
                    return AuditWriteResult(AuditWriteOutcome.CONFLICT, digest)
                if stored != snapshot:
                    return AuditWriteResult(AuditWriteOutcome.CONFLICT, digest)
                return AuditWriteResult(AuditWriteOutcome.ALREADY_STORED, digest, snapshot.audit_digest)
            if not insert:
                return AuditWriteResult(AuditWriteOutcome.STORAGE_UNAVAILABLE, digest)
            await self.repository.insert(session, run_id=run.id, values=_values(snapshot))
        return AuditWriteResult(AuditWriteOutcome.STORED, digest, snapshot.audit_digest)

    async def read(self, lifecycle_result_digest: str) -> AuditReadResult:
        digest = validate_lifecycle_result_digest(lifecycle_result_digest)
        if not self._available:
            return AuditReadResult(AuditReadOutcome.STORAGE_UNAVAILABLE, digest)
        try:
            async with self.database.session_scope() as session:
                record = await self.repository.get(session, digest)
                if record is None:
                    return AuditReadResult(AuditReadOutcome.NOT_FOUND, digest)
                run = await self.lifecycle_repository.get_run(session, digest)
                _require(run is not None, "audit lifecycle missing")
                artifacts = await self.lifecycle_repository.get_artifacts(session, run.id)
                snapshot = _stored_snapshot(record, run, artifacts)
        except (ValueError, TypeError, AttributeError, KeyError, StopIteration, RecursionError):
            return AuditReadResult(AuditReadOutcome.CORRUPT, digest)
        except (SQLAlchemyError, OSError, RuntimeError):
            return AuditReadResult(AuditReadOutcome.STORAGE_UNAVAILABLE, digest)
        return AuditReadResult(AuditReadOutcome.FOUND, digest, snapshot)
