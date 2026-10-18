"""Calibration check: does stated confidence match reality?

A reliability table is built per tier from the ``history`` table (past
decisions with known outcomes). If a tier's actual accuracy falls below its
accuracy bar, the tier is flagged as miscalibrated — the bar is a fiction
and either the bar or the model needs to change.

This is the feedback loop that keeps the accuracy contract honest: tiers
are not set-and-forget.
"""

from __future__ import annotations

import sqlite3

from .tiers import TIERS


def reliability_table(con: sqlite3.Connection) -> list[dict]:
    """One row per tier: n, mean stated confidence, actual accuracy, the
    tier's bar, the gap, and whether the tier is miscalibrated."""
    rows = []
    for tier in TIERS:
        recs = con.execute(
            "SELECT confidence, correct FROM history WHERE tier = ?", (tier.name,)
        ).fetchall()
        n = len(recs)
        mean_conf = sum(r[0] for r in recs) / n if n else 0.0
        accuracy = sum(r[1] for r in recs) / n if n else 0.0
        gap = accuracy - tier.accuracy_bar
        rows.append(
            {
                "tier": tier.name,
                "rule_id": tier.rule_id,
                "n": n,
                "mean_confidence": round(mean_conf, 3),
                "accuracy": round(accuracy, 3),
                "accuracy_bar": tier.accuracy_bar,
                "gap": round(gap, 3),
                "miscalibrated": bool(n and accuracy < tier.accuracy_bar),
            }
        )
    return rows


def miscalibrated_tiers(con: sqlite3.Connection) -> list[str]:
    """Names of tiers whose actual accuracy is below their bar."""
    return [r["tier"] for r in reliability_table(con) if r["miscalibrated"]]
