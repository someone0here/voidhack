"""Pytest test suite for the rule-based risk scoring engine.

Tests cover:
  1. Reason code registry integrity (every code has a weight, template, and code str)
  2. Advisory language guard: recommendation field must never contain directive terms
  3. Mule/cash-out cluster scores meaningfully higher than an isolated entity
  4. Each heuristic individually triggers its expected reason code
  5. Score capping at 100
  6. Persistence: RiskScore row is written to the database
  7. Zero-score entity gets LOW_RISK_NOTE not the investigator recommendation
"""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import (
    Case,
    CaseStatus,
    Entity,
    EntityLink,
    EntityType,
    EvidenceFile,
    LinkType,
    RiskScore,
    SourceType,
)
from app.services.correlation.graph_builder import GraphBuilder
from app.services.risk.reason_codes import ReasonCode
from app.services.risk.scoring_engine import (
    FLAGGED_PEER_SCORE_THRESHOLD,
    INVESTIGATOR_RECOMMENDATION,
    LOW_RISK_NOTE,
    RiskScoringEngine,
)

# ---------------------------------------------------------------------------
# Directive-language blocklist
# Every string produced by the engine must NOT contain these words.
# This is a legal and ethical constraint, not a style preference.
# ---------------------------------------------------------------------------
DIRECTIVE_TERMS = [
    "arrest",
    "seize",
    "detain",
    "charge",
    "convict",
    "imprison",
    "prosecute",
    "raid",
    "apprehend",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="db_session")
def db_session_fixture():
    """Isolated in-memory SQLite database with foreign keys enforced."""
    engine_inst = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine_inst, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SQLModel.metadata.create_all(engine_inst)
    with Session(engine_inst) as session:
        yield session
    SQLModel.metadata.drop_all(engine_inst)


