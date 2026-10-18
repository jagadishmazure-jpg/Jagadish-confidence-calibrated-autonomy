"""Print the real test total (CI docs check consumes this)."""

import subprocess
import sys

out = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-q"],
    capture_output=True,
    text=True,
    cwd=__file__.rsplit("/", 2)[0],
)
print(out.stdout.strip().splitlines()[-1])
