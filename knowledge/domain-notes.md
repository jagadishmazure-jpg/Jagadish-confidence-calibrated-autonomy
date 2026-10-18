# Domain notes: confidence-calibrated autonomy

My own framing of a common design question for decision agents: **not every
decision needs the same accuracy bar.** A low-value claim can be decided
quickly at a lower bar, because a wrong payout is small, adjustable and
appealable. A high-value or irreversible decision needs a much higher bar
and a human in the loop. The repo makes that trade-off explicit, per
decision type, instead of leaving one implicit bar for everything.

## The pattern

1. **Declare the bar per decision type, not per system.** A single global
   accuracy threshold is either too slow (everything waits for 99%) or too
   reckless (everything ships at 90%). Tier the decisions: fast path, standard,
   high stakes — each with its own bar, decision mode, and policy citation.
2. **Route on confidence, never guess.** The engine compares the decider's
   stated confidence against the tier's bar. Cleared → act. Not cleared →
   escalate. There is no third option; "probably fine" is not a routing outcome.
3. **Make every decision appealable.** The appeal is the safety valve that
   makes lower bars acceptable: one extra evidence round, a re-decision, and
   a recorded outcome. Appeal rates per tier are a leading indicator that a
   bar is set wrong.
4. **Calibrate the bars against reality.** Stated confidence drifts. A
   reliability table (actual accuracy vs bar, per tier) turns "we think we're
   95% accurate" into a checkable claim. Flagged tiers get their bar or their
   model changed — tiers are not set-and-forget.

## Why it differs from risk escalation

Escalation tiers (T1–T4) answer "how bad is it if this action is wrong?"
Calibration tiers answer "how sure must we be before acting, and what
recourse exists?" A reversible low-value action can be FAST_PATH even at
T1; an irreversible high-value action is HIGH_STAKES regardless of tier.
The two systems compose rather than compete.

## Anti-patterns

- **Silent sub-bar decisions.** The most common failure: the system acts
  anyway when confidence is low, because no escalation path was wired.
- **Unappealable automation.** A 90% bar without appeals is just a 10% error
  rate with no recourse.
- **Uncalibrated bars.** Bars chosen once and never checked against outcomes
  become fiction within months.