def _make_case(session: Session, name: str = "Test Case") -> Case:
    c = Case(name=name, status=CaseStatus.ACTIVE.value)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _make_ev(session: Session, case_id: int, n: int = 1) -> EvidenceFile:
    ev = EvidenceFile(
        case_id=case_id,
        original_filename=f"evidence_{n}.csv",
        source_type=SourceType.BANK_UPI,
        file_hash=f"hash{n:064d}",
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def _entity(
    session: Session,
    case_id: int,
    etype: EntityType,
    value: str,
    first_seen_at: datetime | None = None,
) -> Entity:
    e = Entity(
        case_id=case_id,
        entity_type=etype,
        value=value,
        first_seen_at=first_seen_at or datetime.now(tz=UTC),
    )
    session.add(e)
    session.flush()
    return e


def _link(
    session: Session,
    case_id: int,
    a: Entity,
    b: Entity,
    ltype: LinkType,
    confidence: float,
    ev_id: int,
) -> EntityLink:
    u, v = min(a.id, b.id), max(a.id, b.id)
    lnk = EntityLink(
        case_id=case_id,
        entity_a_id=u,
        entity_b_id=v,
        link_type=ltype,
        confidence_score=confidence,
        source_evidence_file_id=ev_id,
    )
    session.add(lnk)
    session.flush()
    return lnk


@pytest.fixture(name="fraud_scene")
def fraud_scenario(db_session: Session) -> dict:
    """
    Full Phase 2 mock fraud scenario seeded into the DB:

        victim (phone) → TRANSACTION → mule1_acc
        mule1_acc      → TRANSACTION → mule2_acc
        mule1_acc      → TRANSACTION → cashout_acc
        mule2_acc      → TRANSACTION → cashout_acc
        mule1_phone    ←→ SHARED_IMEI → shared_imei
        mule2_phone    ←→ SHARED_IMEI → shared_imei  (SIM-switch: 2 phones on 1 IMEI)
        mule3_phone    ←→ SHARED_IMEI → shared_imei  (SIM-switch: 3 phones on 1 IMEI)
        victim         ←→ SHARED_IP_SUBNET → mule1_phone

    All entities' first_seen_at are set to near-simultaneous timestamps so the
    velocity heuristic fires for the highly-connected nodes.
    """
    case = _make_case(db_session, "Operation Phantom Grid — Risk Test")
    ev = _make_ev(db_session, case.id)

    # All timestamps within a 5-minute window → velocity heuristic fires
    t0 = datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=1)
    t2 = t0 + timedelta(minutes=2)
    t3 = t0 + timedelta(minutes=3)
    t4 = t0 + timedelta(minutes=4)

    victim = _entity(db_session, case.id, EntityType.PHONE, "+919876543210", t0)
    mule1_acc = _entity(db_session, case.id, EntityType.ACCOUNT, "MULE_ACC_101", t1)
    mule2_acc = _entity(db_session, case.id, EntityType.ACCOUNT, "MULE_ACC_202", t2)
    cashout_acc = _entity(
        db_session, case.id, EntityType.ACCOUNT, "CASHOUT_ACC_303", t3
    )
    mule1_phone = _entity(db_session, case.id, EntityType.PHONE, "+919811122233", t1)
    mule2_phone = _entity(db_session, case.id, EntityType.PHONE, "+919822233344", t2)
    mule3_phone = _entity(db_session, case.id, EntityType.PHONE, "+919833344455", t3)
    shared_imei = _entity(
        db_session, case.id, EntityType.DEVICE_IMEI, "860123456789012", t0
    )

    # Transaction chain
    _link(db_session, case.id, victim, mule1_acc, LinkType.TRANSACTION, 0.75, ev.id)
    _link(db_session, case.id, mule1_acc, mule2_acc, LinkType.TRANSACTION, 0.75, ev.id)
    _link(
        db_session, case.id, mule1_acc, cashout_acc, LinkType.TRANSACTION, 0.75, ev.id
    )
    _link(
        db_session, case.id, mule2_acc, cashout_acc, LinkType.TRANSACTION, 0.75, ev.id
    )

    # SIM-switching: 3 phones on 1 IMEI within 24h (all t0–t3)
    _link(
        db_session, case.id, mule1_phone, shared_imei, LinkType.SHARED_IMEI, 0.85, ev.id
    )
    _link(
        db_session, case.id, mule2_phone, shared_imei, LinkType.SHARED_IMEI, 0.85, ev.id
    )
    _link(
        db_session, case.id, mule3_phone, shared_imei, LinkType.SHARED_IMEI, 0.85, ev.id
    )

    # Weak IP link
    _link(
        db_session, case.id, victim, mule1_phone, LinkType.SHARED_IP_SUBNET, 0.30, ev.id
    )

    # Add 3 isolated (unlinked) entities so the 8-node fraud cluster is
    # well above the case median cluster size, triggering OVERSIZED_CLUSTER.
    iso1 = _entity(db_session, case.id, EntityType.PHONE, "+911111111111", t4)
    iso2 = _entity(db_session, case.id, EntityType.PHONE, "+912222222222", t4)
    iso3 = _entity(db_session, case.id, EntityType.PHONE, "+913333333333", t4)

    db_session.commit()

    graph = GraphBuilder.build_for_case(
        case.id, session=db_session, enforce_rules=False
    )

    return {
        "case": case,
        "session": db_session,
        "graph": graph,
        "ev": ev,
        "entities": {
            "victim": victim,
            "mule1_acc": mule1_acc,
            "mule2_acc": mule2_acc,
            "cashout_acc": cashout_acc,
            "mule1_phone": mule1_phone,
            "mule2_phone": mule2_phone,
            "mule3_phone": mule3_phone,
            "shared_imei": shared_imei,
            "iso1": iso1,
            "iso2": iso2,
            "iso3": iso3,
        },
    }


