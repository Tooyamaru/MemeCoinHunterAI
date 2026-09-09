from dataclasses import FrozenInstanceError
import hashlib
import inspect
import json

import pytest

import core.learning.authority_b_lineage as authority_b
from core.learning.authority_b_lineage import (
    AUTHORITY_B_CONTRACT_VERSION,
    AUTHORITY_B_POLICY_VERSION,
    AUTHORITY_B_SNAPSHOT_CONTRACT_VERSION,
    AuthorityBFailure,
    AuthoritativeLineageFactSetSnapshot,
    DuplicateStatus,
    LineageEdge,
    LineageFact,
    LineageGraphInput,
    LineageType,
    PROVENANCE_STAGES,
    ProvenanceLink,
    canonical_json,
    validate_lineage_fact,
    validate_lineage_graph,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _provenance(authority: str = "authority-a"):
    return tuple(
        ProvenanceLink(
            stage=stage,
            record_identity=f"{stage}-record",
            record_digest=_digest(stage),
            authority_identity=authority,
        )
        for stage in PROVENANCE_STAGES
    )


def _fact(
    predecessor: str = "result-1",
    successor: str = "result-2",
    lineage_type: str | LineageType = LineageType.CORRECTION,
    *,
    lifecycle: str = "lifecycle-1",
    authority: str = "authority-b",
    provenance=None,
):
    return LineageFact(
        contract_version=AUTHORITY_B_CONTRACT_VERSION,
        lineage_policy_version=AUTHORITY_B_POLICY_VERSION,
        lifecycle_identity=lifecycle,
        predecessor_result_identity=predecessor,
        successor_result_identity=successor,
        lineage_type=lineage_type,
        authority_identity=authority,
        provenance=_provenance() if provenance is None else provenance,
    )


def _snapshot(lifecycle="lifecycle-1", *facts):
    return AuthoritativeLineageFactSetSnapshot.from_facts(lifecycle, facts)


def test_canonical_json_has_locked_unicode_escape_and_order_profile():
    value = {
        "z": "é\u2028/\b\t\n\f\r\x00",
        "a": "e\u0301",
        "quote": '"\\',
    }

    encoded = canonical_json(value)

    assert encoded == (
        '{"a":"é","quote":"\\"\\\\","z":"é\u2028/\\b\\t\\n\\f\\r\\u0000"}'
    )
    assert json.loads(encoded) == {"a": "é", "quote": '"\\', "z": "é\u2028/\b\t\n\f\r\x00"}
    assert "\\/" not in encoded
    assert "\\u00" in encoded


def test_canonical_json_rejects_surrogates_nulls_and_numbers_for_authority_values():
    with pytest.raises(ValueError):
        canonical_json({"value": "\ud800"})
    with pytest.raises(ValueError):
        canonical_json({"value": None}, allow_null=False)
    with pytest.raises(ValueError):
        canonical_json({"value": 1})


def test_fact_and_edge_identity_are_exact_and_digest_is_non_circular():
    fact = _fact()
    edge = LineageEdge.from_fact(fact)

    expected_projection = [
        AUTHORITY_B_CONTRACT_VERSION,
        AUTHORITY_B_POLICY_VERSION,
        "lifecycle-1",
        "result-1",
        "result-2",
        "correction",
    ]
    expected_fact = hashlib.sha256(
        b"p08-authority-b:fact:v1\0"
        + authority_b.canonical_json_bytes(expected_projection, allow_null=False)
    ).hexdigest()
    expected_edge = hashlib.sha256(
        b"p08-authority-b:edge:v1\0"
        + authority_b.canonical_json_bytes(expected_projection, allow_null=False)
    ).hexdigest()

    assert fact.lineage_fact_identity == expected_fact
    assert edge.lineage_edge_identity == expected_edge
    assert edge.edge_digest == hashlib.sha256(
        authority_b.canonical_json_bytes(
            edge._digest_representation(), allow_null=False
        )
    ).hexdigest()
    assert "edge_digest" not in edge._digest_representation()


def test_replay_is_independent_of_provenance_order_source_and_snapshot_context():
    fact = _fact()
    equivalent = _fact()
    empty = _snapshot()
    established = _snapshot("lifecycle-1", fact)

    left = validate_lineage_fact(fact, empty)
    right = validate_lineage_fact(equivalent, established)

    assert left.fact.lineage_fact_identity == right.fact.lineage_fact_identity
    assert left.edge.canonical_bytes == right.edge.canonical_bytes
    assert left.edge.edge_digest == right.edge.edge_digest
    assert right.duplicate_status is DuplicateStatus.EXACT_DUPLICATE


def test_snapshot_is_explicit_canonically_ordered_and_identity_is_context_only():
    first = _fact("r1", "r2")
    second = _fact("r2", "r3", LineageType.SUPERSESSION)
    snapshot = _snapshot("lifecycle-1", second, first)

    assert tuple(
        member.lineage_fact_identity for member in snapshot.members
    ) == tuple(sorted(member.lineage_fact_identity for member in snapshot.members))
    assert snapshot.snapshot_contract_version == AUTHORITY_B_SNAPSHOT_CONTRACT_VERSION
    assert snapshot.snapshot_identity
    assert snapshot.snapshot_digest
    assert first.lineage_fact_identity not in snapshot.identity_projection["lifecycle_identity"]


def test_exact_duplicate_is_idempotent_and_reuses_the_same_projection():
    fact = _fact()
    result = validate_lineage_fact(fact, _snapshot("lifecycle-1", fact))

    assert result.accepted
    assert result.duplicate_status is DuplicateStatus.EXACT_DUPLICATE
    assert result.edge == LineageEdge.from_fact(fact)
    assert result.projection.correction_lineage[0] == result.edge.canonical_representation


def test_conflicting_duplicate_fails_closed_without_last_write_wins():
    original = _fact()
    conflicting = _fact(authority="different-authority")

    result = validate_lineage_fact(conflicting, _snapshot("lifecycle-1", original))

    assert not result.accepted
    assert result.failure is AuthorityBFailure.CONFLICTING_DUPLICATE
    assert result.duplicate_status is DuplicateStatus.CONFLICTING_DUPLICATE
    assert result.t07_status == "INVALID_INPUT"
    assert result.t07_failure_reason == "CONFLICTING_INPUT"


@pytest.mark.parametrize(
    ("lineage_type", "field"),
    [
        (LineageType.CORRECTION, "correction_lineage"),
        (LineageType.SUPERSESSION, "supersession_lineage"),
    ],
)
def test_t07_projection_selects_only_the_existing_destination(lineage_type, field):
    fact = _fact(lineage_type=lineage_type)
    result = validate_lineage_fact(fact, _snapshot())

    projection = result.projection
    assert result.accepted
    assert projection.destination_field == field
    assert getattr(projection, field)[0]["lineage_type"] == lineage_type.value
    other = "supersession_lineage" if field == "correction_lineage" else "correction_lineage"
    assert getattr(projection, other) is None


def test_valid_linear_mixed_lineage_returns_one_structural_terminal_candidate():
    first = _fact("r1", "r2", LineageType.CORRECTION)
    second = _fact("r2", "r3", LineageType.SUPERSESSION)
    graph = LineageGraphInput(
        lifecycle_identity="lifecycle-1",
        result_identities={"r1": "lifecycle-1", "r2": "lifecycle-1", "r3": "lifecycle-1"},
        lineage_facts=(second, first),
        snapshot=_snapshot("lifecycle-1"),
    )

    result = validate_lineage_graph(graph)

    assert result.accepted
    assert result.terminal_candidate == "r3"
    assert result.t07_status == "VALID"


@pytest.mark.parametrize(
    ("name", "result_ids", "facts", "failure"),
    [
        (
            "branch",
            {"r1": "lifecycle-1", "r2": "lifecycle-1", "r3": "lifecycle-1"},
            (_fact("r1", "r2"), _fact("r1", "r3")),
            AuthorityBFailure.LINEAGE_BRANCH_CONFLICT,
        ),
        (
            "merge",
            {"r1": "lifecycle-1", "r2": "lifecycle-1", "r3": "lifecycle-1"},
            (_fact("r1", "r3"), _fact("r2", "r3")),
            AuthorityBFailure.MERGE_UNSUPPORTED,
        ),
        (
            "cycle",
            {"r1": "lifecycle-1", "r2": "lifecycle-1"},
            (_fact("r1", "r2"), _fact("r2", "r1")),
            AuthorityBFailure.LINEAGE_CYCLE,
        ),
        (
            "self-reference",
            {"r1": "lifecycle-1"},
            (_fact("r1", "r1"),),
            AuthorityBFailure.LINEAGE_SELF_REFERENCE,
        ),
        (
            "missing-endpoint",
            {"r1": "lifecycle-1"},
            (_fact("r1", "missing"),),
            AuthorityBFailure.MISSING_ENDPOINT,
        ),
        (
            "cross-lifecycle",
            {"r1": "lifecycle-1", "r2": "other-lifecycle"},
            (_fact("r1", "r2"),),
            AuthorityBFailure.CROSS_LIFECYCLE_REFERENCE,
        ),
        (
            "ambiguous-terminal",
            {"r1": "lifecycle-1", "r2": "lifecycle-1"},
            (),
            AuthorityBFailure.DETERMINISM_FAILURE,
        ),
    ],
)
def test_required_graph_failures_fail_closed(name, result_ids, facts, failure):
    graph = LineageGraphInput(
        lifecycle_identity="lifecycle-1",
        result_identities=result_ids,
        lineage_facts=facts,
        snapshot=_snapshot(),
    )

    result = validate_lineage_graph(graph)

    assert not result.accepted, name
    assert result.failure is failure
    assert result.terminal_candidate is None


def test_contradictory_lineage_and_failure_precedence_are_deterministic():
    correction = _fact("r1", "r2", LineageType.CORRECTION)
    supersession = _fact("r1", "r2", LineageType.SUPERSESSION)
    graph = LineageGraphInput(
        lifecycle_identity="lifecycle-1",
        result_identities={"r1": "lifecycle-1", "r2": "lifecycle-1"},
        lineage_facts=(supersession, correction),
        snapshot=_snapshot(),
    )

    result = validate_lineage_graph(graph)

    assert result.failure is AuthorityBFailure.CONTRADICTORY_LINEAGE
    assert result.t07_failure_reason == "CONFLICTING_INPUT"


def test_invalid_provenance_and_digest_fail_closed():
    fact = _fact()
    malformed_provenance = dict(fact.canonical_representation)
    malformed_provenance["provenance"] = ()
    provenance_result = validate_lineage_fact(malformed_provenance, _snapshot())

    tampered = object.__new__(LineageFact)
    for field in (
        "contract_version",
        "lineage_policy_version",
        "lifecycle_identity",
        "predecessor_result_identity",
        "successor_result_identity",
        "lineage_type",
        "authority_identity",
        "provenance",
    ):
        object.__setattr__(tampered, field, getattr(fact, field))
    object.__setattr__(tampered, "lineage_fact_identity", "0" * 64)
    digest_result = validate_lineage_fact(tampered, _snapshot())

    assert provenance_result.failure is AuthorityBFailure.MALFORMED_FACT
    assert digest_result.failure is AuthorityBFailure.INVALID_IDENTITY


def test_fact_edge_snapshot_and_graph_are_immutable():
    fact = _fact()
    edge = LineageEdge.from_fact(fact)
    snapshot = _snapshot("lifecycle-1", fact)
    graph = LineageGraphInput(
        "lifecycle-1",
        {"r1": "lifecycle-1", "r2": "lifecycle-1"},
        (fact,),
        snapshot,
    )

    with pytest.raises(FrozenInstanceError):
        fact.authority_identity = "changed"
    with pytest.raises(FrozenInstanceError):
        edge.edge_digest = "changed"
    with pytest.raises(FrozenInstanceError):
        snapshot.snapshot_digest = "changed"
    with pytest.raises(TypeError):
        snapshot.canonical_representation["members"] = ()
    with pytest.raises(TypeError):
        graph.result_identities["r1"] = "changed"


def test_public_boundary_has_no_ambient_or_prohibited_dependencies():
    assert "socket" not in authority_b.__dict__
    assert "requests" not in authority_b.__dict__
    assert "sqlite3" not in authority_b.__dict__
    assert "datetime" not in authority_b.__dict__
    assert "time" not in authority_b.__dict__
    assert "random" not in authority_b.__dict__
    assert inspect.signature(validate_lineage_fact).parameters.keys() == {
        "candidate",
        "snapshot",
        "lifecycle_identity",
    }
    forbidden = (
        "calculate_profit",
        "calculate_pnl",
        "classify_performance",
        "fetch_provider",
        "execute_trade",
        "sign_transaction",
        "wallet",
        "rpc",
        "persist",
    )
    for name in forbidden:
        assert not hasattr(authority_b, name)