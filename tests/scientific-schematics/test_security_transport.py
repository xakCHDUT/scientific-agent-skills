"""Exercise all shipped schematic transports in separate, offline processes."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PROBE = Path(__file__).resolve().parent / "fixtures" / "transport_probe.py"


@pytest.mark.parametrize("skill", [
    "scientific-schematics", "scientific-slides", "literature-review", "latex-posters",
])
def test_each_shipped_schematic_copy_refuses_redirects_and_preserves_success(skill):
    # These helpers are intentionally copied between skills. Separate children
    # preserve the repository's one-skill-per-interpreter contract and exercise
    # each shipped file rather than trusting a mock's call arguments.
    script = REPO_ROOT / "skills" / skill / "scripts" / "generate_schematic_ai.py"
    environment = {
        name: value for name, value in os.environ.items()
        if name in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG"}
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(PROBE), str(script)],
        env=environment, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {
        "redirect_cases": 600, "success_cases": 2, "redaction_cases": 4,
    }