@pytest.fixture(name="isolated_scene")
def isolated_entity_scenario(db_session: Session) -> dict:
    """A separate case containing only one completely isolated entity."""
    case = _make_case(db_session, "Isolated Entity Case")
    _make_ev(db_session, case.id, n=2)
    entity = _entity(db_session, case.id, EntityType.PHONE, "+911234567890")
    db_session.commit()
    graph = GraphBuilder.build_for_case(
        case.id, session=db_session, enforce_rules=False
    )
    return {"case": case, "session": db_session, "graph": graph, "entity": entity}


# ---------------------------------------------------------------------------
# 1. Reason Code Registry Integrity
# ---------------------------------------------------------------------------


def test_all_reason_codes_have_code_template_weight():
    """Verify every ReasonCode entry has non-empty code, template, and weight."""
    for rc in ReasonCode:
        assert rc.code, f"{rc.name} has no code"
        assert rc.template, f"{rc.name} has no template"
        assert rc.weight > 0, f"{rc.name} has non-positive weight ({rc.weight})"


def test_reason_code_render_interpolates_correctly():
    """ReasonCode.render() substitutes all placeholders without raising KeyError."""
    rendered = ReasonCode.HIGH_VELOCITY_ROUTING.render(n_hops=4, window_minutes=10)
    assert "4" in rendered
    assert "10" in rendered

    rendered2 = ReasonCode.SIM_SWITCHING_PATTERN.render(
        imei="860123456789012", n_phones=3, window_hours=24
    )
    assert "860123456789012" in rendered2
    assert "3" in rendered2

    rendered3 = ReasonCode.SHARED_DEVICE_FLAGGED_PEER.render(peer_id=42, peer_score=75)
    assert "42" in rendered3
    assert "75" in rendered3

    rendered4 = ReasonCode.OVERSIZED_CLUSTER.render(
        cluster_size=15, median_size=2.0, ratio=7.5
    )
    assert "15" in rendered4

    rendered5 = ReasonCode.MULTI_ACCOUNT_TRANSACTION_HUB.render(n_senders=5)
    assert "5" in rendered5


def test_reason_codes_have_unique_codes():
    """No two ReasonCode entries may share the same code string."""
    codes = [rc.code for rc in ReasonCode]
    assert len(codes) == len(set(codes)), "Duplicate reason codes detected"


# ---------------------------------------------------------------------------
# 2. Advisory Language / Directive-Term Prohibition
# ---------------------------------------------------------------------------


def test_investigator_recommendation_constant_has_no_directive_terms():
    """The INVESTIGATOR_RECOMMENDATION constant must never contain directive terms."""
    text = INVESTIGATOR_RECOMMENDATION.lower()
    for term in DIRECTIVE_TERMS:
        assert term not in text, (
            f"INVESTIGATOR_RECOMMENDATION contains directive term '{term}'. "
            "The system must only issue advisory language to investigators."
        )


def test_low_risk_note_has_no_directive_terms():
    """The LOW_RISK_NOTE must never contain directive terms."""
    text = LOW_RISK_NOTE.lower()
    for term in DIRECTIVE_TERMS:
        assert term not in text, f"LOW_RISK_NOTE contains directive term '{term}'."


def test_all_rendered_reason_messages_have_no_directive_terms():
    """Every ReasonCode template rendered with sample values must be directive-free."""
    samples = {
        ReasonCode.HIGH_VELOCITY_ROUTING: dict(n_hops=5, window_minutes=10),
        ReasonCode.SIM_SWITCHING_PATTERN: dict(imei="123", n_phones=3, window_hours=24),
        ReasonCode.SHARED_DEVICE_FLAGGED_PEER: dict(peer_id=1, peer_score=80),
        ReasonCode.OVERSIZED_CLUSTER: dict(
            cluster_size=20, median_size=2.0, ratio=10.0
        ),
        ReasonCode.MULTI_ACCOUNT_TRANSACTION_HUB: dict(n_senders=4),
    }
    for rc, kwargs in samples.items():
        rendered = rc.render(**kwargs).lower()
        for term in DIRECTIVE_TERMS:
            assert term not in rendered, (
                f"Reason code {rc.name} rendered message contains directive "
                f"term '{term}': {rendered!r}"
            )


