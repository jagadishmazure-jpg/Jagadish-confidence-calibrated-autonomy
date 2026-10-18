# Jagadish-confidence-calibrated-autonomy

**Accuracy-tiered decision autonomy with appeal paths — not every decision needs 100% accuracy.**

> **Disclaimer.** Independent portfolio project; not affiliated with any real
> company. "Tornholt Mutual" is fictional. All claims, people, amounts, and
> outcomes are synthetic demo data. Nothing here is insurance or legal advice.

## Recruiter summary

Most agent systems use one implicit accuracy bar for every decision. This repo
makes the bar explicit: each decision type declares how accurate the decider
must be (90% / 95% / 99%), the engine routes only when confidence clears the
bar, never guesses when it doesn't, and every decision is appealable with a
fresh evidence round. A calibration check keeps the bars honest by comparing
stated confidence against actual accuracy per tier. Demo run: 24 claims →
14 auto/spot-check decided, 4 human-decided, 6 escalated, 2 appeals;
calibration flagged FAST_PATH as below its bar (0.825 actual vs 0.90) and
overconfident (it claimed 0.935).

## How it works

1. **Tier registry** (`calib/tiers.py`) — three tiers with cited policy rule IDs:
   `FAST_PATH` (below $500, 0.90 bar, auto-decide), `STANDARD` ($500 to
   $10,000 inclusive, 0.95 bar, agent decides + human spot-checks),
   `HIGH_STAKES` (above $10,000 or fraud flag, 0.99 bar, human decides). The
   bands are half-open, so every amount lands in exactly one tier.
2. **Decide** (`calib/decide.py`) — looks up the claim, routes by amount/fraud
   flag, checks confidence against the bar. Cleared → recorded; not cleared →
   recorded as escalated and `Escalated` raised (the caller cannot ignore it).
   A claim gets one decision record; an escalated or pending claim is closed
   by `human_decide`, which keeps the model's proposal next to the human's
   final decision.
3. **Appeal** (`calib/appeals.py`) — any final decision can be appealed once;
   one supplemental evidence document is gathered, the claim is re-decided
   from **all** its evidence (net supporting vs contradicting), and the
   outcome is `overturned` only if that differs from the final decision.
   Per-tier appeal rates exposed.
4. **Calibrate** (`calib/calibration.py`) — reliability table per tier from
   historical outcomes: mean stated confidence vs actual accuracy. Tiers
   below their bar are flagged `MISCALIBRATED`; tiers whose confidence runs
   more than 0.05 ahead of their accuracy are flagged `OVERCONFIDENT`.
5. **Audit** (`calib/audit.py`) — hash-chained log of every decision, human
   decision, escalation, and appeal.

Real run, rendered from a fresh run in CI (`python -m calib.demo_helpers`):

<!-- run: python -m calib.demo_helpers -->
```text
Claims processed: 24
Auto/spot-check decided: 14, human-decided: 4, escalated (no tier cleared): 6
Decisions per tier: FAST_PATH=9, STANDARD=5, HIGH_STAKES=4
Appeals filed: 2; appeal rates: {'FAST_PATH': 0.222, 'STANDARD': 0.0, 'HIGH_STAKES': 0.0}
Calibration:
  FAST_PATH: n=40 confidence=0.935 accuracy=0.825 bar=0.9 gap=-0.075 MISCALIBRATED OVERCONFIDENT
  STANDARD: n=40 confidence=0.97 accuracy=0.95 bar=0.95 gap=0.0
  HIGH_STAKES: n=40 confidence=0.996 accuracy=1.0 bar=0.99 gap=0.01
Audit chain valid: True (30 entries)
```
<!-- /run -->

## How this differs from escalation tiers

Risk-based escalation tiers (T1–T4, used across this portfolio) key off how
**dangerous an action is** — blast radius, irreversibility. Calibration tiers
key off how **accurate a decision must be** — the bar, the confidence check,
and the recourse when wrong. They compose: a FAST_PATH decision can still be
T3-escalated if the resulting action is irreversible. One answers "how risky
is this?", the other "are we accurate enough to act, and what if we're not?"

`Jagadish-insurance-claims-agents` handles the claims workflow itself
(extraction, fraud signals, settlement); it lists calibration only as future
work. This repo is the policy layer that question needs: per-decision
accuracy bars, a confidence-vs-accuracy check, and recourse.

<!-- run: python scripts/show_differentiator.py -->
```text
FAST_PATH    bar=0.9
STANDARD     bar=0.95
HIGH_STAKES  bar=0.99
claims=24 decided=14 human=4 escalated=6
FAST_PATH    confidence=0.935 accuracy=0.825 MISCALIBRATED OVERCONFIDENT
STANDARD     confidence=0.97 accuracy=0.95 ok
HIGH_STAKES  confidence=0.996 accuracy=1.0 ok
```
<!-- /run -->

## Run it

```bash
python3 -m pytest tests/ -q        # stdlib only
python3 -m calib.demo_helpers      # end-to-end scenario summary
python3 scripts/count_tests.py     # prints the real test total
# Streamlit demo (optional):
pip install streamlit && streamlit run demo/app.py
```

<!-- run: python scripts/count_tests.py -->
```text
54 tests collected
```
<!-- /run -->

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
- The supplemental appeal document's stance is deterministic from IDs (a
  demo stand-in for a real evidence-gathering round); the re-decision then
  weighs it with the claim's existing evidence.
- In the demo, the 6 escalated claims are left open to show the queue; tests
  cover closing them with `human_decide`.
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

## Standardization review (2026-10-18)

Bugs found in review and fixed, each with a regression test in
`tests/test_calib.py` (section "review fixes"):

| ID | Bug | Fix |
|---|---|---|
| ACC-BAND-01 | Amounts such as 499.995 and 10,000.005 fell between tiers and were rejected | Half-open bands, no gaps |
| DEC-ONCE-01 | A claim could be decided twice, producing two records | Second decision refused |
| DEC-HUMAN-01 | Escalated claims had no way to be closed; `human_decide` overwrote the model's proposal | Escalated and pending claims closed by a human; proposal and final decision both kept |
| APPEAL-REDECIDE-01 | The appeal outcome was a hash of the IDs and ignored the evidence | Re-decided from all evidence, compared with the final decision |
| CAL-CONF-01 | The README promised a stated-confidence vs accuracy check that the code did not do | Mean confidence, gap and `OVERCONFIDENT` flag |

Wording: the domain notes are my own framing, with no attribution to
outside material. The "fictional" insurer name turned out to belong to a real insurer and
was replaced with an invented one (now Tornholt Mutual).

## Knowledge base

- [`knowledge/domain-notes.md`](knowledge/domain-notes.md) — accuracy-tiered autonomy, in my own words
- [`knowledge/architecture.md`](knowledge/architecture.md) — Mermaid architecture

## Related repos

- `Jagadish-insurance-claims-agents` — post-loss claims handling (cousin: this
  repo is about *decision accuracy policy*, that one about *claims workflow*).
- `Jagadish-agent-feedback-loop` — captures the feedback this repo's appeal
  rates would feed.
- `Jagadish-llm-evals-observability` — judge/eval patterns behind calibration.
