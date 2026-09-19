"""Pytest test suite for the correlation engine.

Tests cover:
  1. Confidence weighting table values and canonicality
  2. Weak-signal compounding math (hand-calculated reference values)
  3. Graph construction from fixture-based mock fraud scenario
  4. Connected component (cluster) assignment
  5. Path-finding via inverse-confidence shortest path
  6. Graph JSON serialization and confidence_label derivation
  7. Regression guard: lone shared IP subnet stays below "Strong"
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.db.models import (
    Case,
    CaseStatus,
    Entity,
    EntityLink,
    EntityType,
    EvidenceFile,
    LinkType,
    SourceType,
)
from app.schemas.entity_link import get_confidence_label
from app.services.correlation.confidence_rules import (
    CONFIDENCE_SHARED_IMEI,
    CONFIDENCE_SHARED_IP_SUBNET,
    CONFIDENCE_SHARED_MAC,
    CONFIDENCE_SHARED_UPI_HANDLE,
    WEAK_SIGNAL_THRESHOLD,
    combine_confidences,
    compound_weak_signals,
    get_link_confidence,
)
from app.services.correlation.graph_builder import GraphBuilder, find_path
from app.services.correlation.graph_serializer import serialize_graph

# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(name="db_session")
def db_session_fixture():
    """Isolated in-memory SQLite with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="fraud_db")