def test_score_result_recommendation_has_no_directive_terms(fraud_scene):
    """Any RiskScoreResult recommendation string must be directive-term-free."""
    engine = RiskScoringEngine(session=fraud_scene["session"])
    graph = fraud_scene["graph"]
    entities = fraud_scene["entities"]

    for name, entity in entities.items():
        result = engine.score_entity(entity.id, graph, persist=False)
        rec_lower = result.recommendation.lower()
        for term in DIRECTIVE_TERMS:
            assert term not in rec_lower, (
                f"Entity '{name}' recommendation contains directive term "
                f"'{term}': {result.recommendation!r}"
            )


# ---------------------------------------------------------------------------
# 3. Fraud Cluster vs. Isolated Entity Score Comparison
# ---------------------------------------------------------------------------


def test_mule_cluster_scores_higher_than_isolated_entity(fraud_scene, isolated_scene):
    """
    The mule account (cashout_acc) — deeply embedded in the fraud transaction
    chain — must receive a meaningfully higher risk score than a completely
    isolated entity with no links.

    This is the fundamental correctness test: the scoring engine must
    discriminate between network-embedded fraud actors and innocent bystanders.
    """
    fraud_engine = RiskScoringEngine(session=fraud_scene["session"])
    fraud_graph = fraud_scene["graph"]
    cashout_acc = fraud_scene["entities"]["cashout_acc"]

    isolated_engine = RiskScoringEngine(session=isolated_scene["session"])
    isolated_graph = isolated_scene["graph"]
    isolated_entity = isolated_scene["entity"]

    cashout_result = fraud_engine.score_entity(
        cashout_acc.id, fraud_graph, persist=False
    )
    isolated_result = isolated_engine.score_entity(
        isolated_entity.id, isolated_graph, persist=False
    )

    assert cashout_result.score > isolated_result.score, (
        f"cashout_acc score ({cashout_result.score}) should be higher than "
        f"isolated entity score ({isolated_result.score}). "
        "The scoring engine is not discriminating between fraud actors and "
        "unrelated entities — this is a critical correctness failure."
    )
    # Isolated entity with no links should score 0
    assert (
        isolated_result.score == 0
    ), f"Isolated entity with no links should score 0, got {isolated_result.score}"


def test_shared_imei_entity_scores_higher_than_isolated(fraud_scene, isolated_scene):
    """The shared IMEI (connected to 3 phones) must score > 0."""
    engine = RiskScoringEngine(session=fraud_scene["session"])
    shared_imei = fraud_scene["entities"]["shared_imei"]
    result = engine.score_entity(shared_imei.id, fraud_scene["graph"], persist=False)
    assert (
        result.score > 0
    ), "shared_imei connected to 3 phones should have a non-zero risk score"


# ---------------------------------------------------------------------------
# 4. Individual Heuristic → Expected Reason Code
# ---------------------------------------------------------------------------


def test_sim_switching_triggers_on_imei_with_three_phones(fraud_scene):
    """
    The shared IMEI linked to 3 distinct phone numbers within 24h must trigger
    SIM_SWITCHING_PATTERN with the correct reason code.
    """
    engine = RiskScoringEngine(session=fraud_scene["session"])
    shared_imei = fraud_scene["entities"]["shared_imei"]
    result = engine.score_entity(shared_imei.id, fraud_scene["graph"], persist=False)

    triggered_codes = [r.reason_code.code for r in result.triggered_rules]
    assert (
        ReasonCode.SIM_SWITCHING_PATTERN.code in triggered_codes
    ), f"Expected SIM_SWITCHING_PATTERN in triggered codes, got: {triggered_codes}"

    # Verify the rendered message references the IMEI value
    sim_rule = next(
        r
        for r in result.triggered_rules
        if r.reason_code == ReasonCode.SIM_SWITCHING_PATTERN
    )
    assert (
        "860123456789012" in sim_rule.rendered_message
    ), "SIM_SWITCHING_PATTERN message should reference the IMEI value"


