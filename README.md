# Jagadish-confidence-calibrated-autonomy

**Accuracy-tiered decision autonomy with appeal paths — not every decision needs 100% accuracy.**

> **Disclaimer.** Independent portfolio project; not affiliated with any real
> company. "Meridian Mutual" is fictional. All claims, people, amounts, and
> outcomes are synthetic demo data. Nothing here is insurance or legal advice.

## Recruiter summary

Most agent systems use one implicit accuracy bar for every decision. This repo
makes the bar explicit: each decision type declares how accurate the decider
must be (90% / 95% / 99%), the engine routes only when confidence clears the
bar, never guesses when it doesn't, and every decision is appealable with a
fresh evidence round. A calibration check keeps the bars honest by comparing
stated confidence against actual accuracy per tier. Demo run: 24 claims →
14 auto/spot-check decided, 4 human-decided, 6 escalated, 2 appeals;
calibration flagged FAST_PATH as miscalibrated (0.825 actual vs 0.90 bar).

## How it works

1. **Tier registry** (`calib/tiers.py`) — three tiers with cited policy rule IDs:
   `FAST_PATH` (<$500, 0.90 bar, auto-decide), `STANDARD` ($500–$10k, 0.95 bar,
   agent decides + human spot-checks), `HIGH_STAKES` (>$10k or fraud flag,
   0.99 bar, human decides).
2. **Decide** (`calib/decide.py`) — looks up the claim, routes by amount/fraud
   flag, checks confidence against the bar. Cleared → recorded; not cleared →
   recorded as escalated and `Escalated` raised (the caller cannot ignore it).
3. **Appeal** (`calib/appeals.py`) — any final decision can be appealed once;
   one supplemental evidence document is gathered, the claim is re-decided,
   outcome recorded as `upheld`/`overturned`. Per-tier appeal rates exposed.
4. **Calibrate** (`calib/calibration.py`) — reliability table per tier from
   historical outcomes; tiers below their bar are flagged.
5. **Audit** (`calib/audit.py`) — hash-chained log of every decision, human
   decision, escalation, and appeal.

Real run excerpt (`python -m calib.demo_helpers`):

```
Claims processed: 24
Auto/spot-check decided: 14, human-decided: 4, escalated (no tier cleared): 6
Decisions per tier: FAST_PATH=9, STANDARD=5, HIGH_STAKES=4
Appeals filed: 2; appeal rates: {'FAST_PATH': 0.222, 'STANDARD': 0.0, 'HIGH_STAKES': 0.0}
Calibration:
  FAST_PATH: n=40 accuracy=0.825 bar=0.9 gap=-0.075 MISCALIBRATED
  STANDARD: n=40 accuracy=0.95 bar=0.95 gap=0.0
  HIGH_STAKES: n=40 accuracy=1.0 bar=0.99 gap=0.01
Audit chain valid: True (30 entries)
```

## How this differs from escalation tiers

Risk-based escalation tiers (T1–T4, used across this portfolio) key off how
**dangerous an action is** — blast radius, irreversibility. Calibration tiers
key off how **accurate a decision must be** — the bar, the confidence check,
and the recourse when wrong. They compose: a FAST_PATH decision can still be
T3-escalated if the resulting action is irreversible. One answers "how risky
is this?", the other "are we accurate enough to act, and what if we're not?"

## Run it

```bash
python3 -m pytest tests/ -q        # 41 tests, stdlib only
python3 -m calib.demo_helpers      # end-to-end scenario summary
python3 scripts/count_tests.py     # prints the real test total
# Streamlit demo (optional):
pip install streamlit && streamlit run demo/app.py
```

## Guardrails and security

- The engine never emits a decision it is not confident enough to make:
  sub-bar confidence is recorded as an escalation, not a guess.
- HIGH_STAKES is human-only by construction (`pending_human` until a named
  reviewer completes it); fraud flags bypass amount bands via `ACC-HIGH-02`.
- Every routing decision cites its policy rule ID; the audit chain is
  tamper-evident (`AuditLog.verify()`).
- Synthetic data only; no PII (claimant names are invented).

## Limitations and known failures

- Confidence is supplied by the caller; the engine trusts but calibrates it.
  Garbage confidence in → garbage routing out (the calibration table is the
  backstop, not a filter).
- Appeal evidence stance is deterministic from IDs (a demo stand-in for a
  real evidence-gathering round).
- The 0.90/0.95/0.99 bars are illustrative policy choices, not actuarial ones.
- Small synthetic history (40 decisions/tier): the reliability table
  demonstrates the mechanism; it is a regression check, not a quality claim.

## Built / Written-not-run / Planned

| Item | Status |
|---|---|
| Tier registry with cited rule IDs | Built |
| Decision engine (route / escalate / human-complete) | Built |
| Appeal path with evidence round + per-tier rates | Built |
| Calibration reliability table + miscalibration flags | Built |
| Hash-chained audit log | Built |
| Streamlit demo (thin, lazy import) | Written, not run here |
| Live LLM confidence source | Planned |
| Multi-reviewer quorum for HIGH_STAKES | Planned |

## Knowledge base

- [`knowledge/domain-notes.md`](knowledge/domain-notes.md) — accuracy-tiered autonomy, distilled
- [`knowledge/architecture.md`](knowledge/architecture.md) — Mermaid architecture

## Related repos

- `Jagadish-insurance-claims-agents` — post-loss claims handling (cousin: this
  repo is about *decision accuracy policy*, that one about *claims workflow*).
- `Jagadish-agent-feedback-loop` — captures the feedback this repo's appeal
  rates would feed.
- `Jagadish-llm-evals-observability` — judge/eval patterns behind calibration.
