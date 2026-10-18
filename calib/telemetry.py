"""Synthetic telemetry for Tornholt Mutual (fictional insurer).

SQLite database with three tables:

* ``claims`` — one row per claim (amount, fraud flag, status).
* ``evidence`` — supporting/refuting documents attached to claims.
* ``history`` — past decisions with known outcomes, used to check whether
  the engine's stated confidence matches reality (see ``calibration``).

Everything is seeded deterministically (seed 42) so runs are reproducible.
"""

from __future__ import annotations

import random
import sqlite3

SEED = 42

SCHEMA = """
CREATE TABLE claims (
    claim_id   TEXT PRIMARY KEY,
    claimant   TEXT NOT NULL,
    amount     REAL NOT NULL,
    fraud_flag INTEGER NOT NULL,
    status     TEXT NOT NULL
);
CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    claim_id    TEXT NOT NULL,
    kind        TEXT NOT NULL,
    summary     TEXT NOT NULL,
    supports    INTEGER NOT NULL
);
CREATE TABLE history (
    hist_id    TEXT PRIMARY KEY,
    claim_id   TEXT NOT NULL,
    tier       TEXT NOT NULL,
    confidence REAL NOT NULL,
    decided    TEXT NOT NULL,
    correct    INTEGER NOT NULL
);
CREATE TABLE decisions (
    decision_id TEXT PRIMARY KEY,
    claim_id    TEXT NOT NULL,
    tier        TEXT NOT NULL,
    rule_id     TEXT NOT NULL,
    confidence  REAL NOT NULL,
    proposed    TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    evidence_cited TEXT NOT NULL,
    decided_by  TEXT NOT NULL,
    ts          TEXT NOT NULL,
    final_decision TEXT
);
CREATE TABLE appeals (
    appeal_id   TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    appellant   TEXT NOT NULL,
    reason      TEXT NOT NULL,
    new_evidence_id TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    ts          TEXT NOT NULL
);
"""

_FIRST = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Eli", "Ivy", "Owen"]
_LAST = ["Carter", "Nguyen", "Patel", "Garcia", "Kim", "Rossi", "Haddad", "Okafor"]
_KINDS = ["repair estimate", "photo set", "police report", "medical bill", "witness note"]


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    return con


def seed(con: sqlite3.Connection) -> sqlite3.Connection:
    """Create schema and load deterministic synthetic data."""
    rng = random.Random(SEED)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    # 24 claims spread across the three amount bands; 2 fraud-flagged.
    bands = [(50, 450, 10), (600, 9500, 10), (11000, 60000, 4)]
    cid = 0
    for lo, hi, n in bands:
        for _ in range(n):
            cid += 1
            claim_id = f"CLM-{cid:04d}"
            amount = round(rng.uniform(lo, hi), 2)
            fraud = 1 if (cid in (7, 19)) else 0
            claimant = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
            cur.execute(
                "INSERT INTO claims VALUES (?,?,?,?,?)",
                (claim_id, claimant, amount, fraud, "open"),
            )
            # 2-4 evidence documents per claim.
            for e in range(rng.randint(2, 4)):
                eid = f"{claim_id}-E{e + 1}"
                kind = rng.choice(_KINDS)
                supports = rng.choice([1, 1, 1, -1, 0])
                cur.execute(
                    "INSERT INTO evidence VALUES (?,?,?,?,?)",
                    (eid, claim_id, kind, f"{kind} for {claim_id}", supports),
                )

    # Historical decisions for calibration: true accuracy per tier is baked
    # in so the reliability table has something meaningful to report.
    # FAST_PATH is deliberately slightly miscalibrated (0.88 true vs 0.90 bar).
    true_acc = {"FAST_PATH": 0.88, "STANDARD": 0.96, "HIGH_STAKES": 0.995}
    conf_range = {"FAST_PATH": (0.90, 0.97), "STANDARD": (0.95, 0.99), "HIGH_STAKES": (0.99, 1.0)}
    hid = 0
    for tier, acc in true_acc.items():
        lo, hi = conf_range[tier]
        for _ in range(40):
            hid += 1
            conf = round(rng.uniform(lo, hi), 3)
            correct = 1 if rng.random() < acc else 0
            decided = rng.choice(["approve", "deny"])
            cur.execute(
                "INSERT INTO history VALUES (?,?,?,?,?,?)",
                (f"HIST-{hid:04d}", f"CLM-{rng.randint(1, 24):04d}", tier, conf, decided, correct),
            )
    con.commit()
    return con


def seed_db() -> sqlite3.Connection:
    return seed(connect())
