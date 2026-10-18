"""Tests for confidence-calibrated autonomy. Deterministic (seed 42)."""

import pytest

from calib import appeals, calibration, decide, telemetry
from calib.audit import AuditLog
from calib.tiers import (
    FAST_PATH,
    FRAUD_RULE_ID,
    HIGH_STAKES,
    STANDARD,
    TIERS,
    tier_for_amount,
)


@pytest.fixture()
def con():
    return telemetry.seed_db()


# ---- tier registry -------------------------------------------------------

def test_three_tiers_registered():
    assert [t.name for t in TIERS] == ["FAST_PATH", "STANDARD", "HIGH_STAKES"]


def test_accuracy_bars():
    assert (FAST_PATH.accuracy_bar, STANDARD.accuracy_bar, HIGH_STAKES.accuracy_bar) == (0.90, 0.95, 0.99)


def test_each_tier_cites_rule_id():
    assert FAST_PATH.rule_id == "ACC-FAST-01"
    assert STANDARD.rule_id == "ACC-STD-01"
    assert HIGH_STAKES.rule_id == "ACC-HIGH-01"


def test_amount_bands():
    assert tier_for_amount(100, False)[0].name == "FAST_PATH"
    assert tier_for_amount(500, False)[0].name == "STANDARD"
    assert tier_for_amount(10000, False)[0].name == "STANDARD"
    assert tier_for_amount(10000.01, False)[0].name == "HIGH_STAKES"


def test_fraud_always_high_stakes():
    tier, via_fraud = tier_for_amount(100, True)
    assert tier.name == "HIGH_STAKES" and via_fraud
    assert FRAUD_RULE_ID == "ACC-HIGH-02"


def test_negative_amount_rejected():
    with pytest.raises(ValueError):
        tier_for_amount(-5, False)


# ---- decision routing ----------------------------------------------------

def test_fast_path_auto_decide(con):
    # CLM-0001 is in the low band; confidence 0.95 clears 0.90.
    rec = decide.decide(con, "CLM-0001", "approve", 0.95)
    assert rec["tier"] == "FAST_PATH" and rec["outcome"] == "decided"
    assert rec["rule_id"] == "ACC-FAST-01"


def test_fast_path_low_confidence_escalates(con):
    with pytest.raises(decide.Escalated):
        decide.decide(con, "CLM-0001", "approve", 0.85)


def test_escalation_is_recorded(con):
    with pytest.raises(decide.Escalated) as exc:
        decide.decide(con, "CLM-0001", "approve", 0.50)
    rec = decide.get_decision(con, exc.value.decision_id)
    assert rec["outcome"] == "escalated"


def test_standard_band_decide(con):
    # Find a mid-band claim.
    row = con.execute(
        "SELECT claim_id FROM claims WHERE amount BETWEEN 500 AND 10000 AND fraud_flag = 0 LIMIT 1"
    ).fetchone()
    rec = decide.decide(con, row[0], "deny", 0.97)
    assert rec["tier"] == "STANDARD" and rec["outcome"] == "decided"


def test_standard_low_confidence_escalates(con):
    row = con.execute(
        "SELECT claim_id FROM claims WHERE amount BETWEEN 500 AND 10000 AND fraud_flag = 0 LIMIT 1"
    ).fetchone()
    with pytest.raises(decide.Escalated):
        decide.decide(con, row[0], "deny", 0.90)


def test_high_stakes_amount_pending_human(con):
    row = con.execute("SELECT claim_id FROM claims WHERE amount > 10000 LIMIT 1").fetchone()
    rec = decide.decide(con, row[0], "approve", 0.999)
    assert rec["tier"] == "HIGH_STAKES" and rec["outcome"] == "pending_human"


def test_high_stakes_fraud_pending_human(con):
    row = con.execute("SELECT claim_id FROM claims WHERE fraud_flag = 1 LIMIT 1").fetchone()
    rec = decide.decide(con, row[0], "approve", 0.999)
    assert rec["tier"] == "HIGH_STAKES" and rec["rule_id"] == FRAUD_RULE_ID
    assert rec["outcome"] == "pending_human"