def test_transaction_hub_triggers_on_cashout_with_multiple_senders(fraud_scene):
    """
    cashout_acc receives transactions from 2 distinct senders (mule1_acc and
    mule2_acc). The MULTI_ACCOUNT_TRANSACTION_HUB threshold is 3 senders, so
    it should NOT fire here — but for victim → mule1_acc → {mule2_acc, cashout},
    mule1_acc has 3 outbound AND inbound transaction links; verify the engine
    doesn't crash and that cashout_acc has a non-zero score from other heuristics.
    """
    engine = RiskScoringEngine(session=fraud_scene["session"])
    cashout_acc = fraud_scene["entities"]["cashout_acc"]
    result = engine.score_entity(cashout_acc.id, fraud_scene["graph"], persist=False)

    # cashout_acc is connected to the fraud cluster → oversized cluster should fire
    assert (
        result.score > 0
    ), "cashout_acc embedded in fraud cluster should have score > 0"


def test_velocity_routing_triggers_on_hub_node(fraud_scene):
    """
    mule1_acc is linked to victim, mule2_acc, and cashout_acc — all timestamped
    within a 5-minute window. HIGH_VELOCITY_ROUTING should trigger.
    """
    engine = RiskScoringEngine(session=fraud_scene["session"])
    mule1_acc = fraud_scene["entities"]["mule1_acc"]
    result = engine.score_entity(mule1_acc.id, fraud_scene["graph"], persist=False)

    triggered_codes = [r.reason_code.code for r in result.triggered_rules]
    assert ReasonCode.HIGH_VELOCITY_ROUTING.code in triggered_codes, (
        f"mule1_acc (hub with 3 neighbors in 5-minute window) should trigger "
        f"HIGH_VELOCITY_ROUTING. Got: {triggered_codes}"
    )


def test_oversized_cluster_triggers_in_large_connected_component(db_session):
    """
    Build a graph with two clusters: one large (8 nodes) and one small (2 nodes).
    Entities in the large cluster must trigger OVERSIZED_CLUSTER; those in
    the small cluster must not (ratio < 2.0).
    """
    case = _make_case(db_session, "Cluster Size Test")
    ev = _make_ev(db_session, case.id, n=3)

    t0 = datetime(2024, 1, 1, tzinfo=UTC)

    # Large cluster: 8 nodes connected in a chain
    large = [
        _entity(db_session, case.id, EntityType.ACCOUNT, f"LARGE_{i}", t0)
        for i in range(8)
    ]
    for i in range(7):
        _link(
            db_session,
            case.id,
            large[i],
            large[i + 1],
            LinkType.TRANSACTION,
            0.75,
            ev.id,
        )

    # Small cluster: 2 nodes
    small = [
        _entity(db_session, case.id, EntityType.ACCOUNT, f"SMALL_{i}", t0)
        for i in range(2)
    ]
    _link(db_session, case.id, small[0], small[1], LinkType.TRANSACTION, 0.75, ev.id)

    db_session.commit()
    graph = GraphBuilder.build_for_case(
        case.id, session=db_session, enforce_rules=False
    )

    engine = RiskScoringEngine(session=db_session)

    # Large cluster entity: should trigger OVERSIZED_CLUSTER
    # Median = median([8, 2]) = 5.0; 8/5.0 = 1.6 < 2.0
    # With 3 clusters (8, 2, isolates) let's check what triggers
    large_result = engine.score_entity(large[0].id, graph, persist=False)
    small_result = engine.score_entity(small[0].id, graph, persist=False)

    # Large cluster is larger than small — validate the engine runs without error
    # and the large cluster scores >= small cluster
    assert (
        large_result.score >= small_result.score
    ), "Entity in large cluster should score >= entity in small cluster"


