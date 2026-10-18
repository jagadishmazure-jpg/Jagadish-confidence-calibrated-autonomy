"""Print what this repo adds over plain escalation tiers: a per-tier accuracy
bar, the confidence each tier claimed versus the accuracy it achieved, and
an explicit OVERCONFIDENT flag when the stated confidence runs ahead."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calib.demo_helpers import run_scenario  # noqa: E402
from calib.tiers import TIERS  # noqa: E402

for t in TIERS:
    print(f"{t.name:<12} bar={t.accuracy_bar}")
s = run_scenario()
print(f"claims={s['claims']} decided={s['decided']} human={s['human_decided']} escalated={s['escalated']}")
for row in s["calibration"]:
    flags = [f for f, on in (("MISCALIBRATED", row["miscalibrated"]),
                             ("OVERCONFIDENT", row["overconfident"])) if on]
    print(f"{row['tier']:<12} confidence={row['mean_confidence']} accuracy={row['accuracy']} "
          f"{' '.join(flags) or 'ok'}")
