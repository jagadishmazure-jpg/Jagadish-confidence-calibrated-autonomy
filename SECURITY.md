# Security policy

This is a synthetic-data demo repo. Do not point it at real claims, real
claimant data, or production models.

## Reporting a vulnerability

Open a private vulnerability report via the repo's Security tab. Do not
file public issues for security bugs.

## Scope notes

- Confidence scores are caller-supplied; a model that inflates confidence
  defeats the tier bars. Calibrate models separately (see
  `Jagadish-llm-evals-observability`).
- Appeal `reason` is free text: scrub PII before storing in production.
- The audit chain detects tampering; it does not prevent it. Back up the
  log.
