"""Appeal path: every decided claim can be challenged.

An appeal triggers exactly one extra evidence-gathering round (a supplemental
review document is attached to the claim), then the claim is re-decided from
the augmented evidence: the net stance of every document on the claim. The appeal outcome — ``upheld`` or ``overturned`` —
is recorded next to the original decision, and per-tier appeal rates show
where the accuracy bars are set wrong.

Only final (``outcome="decided"``) decisions can be appealed, and each
decision can be appealed at most once. Pending-human and escalated records
have their own paths (a human, or the escalation queue) and do not go
through appeals.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import sqlite3

from .decide import get_decision


class AppealError(Exception):
    """Raised when an appeal is not allowed."""


def _appeal_stance(claim_id: str, decision_id: str) -> int:
    """Deterministic stance of the supplemental evidence: +1 supports the
    claimant (leans approve), -1 leans deny. Derived from ids so appeals are
    reproducible without randomness."""
    digest = hashlib.md5(f"{claim_id}:{decision_id}".encode()).hexdigest()
    return 1 if int(digest, 16) % 2 == 0 else -1


def appeal(
    con: sqlite3.Connection, decision_id: str, appellant: str, reason: str
) -> dict:
    """File an appeal against a decided claim. Returns the appeal record.

    The extra evidence round attaches one supplemental document; if its
    stance disagrees with the original decision the appeal overturns it,
    otherwise the decision is upheld.
    """
    rec = get_decision(con, decision_id)
    if rec is None:
        raise AppealError(f"unknown decision {decision_id}")
    if rec["outcome"] != "decided":
        raise AppealError(
            f"only final decisions can be appealed; {decision_id} is {rec['outcome']}"
        )
    existing = con.execute(
        "SELECT appeal_id FROM appeals WHERE decision_id = ?", (decision_id,)
    ).fetchone()
    if existing:
        raise AppealError(f"decision {decision_id} already appealed as {existing[0]}")

    n = con.execute("SELECT COUNT(*) FROM appeals").fetchone()[0] + 1
    appeal_id = f"A-{n:04d}"
    new_eid = f"{rec['claim_id']}-{appeal_id}"
    stance = _appeal_stance(rec["claim_id"], decision_id)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO evidence VALUES (?,?,?,?,?)",
        (new_eid, rec["claim_id"], "supplemental review",
         f"appeal evidence for {decision_id} filed by {appellant}", stance),
    )
    # Re-decide from ALL the evidence, now including the supplemental document
    # (APPEAL-REDECIDE-01). The old rule looked only at the new document's
    # stance, so an appeal was a coin flip that ignored the claim file.
    net = sum(r[0] for r in cur.execute(
        "SELECT supports FROM evidence WHERE claim_id = ?", (rec["claim_id"],)))
    redecided = "approve" if net >= 0 else "deny"
    outcome = "overturned" if redecided != rec["final_decision"] else "upheld"
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    cur.execute(
        "INSERT INTO appeals VALUES (?,?,?,?,?,?,?)",
        (appeal_id, decision_id, appellant, reason, new_eid, outcome, ts),
    )
    con.commit()
    row = con.execute("SELECT * FROM appeals WHERE appeal_id = ?", (appeal_id,)).fetchone()
    return dict(row)


def appeal_rate(con: sqlite3.Connection, tier_name: str) -> dict:
    """Appeal statistics for one tier: decisions, appeals, rate."""
    n_dec = con.execute(
        "SELECT COUNT(*) FROM decisions WHERE tier = ? AND outcome = 'decided'",
        (tier_name,),
    ).fetchone()[0]
    n_app = con.execute(
        """SELECT COUNT(*) FROM appeals a
           JOIN decisions d ON d.decision_id = a.decision_id
           WHERE d.tier = ?""",
        (tier_name,),
    ).fetchone()[0]
    return {
        "tier": tier_name,
        "decisions": n_dec,
        "appeals": n_app,
        "appeal_rate": (n_app / n_dec) if n_dec else 0.0,
    }