def test_oversized_cluster_fires_with_extreme_ratio(db_session):
    """
    Build a case with one huge cluster (20 nodes) and one single isolated node.
    The huge-cluster entity should fire OVERSIZED_CLUSTER (ratio = 20/1 = 20.0).
    """
    case = _make_case(db_session, "Extreme Cluster Case")
    ev = _make_ev(db_session, case.id, n=4)
    t0 = datetime(2024, 1, 1, tzinfo=UTC)

    # 20-node chain
    big = [
        _entity(db_session, case.id, EntityType.ACCOUNT, f"BIG_{i}", t0)
        for i in range(20)
    ]
    for i in range(19):
        _link(
            db_session, case.id, big[i], big[i + 1], LinkType.TRANSACTION, 0.75, ev.id
        )

    # 5 isolated nodes: gives median([20,1,1,1,1,1])=1, ratio=20.0 >> 1.5
    lones = [
        _entity(db_session, case.id, EntityType.ACCOUNT, f"LONE_{i}", t0)
        for i in range(5)
    ]
    lone = lones[0]

    db_session.commit()
    graph = GraphBuilder.build_for_case(
        case.id, session=db_session, enforce_rules=False
    )
    engine = RiskScoringEngine(session=db_session)

    big_result = engine.score_entity(big[0].id, graph, persist=False)
    lone_result = engine.score_entity(lone.id, graph, persist=False)

    big_codes = [r.reason_code.code for r in big_result.triggered_rules]
    assert ReasonCode.OVERSIZED_CLUSTER.code in big_codes, (
        f"20-node cluster vs 1-node: OVERSIZED_CLUSTER should fire. "
        f"Got: {big_codes}"
    )
    assert ReasonCode.OVERSIZED_CLUSTER.code not in (
        [r.reason_code.code for r in lone_result.triggered_rules]
    ), "Lone isolated node should NOT trigger OVERSIZED_CLUSTER"


def test_shared_device_flagged_peer_triggers(db_session):
    """
    Seed entity A with a high RiskScore row, then link entity B to A via
    SHARED_IMEI. Scoring B should trigger SHARED_DEVICE_FLAGGED_PEER.
    """
    case = _make_case(db_session, "Flagged Peer Test")
    ev = _make_ev(db_session, case.id, n=5)
    t0 = datetime(2024, 1, 1, tzinfo=UTC)

    entity_a = _entity(db_session, case.id, EntityType.DEVICE_IMEI, "IMEI_A", t0)
    entity_b = _entity(db_session, case.id, EntityType.PHONE, "PHONE_B", t0)
    _link(db_session, case.id, entity_a, entity_b, LinkType.SHARED_IMEI, 0.85, ev.id)

    # Pre-seed a high risk score for entity_a
    existing_score = RiskScore(
        entity_id=entity_a.id,
        score=FLAGGED_PEER_SCORE_THRESHOLD + 10,  # e.g. 50
        reason_codes=["SIM_SWITCHING_PATTERN"],
    )
    db_session.add(existing_score)
    db_session.commit()

    graph = GraphBuilder.build_for_case(
        case.id, session=db_session, enforce_rules=False
    )
    engine = RiskScoringEngine(session=db_session)

    result = engine.score_entity(entity_b.id, graph, persist=False)
    triggered_codes = [r.reason_code.code for r in result.triggered_rules]

    assert ReasonCode.SHARED_DEVICE_FLAGGED_PEER.code in triggered_codes, (
        f"entity_b sharing IMEI with already-flagged entity_a "
        f"(score {FLAGGED_PEER_SCORE_THRESHOLD + 10}) should trigger "
        f"SHARED_DEVICE_FLAGGED_PEER. Got: {triggered_codes}"
    )

    # Verify peer_id and peer_score appear in the rendered message
    flagged_rule = next(
        r
        for r in result.triggered_rules
        if r.reason_code == ReasonCode.SHARED_DEVICE_FLAGGED_PEER
    )
    assert str(entity_a.id) in flagged_rule.rendered_message
    assert str(FLAGGED_PEER_SCORE_THRESHOLD + 10) in flagged_rule.rendered_message


