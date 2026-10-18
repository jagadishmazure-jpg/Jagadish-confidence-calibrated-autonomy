"""Decision engine: route a claim to the tier its confidence clears.

The engine never guesses. If the model's confidence does not clear the
accuracy bar of the tier the claim belongs to, the claim is recorded as
escalated and :class:`Escalated` is raised so the caller is forced to
handle it. HIGH_STAKES claims are never auto-decided: they are recorded
as ``pending_human`` until a person completes them via :func:`human_decide`,
which also resolves escalated claims. A claim is decided at most once.
"""

from __future__ import annotations

import datetime as _dt
import sqlite3

from .tiers import FRAUD_RULE_ID, tier_for_amount


class Escalated(Exception):
    """Raised when no tier's accuracy bar is cleared. Carries the decision id."""

    def __init__(self, decision_id: str):
        super().__init__(f"no tier cleared; escalated as {decision_id}")
        self.decision_id = decision_id


class DecisionError(Exception):
    """Raised for invalid inputs (unknown claim, bad confidence, bad state)."""


def _next_id(con: sqlite3.Connection) -> str:
    n = con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] + 1
    return f"D-{n:04d}"


def _evidence_ids(con: sqlite3.Connection, claim_id: str) -> list[str]:
    rows = con.execute(
        "SELECT evidence_id FROM evidence WHERE claim_id = ? ORDER BY evidence_id",
        (claim_id,),
    ).fetchall()
    return [r[0] for r in rows]


def decide(
    con: sqlite3.Connection,
    claim_id: str,
    proposed: str,
    confidence: float,
    decided_by: str = "model",
) -> dict:
    """Route and record a decision. Returns the decision record as a dict.

    * ``proposed`` must be ``"approve"`` or ``"deny"``.
    * ``confidence`` must be in ``[0, 1]``.
    * If confidence clears the tier's bar the decision is recorded with
      ``outcome="decided"`` (FAST_PATH/STANDARD) or ``"pending_human"``
      (HIGH_STAKES).
    * Otherwise the escalation is recorded and :class:`Escalated` is raised.
    """
    if proposed not in ("approve", "deny"):
        raise DecisionError(f"proposed must be approve/deny, got {proposed!r}")
    if not (0.0 <= confidence <= 1.0):
        raise DecisionError(f"confidence must be in [0,1], got {confidence}")
    claim = con.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
    if claim is None:
        raise DecisionError(f"unknown claim {claim_id}")
    prior = con.execute(
        "SELECT decision_id, outcome FROM decisions WHERE claim_id = ? ORDER BY decision_id",
        (claim_id,),
    ).fetchone()
    if prior is not None:
        # One decision per claim (DEC-ONCE-01): a second call must not create a
        # second payout. Escalated claims go to a human via human_decide().
        raise DecisionError(
            f"claim {claim_id} already has decision {prior['decision_id']} ({prior['outcome']})"
        )

    tier, via_fraud = tier_for_amount(claim["amount"], bool(claim["fraud_flag"]))
    rule_id = FRAUD_RULE_ID if via_fraud else tier.rule_id
    decision_id = _next_id(con)
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    evidence_cited = ",".join(_evidence_ids(con, claim_id))

    if confidence < tier.accuracy_bar:
        con.execute(
            "INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (decision_id, claim_id, tier.name, rule_id, confidence, proposed,
             "escalated", evidence_cited, decided_by, ts, None),
        )
        con.commit()
        raise Escalated(decision_id)

    outcome = "pending_human" if tier.mode == "human_decides" else "decided"
    con.execute(
        "INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (decision_id, claim_id, tier.name, rule_id, confidence, proposed,
         outcome, evidence_cited, decided_by, ts,
         proposed if outcome == "decided" else None),
    )
    con.commit()
    return get_decision(con, decision_id)


def human_decide(
    con: sqlite3.Connection, decision_id: str, human_decision: str, reviewer: str
) -> dict:
    """Complete a ``pending_human`` or ``escalated`` decision.

    The model's ``proposed`` value is kept; the human's call is stored in
    ``final_decision`` so the audit shows whether the human agreed (DEC-HUMAN-01).
    """
    if human_decision not in ("approve", "deny"):
        raise DecisionError(f"human_decision must be approve/deny, got {human_decision!r}")
    rec = get_decision(con, decision_id)
    if rec is None:
        raise DecisionError(f"unknown decision {decision_id}")
    if rec["outcome"] not in ("pending_human", "escalated"):
        raise DecisionError(
            f"decision {decision_id} is {rec['outcome']}, not pending_human or escalated")
    con.execute(
        "UPDATE decisions SET outcome = ?, final_decision = ?, decided_by = ? WHERE decision_id = ?",
        ("decided", human_decision, f"human:{reviewer}", decision_id),
    )
    con.commit()
    return get_decision(con, decision_id)


def get_decision(con: sqlite3.Connection, decision_id: str) -> dict | None:
    row = con.execute(
        "SELECT * FROM decisions WHERE decision_id = ?", (decision_id,)
    ).fetchone()
    return dict(row) if row else None
