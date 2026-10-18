# Threat model (STRIDE-lite)

| Threat | Mitigation in this repo |
|---|---|
| **Spoofing** — fake confidence scores | Engine validates range but trusts the caller; calibration table is the detective control. Documented limitation. |
| **Tampering** — altering a recorded decision | Hash-chained audit log; `verify()` detects any edit. |
| **Repudiation** — "I never approved that" | Every decision records `decided_by`; human decisions record the named reviewer. |
| **Information disclosure** | Synthetic data only; no PII in seed. Appeal reasons are free text — scrub before production use. |
| **Denial of service** | Sub-bar confidence escalates instead of retrying in a loop; one retry-free design. |
| **Elevation of privilege** — model self-approving high-stakes | HIGH_STAKES is human-only by construction; `human_decide` rejects non-pending records. |

## Key residual risks

1. **Confidence gaming:** a model that inflates confidence bypasses every bar.
   Mitigation is organizational (calibrate the model, monitor the reliability
   table), not in this code.
2. **Appeal flooding:** no rate limit on appeals in this demo; production
   needs per-claimant throttling.
3. **Single reviewer:** HIGH_STAKES needs one human; collusion/fatigue is out
   of scope (quorum is Planned).