def fraud_scenario_db(db_session: Session) -> dict:
    """
    Seed the mock fraud scenario from Phase 2 fixture data:

        victim (phone) → TRANSACTION → mule1 (account)
        mule1 (account) → TRANSACTION → mule2 (account)
        mule1 (account) → TRANSACTION → cashout (account)
        mule2 (account) → TRANSACTION → cashout (account)
        mule1 (phone) ←→ SHARED_IMEI  → shared_imei (device)
        victim (phone) ←→ SHARED_IP_SUBNET → mule1 (phone) [weak signal]

    The mule1 phone and victim phone also share an IP subnet link (weak).
    """
    # Case
    case = Case(
        name="Operation Phantom Grid — Correlation Test", status=CaseStatus.ACTIVE.value
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # Evidence file
    ev = EvidenceFile(
        case_id=case.id,
        original_filename="fixture_seed.csv",
        source_type=SourceType.BANK_UPI,
        file_hash="e3b0c44298fc1c149afbf4c8996fb924" * 2,
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)
    ev_id = ev.id

    def entity(etype: EntityType, value: str) -> Entity:
        e = Entity(case_id=case.id, entity_type=etype, value=value)
        db_session.add(e)
        db_session.flush()
        return e

    def link(a: Entity, b: Entity, ltype: LinkType, confidence: float) -> EntityLink:
        u, v = min(a.id, b.id), max(a.id, b.id)
        lnk = EntityLink(
            case_id=case.id,
            entity_a_id=u,
            entity_b_id=v,
            link_type=ltype,
            confidence_score=confidence,
            source_evidence_file_id=ev_id,
        )
        db_session.add(lnk)
        db_session.flush()
        return lnk

    # Entities mirroring Phase 2 bank fixture
    victim = entity(EntityType.PHONE, "+919876543210")
    mule1_acc = entity(EntityType.ACCOUNT, "MULE_ACC_101")
    mule2_acc = entity(EntityType.ACCOUNT, "MULE_ACC_202")
    cashout_acc = entity(EntityType.ACCOUNT, "CASHOUT_ACC_303")
    mule1_phone = entity(EntityType.PHONE, "+919811122233")
    shared_imei = entity(EntityType.DEVICE_IMEI, "860123456789012")
    shared_ip = entity(EntityType.IP_ADDRESS, "185.220.101.5")

    # Transaction chain
    l1 = link(victim, mule1_acc, LinkType.TRANSACTION, 0.75)
    l2 = link(mule1_acc, mule2_acc, LinkType.TRANSACTION, 0.75)
    l3 = link(mule1_acc, cashout_acc, LinkType.TRANSACTION, 0.75)
    l4 = link(mule2_acc, cashout_acc, LinkType.TRANSACTION, 0.75)

    # IMEI link
    l5 = link(mule1_phone, shared_imei, LinkType.SHARED_IMEI, 0.85)

    # Weak IP subnet link: victim phone ↔ mule1 phone
    l6 = link(victim, mule1_phone, LinkType.SHARED_IP_SUBNET, 0.30)

    # Another weak IP subnet link: mule1 phone ↔ shared IP
    l7 = link(mule1_phone, shared_ip, LinkType.SHARED_IP_SUBNET, 0.30)

    db_session.commit()

    return {
        "case": case,
        "session": db_session,
        "entities": {
            "victim": victim,
            "mule1_acc": mule1_acc,
            "mule2_acc": mule2_acc,
            "cashout_acc": cashout_acc,
            "mule1_phone": mule1_phone,
            "shared_imei": shared_imei,
            "shared_ip": shared_ip,
        },
        "links": [l1, l2, l3, l4, l5, l6, l7],
    }


# ---------------------------------------------------------------------------
# 1. Confidence Weighting Table Tests
# ---------------------------------------------------------------------------


def test_confidence_constants_match_spec():
    """Verify named confidence constants exactly match documented specification."""
    assert CONFIDENCE_SHARED_IMEI == pytest.approx(0.85)
    assert CONFIDENCE_SHARED_UPI_HANDLE == pytest.approx(0.80)
    assert CONFIDENCE_SHARED_MAC == pytest.approx(0.60)
    assert CONFIDENCE_SHARED_IP_SUBNET == pytest.approx(0.30)


def test_get_link_confidence_by_enum():
    """Verify lookup by LinkType enum returns canonical weights."""
    assert get_link_confidence(LinkType.SHARED_IMEI) == pytest.approx(0.85)
    assert get_link_confidence(LinkType.SHARED_UPI_HANDLE) == pytest.approx(0.80)
    assert get_link_confidence(LinkType.SHARED_MAC) == pytest.approx(0.60)
    assert get_link_confidence(LinkType.SHARED_IP_SUBNET) == pytest.approx(0.30)


def test_get_link_confidence_by_string():
    """Verify lookup by string value also resolves correctly."""
    assert get_link_confidence("shared_imei") == pytest.approx(0.85)
    assert get_link_confidence("shared_ip_subnet") == pytest.approx(0.30)


def test_shared_ip_alone_is_weak():
    """
    Regression guard: a lone shared_ip_subnet link must stay below
    the WEAK_SIGNAL_THRESHOLD (0.50) — i.e., not "Medium" or "Strong".

    This test would fail if someone changed CONFIDENCE_SHARED_IP_SUBNET to >= 0.50
    or changed the threshold, breaking the evidentiary calibration.
    """
    confidence = get_link_confidence(LinkType.SHARED_IP_SUBNET)
    label = get_confidence_label(confidence)
    assert confidence < WEAK_SIGNAL_THRESHOLD, (
        f"Lone shared_ip_subnet confidence ({confidence}) must be < "
        f"WEAK_SIGNAL_THRESHOLD ({WEAK_SIGNAL_THRESHOLD}). "
        "Do NOT raise: CGNAT means thousands of civilian subscribers share a subnet."
    )
    assert label == "Weak", (
        f"Lone shared_ip_subnet label was '{label}' but must be 'Weak'. "
        "Regression: binary linking without proper signal weighting would wrongly "
        "incriminate innocent citizens sharing a carrier-grade NAT address."
    )


def test_shared_mac_is_medium():
    """Shared MAC must be 'Medium' (0.60), not strong or weak."""
    c = get_link_confidence(LinkType.SHARED_MAC)
    assert get_confidence_label(c) == "Medium"


def test_shared_imei_and_upi_are_strong():
    """Shared IMEI (0.85) and UPI handle (0.80) must be 'Strong'."""
    assert get_confidence_label(get_link_confidence(LinkType.SHARED_IMEI)) == "Strong"
    assert (
        get_confidence_label(get_link_confidence(LinkType.SHARED_UPI_HANDLE))
        == "Strong"
    )


# ---------------------------------------------------------------------------
# 2. Weak-Signal Compounding Math Tests (hand-calculated)
# ---------------------------------------------------------------------------


def test_compound_weak_signals_single():
    """Single weak signal: compounding returns the signal itself."""
    result = compound_weak_signals([0.30])
    assert result == pytest.approx(0.30)


def test_compound_weak_signals_two_ip_links_hand_calc():
    """
    Two independent shared_ip_subnet links (0.30 each).

    Hand calculation:
        C = 1 - (1 - 0.30) * (1 - 0.30)
          = 1 - 0.70 * 0.70
          = 1 - 0.49
          = 0.51

    Resulting label: "Medium" — escalated from individual "Weak" links.
    """
    result = compound_weak_signals([0.30, 0.30])
    assert result == pytest.approx(0.51, abs=1e-4)
    assert get_confidence_label(result) == "Medium"


def test_compound_weak_signals_three_ip_links_hand_calc():
    """
    Three independent shared_ip_subnet links (0.30 each).

    Hand calculation:
        C = 1 - (1 - 0.30)^3
          = 1 - 0.70^3
          = 1 - 0.343
          = 0.657
    """
    result = compound_weak_signals([0.30, 0.30, 0.30])
    assert result == pytest.approx(0.657, abs=1e-4)
    assert get_confidence_label(result) == "Medium"


def test_compound_weak_signals_five_ip_links_hand_calc():
    """
    Five independent shared_ip_subnet links (0.30 each).

    Hand calculation:
        C = 1 - 0.70^5
          = 1 - 0.16807
          = 0.83193 → "Strong"
    """
    result = compound_weak_signals([0.30, 0.30, 0.30, 0.30, 0.30])
    assert result == pytest.approx(0.83193, abs=1e-4)
    assert get_confidence_label(result) == "Strong"


def test_compound_weak_signals_mixed_weak():
    """
    Two different weak signals (0.30 and 0.40).

    Hand calculation:
        C = 1 - (1 - 0.30) * (1 - 0.40)
          = 1 - 0.70 * 0.60
          = 1 - 0.42
          = 0.58
    """
    result = compound_weak_signals([0.30, 0.40])
    assert result == pytest.approx(0.58, abs=1e-4)
    assert get_confidence_label(result) == "Medium"


def test_compound_weak_signals_empty():
    """Empty sequence: returns 0.0."""
    assert compound_weak_signals([]) == pytest.approx(0.0)


def test_combine_confidences_all_weak_uses_compounding():
    """
    When all signals are weak, combine_confidences MUST use the compounding
    formula, NOT naive max. Two 0.30 signals should yield 0.51, not 0.30.

    This is the key regression guard: if someone replaces compounding with
    `max(weights)`, this test will fail.
    """
    result = combine_confidences([0.30, 0.30])
    naive_max = 0.30  # What a naive implementation would return
    assert result > naive_max, (
        "combine_confidences() must compound weak signals, not take the naive max. "
        "Two independent IP subnet observations are more meaningful than one."
    )
    assert result == pytest.approx(0.51, abs=1e-4)


def test_combine_confidences_with_strong_signal():
    """When a strong signal is present, its weight is not degraded by weak signals."""
    result = combine_confidences([0.85, 0.30])  # IMEI + IP subnet
    assert result == pytest.approx(0.85)


def test_combine_confidences_single_value():
    """Single signal is returned as-is."""
    assert combine_confidences([0.75]) == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 3. Graph Construction — Mock Fraud Scenario
# ---------------------------------------------------------------------------


def test_graph_builds_successfully(fraud_db):
    """GraphBuilder.build_for_case() returns a valid NetworkX graph for case."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    assert graph is not None
    # 7 nodes: victim, mule1_acc, mule2_acc, cashout, mule1_phone, imei, ip
    assert graph.number_of_nodes() == 7
    # 7 links seeded across transaction, IMEI, and IP subnet relationships
    assert graph.number_of_edges() >= 6


def test_graph_all_entities_are_nodes(fraud_db):
    """All seeded entities appear as nodes in the graph."""
    case = fraud_db["case"]
    session = fraud_db["session"]
    entities = fraud_db["entities"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    for name, entity in entities.items():
        assert (
            entity.id in graph
        ), f"Entity '{name}' (id={entity.id}) missing from graph"


def test_graph_connected_components_form_single_cluster(fraud_db):
    """
    In the fraud scenario, all entities form one connected component (cluster).

    The victim phone links to mule1_phone (IP subnet), mule1_phone links to the IMEI,
    and the transaction chain connects all accounts. There should be exactly 1 cluster.
    """
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    import networkx as nx

    components = list(nx.connected_components(graph))
    assert len(components) == 1, (
        f"Expected 1 connected cluster (fraud syndicate), got {len(components)}. "
        f"Clusters: {components}"
    )


def test_graph_nodes_have_cluster_id(fraud_db):
    """Every node in the graph must have a cluster_id attribute assigned."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    for node_id, data in graph.nodes(data=True):
        assert "cluster_id" in data, f"Node {node_id} is missing 'cluster_id' attribute"
        assert isinstance(data["cluster_id"], int)


def test_graph_edges_have_confidence_and_link_type(fraud_db):
    """Every edge must carry 'confidence' and 'link_type' attributes."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    for u, v, data in graph.edges(data=True):
        assert "confidence" in data, f"Edge ({u},{v}) missing 'confidence'"
        assert "link_type" in data, f"Edge ({u},{v}) missing 'link_type'"
        assert (
            0.0 <= data["confidence"] <= 1.0
        ), f"Confidence {data['confidence']} out of range"


def test_graph_edge_confidence_values(fraud_db):
    """IMEI edge has 0.85 confidence; IP subnet edge has 0.30 confidence."""
    case = fraud_db["case"]
    session = fraud_db["session"]
    entities = fraud_db["entities"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    mule1_phone_id = entities["mule1_phone"].id
    imei_id = entities["shared_imei"].id
    victim_id = entities["victim"].id

    imei_edge = graph.get_edge_data(
        min(mule1_phone_id, imei_id), max(mule1_phone_id, imei_id)
    )
    assert imei_edge is not None, "IMEI edge not found"
    assert imei_edge["confidence"] == pytest.approx(0.85)

    ip_edge_data = graph.get_edge_data(
        min(victim_id, mule1_phone_id), max(victim_id, mule1_phone_id)
    )
    assert ip_edge_data is not None, "IP subnet edge not found"
    assert ip_edge_data["confidence"] == pytest.approx(0.30)


def test_graph_inverse_confidence_weights(fraud_db):
    """Edges must have 'inverse_confidence' set to 1/confidence for path weighting."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    for u, v, data in graph.edges(data=True):
        confidence = data["confidence"]
        inv = data["inverse_confidence"]
        assert inv == pytest.approx(
            1.0 / confidence, rel=1e-4
        ), f"Edge ({u},{v}): inverse_confidence {inv} != 1/confidence {1.0/confidence}"


def test_fraud_scenario_victim_to_cashout_path(fraud_db):
    """
    The 'how are these connected' feature:
    find_path(graph, victim_id, cashout_id) must return a valid path.
    The path should travel through the transaction chain (high-confidence edges),
    not through weak IP subnet hops.
    """
    case = fraud_db["case"]
    session = fraud_db["session"]
    entities = fraud_db["entities"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    victim_id = entities["victim"].id
    cashout_id = entities["cashout_acc"].id

    path = find_path(graph, victim_id, cashout_id)
    assert path is not None, "Expected a path from victim to cashout_acc"
    assert path[0] == victim_id, "Path must start at victim"
    assert path[-1] == cashout_id, "Path must end at cashout"
    # Path should exist; verify it passes through mule1_acc (transaction chain)
    mule1_acc_id = entities["mule1_acc"].id
    assert (
        mule1_acc_id in path
    ), "Shortest (strongest) path should route through mule1_acc transaction link"


def test_find_path_no_path_returns_none(fraud_db):
    """find_path returns None when two nodes are disconnected."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    # Add an isolated node not connected to anyone
    graph.add_node(
        99999, id=99999, entity_type="phone", value="isolated", cluster_id=99
    )

    path = find_path(graph, 99999, next(iter(fraud_db["entities"].values())).id)
    assert path is None


def test_find_path_same_node_returns_self(fraud_db):
    """find_path for the same node as source and target returns [node_id]."""
    case = fraud_db["case"]
    session = fraud_db["session"]
    entities = fraud_db["entities"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)

    victim_id = entities["victim"].id
    path = find_path(graph, victim_id, victim_id)
    assert path == [victim_id]


# ---------------------------------------------------------------------------
# 4. Graph Serialization Tests
# ---------------------------------------------------------------------------


def test_serialization_shape(fraud_db):
    """serialize_graph returns dict with 'nodes' and 'edges' lists."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)
    result = serialize_graph(graph)

    assert "nodes" in result
    assert "edges" in result
    assert isinstance(result["nodes"], list)
    assert isinstance(result["edges"], list)


def test_serialized_node_fields(fraud_db):
    """Each serialized node has required fields: id, entity_type, value, cluster_id."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)
    result = serialize_graph(graph)

    for node in result["nodes"]:
        assert "id" in node
        assert "entity_type" in node
        assert "value" in node
        assert "cluster_id" in node


def test_serialized_edge_fields(fraud_db):
    """Each serialized edge has required fields including confidence_label."""
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)
    result = serialize_graph(graph)

    for edge in result["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "confidence" in edge
        assert "link_type" in edge
        assert "confidence_label" in edge
        assert edge["confidence_label"] in {"Strong", "Medium", "Weak"}


def test_serialized_confidence_labels_match_schema_layer(fraud_db):
    """
    Confidence labels must be derived using the same thresholds as Phase 1's
    EntityLinkRead.confidence_label (imported get_confidence_label).
    This ensures no duplicate threshold definitions.
    """
    case = fraud_db["case"]
    session = fraud_db["session"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)
    result = serialize_graph(graph)

    for edge in result["edges"]:
        expected_label = get_confidence_label(edge["confidence"])
        assert edge["confidence_label"] == expected_label, (
            f"Serializer label '{edge['confidence_label']}' differs from "
            f"schema layer label '{expected_label}' for confidence {edge['confidence']}"
        )


def test_ip_subnet_edge_label_is_weak_in_serialization(fraud_db):
    """
    Regression guard for serializer:
    The lone shared_ip_subnet edge (0.30) must serialize with confidence_label="Weak".
    """
    case = fraud_db["case"]
    session = fraud_db["session"]
    entities = fraud_db["entities"]

    graph = GraphBuilder.build_for_case(case.id, session=session, enforce_rules=False)
    result = serialize_graph(graph)

    victim_id = entities["victim"].id
    mule1_phone_id = entities["mule1_phone"].id

    ip_edges = [
        e
        for e in result["edges"]
        if (
            e["source"] == min(victim_id, mule1_phone_id)
            and e["target"] == max(victim_id, mule1_phone_id)
        )
    ]
    assert (
        len(ip_edges) == 1
    ), "Expected exactly one edge between victim and mule1_phone"
    assert ip_edges[0]["confidence_label"] == "Weak", (
        f"IP subnet edge (0.30) must be Weak, got {ip_edges[0]['confidence_label']}. "
        "This regression would falsely escalate a circumstantial link to Medium/Strong."
    )


def test_empty_case_graph(db_session: Session):
    """An empty case yields a graph with 0 nodes and 0 edges."""
    case = Case(name="Empty Case", status=CaseStatus.ACTIVE.value)
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    graph = GraphBuilder.build_for_case(case.id, session=db_session)
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0

    result = serialize_graph(graph)
    assert result["nodes"] == []
    assert result["edges"] == []


# ---------------------------------------------------------------------------
# 5. Rule-Enforcement Mode Tests
# ---------------------------------------------------------------------------


def test_enforce_rules_true_overrides_stored_confidence(fraud_db):
    """
    When enforce_rules=True, the graph uses config-table weights
    (not the stored confidence_score column). This ensures the
    weighting table is authoritative and raw parser values don't bypass it.
    """
    case = fraud_db["case"]
    session = fraud_db["session"]
    entities = fraud_db["entities"]

    graph_enforced = GraphBuilder.build_for_case(
        case.id, session=session, enforce_rules=True
    )
    graph_raw = GraphBuilder.build_for_case(
        case.id, session=session, enforce_rules=False
    )

    mule1_phone_id = entities["mule1_phone"].id
    imei_id = entities["shared_imei"].id
    u, v = min(mule1_phone_id, imei_id), max(mule1_phone_id, imei_id)

    edge_enforced = graph_enforced.get_edge_data(u, v)
    edge_raw = graph_raw.get_edge_data(u, v)

    # Enforced should use CONFIDENCE_SHARED_IMEI (0.85)
    assert edge_enforced["confidence"] == pytest.approx(0.85)

    # Raw stored was 0.85 too, so both should agree in this case
    assert edge_raw["confidence"] == pytest.approx(0.85)
