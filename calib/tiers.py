"""Decision-type registry with explicit accuracy bars.

Every tier pairs an accuracy bar with a decision mode, and every routing
decision cites the policy rule ID it was made under. The point of the
registry is to make the accuracy contract *explicit*: instead of one
implicit bar for every decision, each decision type declares how accurate
the decider must be before it is allowed to act.

This is different from risk-based escalation tiers (T1-T4), which key off
how dangerous an *action* is. Calibration tiers key off how accurate a
*decision* must be. The two compose: a FAST_PATH decision can still be
T3-escalated if the resulting action is irreversible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    """One accuracy tier in the registry."""

    name: str
    rule_id: str
    min_amount: float  # inclusive lower bound of the claim-amount band
    max_amount: float  # inclusive upper bound; float("inf") for open top
    accuracy_bar: float  # model confidence must clear this to decide
    mode: str  # auto_decide | decide_with_spot_check | human_decides
    description: str


FAST_PATH = Tier(
    name="FAST_PATH",
    rule_id="ACC-FAST-01",
    min_amount=0.0,
    max_amount=499.99,
    accuracy_bar=0.90,
    mode="auto_decide",
    description=(
        "Low-value claims are auto-decided when model confidence clears 90%. "
        "Speed is the point: small mistakes are cheap and every decision is appealable."
    ),
)

STANDARD = Tier(
    name="STANDARD",
    rule_id="ACC-STD-01",
    min_amount=500.0,
    max_amount=10000.0,
    accuracy_bar=0.95,
    mode="decide_with_spot_check",
    description=(
        "Mid-value claims are decided by the agent when confidence clears 95%; "
        "humans spot-check a sample after the fact."
    ),
)

HIGH_STAKES = Tier(
    name="HIGH_STAKES",
    rule_id="ACC-HIGH-01",
    min_amount=10000.01,
    max_amount=float("inf"),
    accuracy_bar=0.99,
    mode="human_decides",
    description=(
        "High-value claims are decided by a human, not the model. The 99% bar "
        "applies to the human-plus-model system and is checked by calibration."
    ),
)

# Fraud flags bypass the amount bands entirely.
FRAUD_RULE_ID = "ACC-HIGH-02"

TIERS = (FAST_PATH, STANDARD, HIGH_STAKES)


def tier_for_amount(amount: float, fraud_flag: bool) -> tuple[Tier, bool]:
    """Return ``(tier, via_fraud_rule)`` for a claim.

    Fraud-flagged claims always route to HIGH_STAKES regardless of amount.
    Raises :class:`ValueError` for negative amounts.
    """
    if amount < 0:
        raise ValueError(f"claim amount must be >= 0, got {amount}")
    if fraud_flag:
        return HIGH_STAKES, True
    for tier in TIERS:
        if tier.min_amount <= amount <= tier.max_amount:
            return tier, False
    raise ValueError(f"no tier covers amount {amount}")  # unreachable by construction
