"""Stdlib demo helpers: run an end-to-end scenario and summarize it.

All numbers returned here come from real runs against the seeded database;
the README quotes them verbatim.
"""

from __future__ import annotations

import sqlite3

from calib import appeals, calibration, decide, telemetry
from calib.audit import AuditLog
from calib.tiers import TIERS


def run_scenario(con: sqlite3.Connection | None = None) -> dict:
    """Decide every open claim, file a few appeals, and summarize.

    The model's proposed decision/confidence per claim is deterministic:
    confidence is derived from the claim's evidence lean so the scenario is
    reproducible.
    """
    con = con or telemetry.seed_db()
    log = AuditLog()

    claims = con.execute("SELECT * FROM claims ORDER BY claim_id").fetchall()
    decided, escalated, pending = 0, 0, 0
    per_tier: dict[str, int] = {t.name: 0 for t in TIERS}
    for claim in claims:
        ev = con.execute(
            "SELECT supports FROM evidence WHERE claim_id = ?", (claim["claim_id"],)
        ).fetchall()
        lean = sum(r[0] for r in ev)
        proposed = "approve" if lean >= 0 else "deny"
        # Confidence scales with evidence agreement; deterministic.
        agree = sum(1 for r in ev if (r[0] >= 0) == (lean >= 0))
        confidence = round(0.80 + 0.19 * (agree / max(len(ev), 1)), 3)
        try:
            rec = decide.decide(con, claim["claim_id"], proposed, confidence)
            per_tier[rec["tier"]] += 1
            log.record("decision", {"decision_id": rec["decision_id"], "tier": rec["tier"],
                                    "outcome": rec["outcome"]})
            if rec["outcome"] == "pending_human":
                decide.human_decide(con, rec["decision_id"], proposed, "R. Osei")
                pending += 1
                log.record("human_decision", {"decision_id": rec["decision_id"]})
            else:
                decided += 1
        except decide.Escalated as exc:
            escalated += 1
            log.record("escalation", {"decision_id": exc.decision_id})

    # Appeal the first two final decisions to exercise the appeal path.
    appealed = 0
    for row in con.execute(
        "SELECT decision_id FROM decisions WHERE outcome='decided' ORDER BY decision_id LIMIT 2"
    ).fetchall():
        ap = appeals.appeal(con, row[0], "claimant", "requesting second review")
        log.record("appeal", {"appeal_id": ap["appeal_id"], "outcome": ap["outcome"]})
        appealed += 1

    appeal_rates = {t.name: appeals.appeal_rate(con, t.name)["appeal_rate"] for t in TIERS}
    calib = calibration.reliability_table(con)
    return {
        "claims": len(claims),
        "decided": decided,
        "escalated": escalated,
        "human_decided": pending,
        "per_tier": per_tier,
        "appeals_filed": appealed,
        "appeal_rates": {k: round(v, 3) for k, v in appeal_rates.items()},
        "calibration": calib,
        "miscalibrated": calibration.miscalibrated_tiers(con),
        "audit_ok": log.verify(),
        "audit_entries": len(log.entries),
    }


def format_summary(s: dict) -> str:
    lines = [
        f"Claims processed: {s['claims']}",
        f"Auto/spot-check decided: {s['decided']}, human-decided: {s['human_decided']}, "
        f"escalated (no tier cleared): {s['escalated']}",
        "Decisions per tier: " + ", ".join(f"{k}={v}" for k, v in s["per_tier"].items()),
        f"Appeals filed: {s['appeals_filed']}; appeal rates: {s['appeal_rates']}",
        "Calibration:",
    ]
    for row in s["calibration"]:
        flag = " MISCALIBRATED" if row["miscalibrated"] else ""
        lines.append(
            f"  {row['tier']}: n={row['n']} accuracy={row['accuracy']} "
            f"bar={row['accuracy_bar']} gap={row['gap']}{flag}"
        )
    lines.append(f"Audit chain valid: {s['audit_ok']} ({s['audit_entries']} entries)")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_summary(run_scenario()))