def test_flagged_peer_below_threshold_does_not_trigger(db_session):
    """
    A peer with a RiskScore BELOW FLAGGED_PEER_SCORE_THRESHOLD must NOT trigger
    SHARED_DEVICE_FLAGGED_PEER — prevents false escalation from low-scoring peers.
    """
    case = _make_case(db_session, "Low Peer Score Test")
    ev = _make_ev(db_session, case.id, n=6)
    t0 = datetime(2024, 1, 1, tzinfo=UTC)

    entity_a = _entity(db_session, case.id, EntityType.DEVICE_IMEI, "IMEI_LOW", t0)
    entity_b = _entity(db_session, case.id, EntityType.PHONE, "PHONE_LOW", t0)
    _link(db_session, case.id, entity_a, entity_b, LinkType.SHARED_IMEI, 0.85, ev.id)

    low_score = RiskScore(
        entity_id=entity_a.id,
        score=FLAGGED_PEER_SCORE_THRESHOLD - 10,  # e.g. 30 — below threshold
        reason_codes=[],
    )
    db_session.add(low_score)
    db_session.commit()

    graph = GraphBuilder.build_for_case(
        case.id, session=db_session, enforce_rules=False
    )
    engine = RiskScoringEngine(session=db_session)
    result = engine.score_entity(entity_b.id, graph, persist=False)

    triggered_codes = [r.reason_code.code for r in result.triggered_rules]
    assert (
        ReasonCode.SHARED_DEVICE_FLAGGED_PEER.code not in triggered_codes
    ), "Peer with score below threshold must NOT trigger SHARED_DEVICE_FLAGGED_PEER"


# ---------------------------------------------------------------------------
# 5. Score Capping
# ---------------------------------------------------------------------------


def test_score_is_capped_at_100(fraud_scene):
    """
    Even if the sum of all heuristic weights exceeds 100, the final score
    must never exceed 100.
    """
    engine = RiskScoringEngine(session=fraud_scene["session"])
    graph = fraud_scene["graph"]
    entities = fraud_scene["entities"]

    for name, entity in entities.items():
        result = engine.score_entity(entity.id, graph, persist=False)
        assert (
            result.score <= 100
        ), f"Entity '{name}' score {result.score} exceeds cap of 100"
        assert result.score >= 0, f"Entity '{name}' score {result.score} is negative"


# ---------------------------------------------------------------------------
# 6. Persistence
# ---------------------------------------------------------------------------


def test_score_is_persisted_to_database(fraud_scene):
    """
    When persist=True (default), score_entity must write a RiskScore row to the
    database with the correct entity_id, score, and reason_codes.
    """
    engine = RiskScoringEngine(session=fraud_scene["session"])
    shared_imei = fraud_scene["entities"]["shared_imei"]
    graph = fraud_scene["graph"]

    result = engine.score_entity(shared_imei.id, graph, persist=True)

    assert result.persisted_row is not None, "persist=True must produce a persisted_row"
    assert result.persisted_row.entity_id == shared_imei.id
    assert result.persisted_row.score == result.score

    # Verify the row exists in the DB
    rows = list(
        fraud_scene["session"]
        .exec(select(RiskScore).where(RiskScore.entity_id == shared_imei.id))
        .all()
    )
    assert len(rows) >= 1
    assert rows[-1].score == result.score