def test_human_decide_completes(con):
    row = con.execute("SELECT claim_id FROM claims WHERE amount > 10000 LIMIT 1").fetchone()
    rec = decide.decide(con, row[0], "approve", 0.999)
    done = decide.human_decide(con, rec["decision_id"], "deny", "R. Osei")
    assert done["outcome"] == "decided" and done["proposed"] == "deny"
    assert done["decided_by"] == "human:R. Osei"


def test_human_decide_wrong_state_rejected(con):
    rec = decide.decide(con, "CLM-0001", "approve", 0.95)
    with pytest.raises(decide.DecisionError):
        decide.human_decide(con, rec["decision_id"], "deny", "R. Osei")


def test_unknown_claim_rejected(con):
    with pytest.raises(decide.DecisionError):
        decide.decide(con, "CLM-9999", "approve", 0.95)


def test_bad_confidence_rejected(con):
    with pytest.raises(decide.DecisionError):
        decide.decide(con, "CLM-0001", "approve", 1.5)
    with pytest.raises(decide.DecisionError):
        decide.decide(con, "CLM-0001", "approve", -0.1)


def test_bad_proposed_rejected(con):
    with pytest.raises(decide.DecisionError):
        decide.decide(con, "CLM-0001", "maybe", 0.95)


def test_decision_cites_evidence(con):
    rec = decide.decide(con, "CLM-0001", "approve", 0.95)
    assert rec["evidence_cited"].startswith("CLM-0001-E")


def test_decision_ids_sequential(con):
    a = decide.decide(con, "CLM-0001", "approve", 0.95)
    b = decide.decide(con, "CLM-0002", "deny", 0.96)
    assert a["decision_id"] == "D-0001" and b["decision_id"] == "D-0002"


# ---- appeals --------------------------------------------------------------

def _decided(con, claim_id="CLM-0001", conf=0.95):
    return decide.decide(con, claim_id, "approve", conf)


def test_appeal_records_outcome(con):
    rec = _decided(con)
    ap = appeals.appeal(con, rec["decision_id"], "claimant", "second review please")
    assert ap["outcome"] in ("upheld", "overturned")
    assert ap["appellant"] == "claimant"


def test_appeal_adds_evidence(con):
    rec = _decided(con)
    before = con.execute("SELECT COUNT(*) FROM evidence WHERE claim_id='CLM-0001'").fetchone()[0]
    appeals.appeal(con, rec["decision_id"], "auditor", "spot check")
    after = con.execute("SELECT COUNT(*) FROM evidence WHERE claim_id='CLM-0001'").fetchone()[0]
    assert after == before + 1


def test_appeal_outcome_deterministic(con):
    r1 = _decided(con)
    a1 = appeals.appeal(con, r1["decision_id"], "claimant", "x")
    # Fresh DB, same inputs -> same appeal outcome.
    con2 = telemetry.seed_db()
    r2 = decide.decide(con2, "CLM-0001", "approve", 0.95)
    a2 = appeals.appeal(con2, r2["decision_id"], "claimant", "x")
    assert a1["outcome"] == a2["outcome"]


def test_double_appeal_rejected(con):
    rec = _decided(con)
    appeals.appeal(con, rec["decision_id"], "claimant", "x")
    with pytest.raises(appeals.AppealError):
        appeals.appeal(con, rec["decision_id"], "claimant", "y")


def test_appeal_unknown_decision_rejected(con):
    with pytest.raises(appeals.AppealError):
        appeals.appeal(con, "D-9999", "claimant", "x")


def test_appeal_pending_human_rejected(con):
    row = con.execute("SELECT claim_id FROM claims WHERE amount > 10000 LIMIT 1").fetchone()
    rec = decide.decide(con, row[0], "approve", 0.999)
    with pytest.raises(appeals.AppealError):
        appeals.appeal(con, rec["decision_id"], "claimant", "x")


