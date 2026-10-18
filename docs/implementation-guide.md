# Implementation guide

## For adopters: wiring accuracy tiers into your own decision system

1. **Inventory your decision types.** List every decision the agent makes and
   sort by cost-of-error, not by frequency. The natural bands (here <$500 /
   $500–$10k / >$10k) fall out of your own loss data.
2. **Set bars from loss math, not vibes.** Bar ≈ 1 − (acceptable loss per
   decision / cost per decision). A $200 claim decided in 2 seconds can
   tolerate 90%; a $50k claim cannot.
3. **Make escalation the default, not the exception.** `decide()` raises
   `Escalated` when no bar clears — design the caller so the exception path
   is the well-tested one.
4. **Appeals are a product feature, not an afterthought.** One extra evidence
   round, a recorded upheld/overturned outcome, and per-tier appeal rates.
   If a tier's appeal rate climbs, its bar is wrong.
5. **Recalibrate on a schedule.** Run `reliability_table()` against recent
   decisions with known outcomes (monthly is a sane default). Flagged tiers
   get a bar change or a model change — document which in an ADR.

## Extending this repo

- Add a tier: one `Tier(...)` entry in `calib/tiers.py` plus seed history in
  `calib/telemetry.py`; the engine, appeals, and calibration pick it up.
- Plug a real model: replace the `confidence` argument to `decide()` with
  your model's calibrated score (see `Jagadish-llm-evals-observability` for
  calibration patterns like Wilson intervals).
- Multi-reviewer quorum: extend `human_decide` to require N reviewers for
  amounts above a second threshold.