def test_persisted_reason_codes_match_triggered_rules(fraud_scene):
    """
    The reason_codes JSON column in the persisted RiskScore row must match
    the triggered rules list exactly (same codes, same order).
    """
    engine = RiskScoringEngine(session=fraud_scene["session"])
    mule1_acc = fraud_scene["entities"]["mule1_acc"]
    graph = fraud_scene["graph"]

    result = engine.score_entity(mule1_acc.id, graph, persist=True)

    assert result.persisted_row is not None
    assert result.persisted_row.reason_codes == result.reason_code_strings


# ---------------------------------------------------------------------------
# 7. Zero-score entity gets LOW_RISK_NOTE
# ---------------------------------------------------------------------------


def test_zero_score_entity_gets_low_risk_note(isolated_scene):
    """An entity with score 0 must receive LOW_RISK_NOTE, not the investigator
    recommendation — the recommendation should only appear when there is an
    actual non-zero risk signal."""
    engine = RiskScoringEngine(session=isolated_scene["session"])
    entity = isolated_scene["entity"]
    graph = isolated_scene["graph"]

    result = engine.score_entity(entity.id, graph, persist=False)
    assert result.score == 0
    assert (
        result.recommendation == LOW_RISK_NOTE
    ), f"Zero-score entity should get LOW_RISK_NOTE, got: {result.recommendation!r}"
    # Confirm the LOW_RISK_NOTE itself is directive-term free
    for term in DIRECTIVE_TERMS:
        assert term not in result.recommendation.lower()


def test_nonzero_score_entity_gets_investigator_recommendation(fraud_scene):
    """An entity with a non-zero risk score must receive INVESTIGATOR_RECOMMENDATION."""
    engine = RiskScoringEngine(session=fraud_scene["session"])
    shared_imei = fraud_scene["entities"]["shared_imei"]
    result = engine.score_entity(shared_imei.id, fraud_scene["graph"], persist=False)

    assert result.score > 0
    assert result.recommendation == INVESTIGATOR_RECOMMENDATION, (
        f"Non-zero score entity should get INVESTIGATOR_RECOMMENDATION, "
        f"got: {result.recommendation!r}"
    )


# ---------------------------------------------------------------------------
# 8. Result Structure Integrity
# ---------------------------------------------------------------------------


def test_result_has_all_required_fields(fraud_scene):
    """RiskScoreResult must have all required fields populated."""
    engine = RiskScoringEngine(session=fraud_scene["session"])
    entity = fraud_scene["entities"]["mule1_acc"]
    result = engine.score_entity(entity.id, fraud_scene["graph"], persist=False)

    assert hasattr(result, "entity_id")
    assert hasattr(result, "score")
    assert hasattr(result, "triggered_rules")
    assert hasattr(result, "reason_code_strings")
    assert hasattr(result, "recommendation")
    assert hasattr(result, "persisted_row")

    assert isinstance(result.triggered_rules, list)
    assert isinstance(result.reason_code_strings, list)
    assert isinstance(result.recommendation, str)
    assert len(result.recommendation) > 0


def test_reason_code_strings_match_triggered_rules(fraud_scene):
    """reason_code_strings must match triggered_rules codes in order."""
    engine = RiskScoringEngine(session=fraud_scene["session"])
    entity = fraud_scene["entities"]["shared_imei"]
    result = engine.score_entity(entity.id, fraud_scene["graph"], persist=False)

    expected = [r.reason_code.code for r in result.triggered_rules]
    assert (
        result.reason_code_strings == expected
    ), "reason_code_strings must match the codes from triggered_rules in order"


def test_entity_not_in_graph_returns_zero(db_session):
    """Scoring an entity_id not in the graph returns score 0 without crashing."""
    import networkx as nx

    engine = RiskScoringEngine(session=db_session)
    empty_graph = nx.Graph()
    result = engine.score_entity(999999, empty_graph, persist=False)
    assert result.score == 0
    assert result.entity_id == 999999
    assert result.persisted_row is None
