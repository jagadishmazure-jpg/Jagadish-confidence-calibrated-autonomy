# Interview points

- **The one-liner:** "Not every decision needs 100% accuracy — so I built a
  system where each decision type declares its accuracy bar, the engine only
  acts when confidence clears it, and every decision is appealable."
- **Why tiers, not one threshold:** a single bar is either too slow or too
  reckless. Tiering by cost-of-error lets low-stakes decisions fly at 90%
  while high-stakes ones wait for a human at 99%.
- **Never guess:** sub-bar confidence doesn't produce a hesitant decision —
  it produces a recorded escalation and an exception the caller must handle.
- **Appeals make lower bars safe:** the 90% fast path is acceptable *because*
  any decision can be re-examined with fresh evidence; appeal rates per tier
  tell you when a bar is mis-set.
- **Calibration closes the loop:** stated confidence drifts; the reliability
  table checks actual accuracy against each bar. In the demo, FAST_PATH is
  flagged (0.825 actual vs 0.90 bar) — the system tells you its own bar is
  fiction.
- **Vs escalation tiers:** T1–T4 key off action risk; calibration tiers key
  off decision accuracy. They compose — a fast-path decision can still be
  T3-escalated if the action is irreversible.
- **Fraud bypass:** fraud flags skip amount bands entirely (`ACC-HIGH-02`) —
  some signals always mean human review, regardless of value.