def test_appeal_escalated_rejected(con):
    with pytest.raises(decide.Escalated) as exc:
        decide.decide(con, "CLM-0001", "approve", 0.50)
    with pytest.raises(appeals.AppealError):
        appeals.appeal(con, exc.value.decision_id, "claimant", "x")


def test_appeal_rate_math(con):
    for cid in ("CLM-0001", "CLM-0002", "CLM-0003"):
        r = decide.decide(con, cid, "approve", 0.95)
        assert r["tier"] == "FAST_PATH"
    rec = con.execute("SELECT decision_id FROM decisions LIMIT 1").fetchone()
    appeals.appeal(con, rec[0], "claimant", "x")
    stats = appeals.appeal_rate(con, "FAST_PATH")
    assert stats["decisions"] == 3 and stats["appeals"] == 1
    assert stats["appeal_rate"] == pytest.approx(1 / 3)


def test_appeal_rate_empty_tier(con):
    stats = appeals.appeal_rate(con, "HIGH_STAKES")
    assert stats["decisions"] == 0 and stats["appeal_rate"] == 0.0


# ---- calibration ----------------------------------------------------------

def test_reliability_table_shape(con):
    table = calibration.reliability_table(con)
    assert [r["tier"] for r in table] == ["FAST_PATH", "STANDARD", "HIGH_STAKES"]
    for row in table:
        assert row["n"] == 40
        assert 0.0 <= row["accuracy"] <= 1.0


def test_fast_path_flagged_miscalibrated(con):
    flagged = calibration.miscalibrated_tiers(con)
    assert "FAST_PATH" in flagged  # seeded true accuracy 0.88 < 0.90 bar


def test_standard_not_flagged(con):
    flagged = calibration.miscalibrated_tiers(con)
    assert "STANDARD" not in flagged  # seeded 0.96 >= 0.95 bar


def test_gap_is_accuracy_minus_bar(con):
    for row in calibration.reliability_table(con):
        assert row["gap"] == pytest.approx(row["accuracy"] - row["accuracy_bar"], abs=0.002)


def test_calibration_deterministic(con):
    t1 = calibration.reliability_table(con)
    t2 = calibration.reliability_table(telemetry.seed_db())
    assert t1 == t2


# ---- audit -----------------------------------------------------------------

def test_audit_chain_verifies():
    log = AuditLog()
    log.record("decision", {"id": "D-0001"})
    log.record("appeal", {"id": "A-0001"})
    assert log.verify() and len(log.entries) == 2


def test_audit_tamper_detected():
    log = AuditLog()
    log.record("decision", {"id": "D-0001"})
    log.entries[0]["payload"]["id"] = "D-9999"
    assert not log.verify()


def test_audit_seq_increments():
    log = AuditLog()
    a = log.record("x", {})
    b = log.record("y", {})
    assert (a["seq"], b["seq"]) == (1, 2)
    assert b["prev"] == a["hash"]


def test_audit_save_load(tmp_path):
    log = AuditLog()
    log.record("decision", {"id": "D-0001"})
    p = str(tmp_path / "audit.json")
    log.save(p)
    assert AuditLog.load(p).verify()


# ---- demo -------------------------------------------------------------------

def test_scenario_runs():
    from calib import demo_helpers
    s = demo_helpers.run_scenario()
    assert s["claims"] == 24
    assert s["decided"] + s["escalated"] + s["human_decided"] == 24
    assert s["audit_ok"] is True
    assert s["appeals_filed"] == 2


def test_scenario_deterministic():
    from calib import demo_helpers
    a = demo_helpers.run_scenario()
    b = demo_helpers.run_scenario()
    assert a == b


def test_format_summary_mentions_calibration():
    from calib import demo_helpers
    text = demo_helpers.format_summary(demo_helpers.run_scenario())
    assert "FAST_PATH" in text and "MISCALIBRATED" in text
