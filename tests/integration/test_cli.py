import pytest
import subprocess
import os
import sys

@pytest.mark.integration
def test_cli_dry_run():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    # Assume data needs to be mocked
    # We will just see if the help runs
    res = subprocess.run([sys.executable, "-m", "ra_causal.cli.run_pipeline", "--help"], cwd=root, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Run the ra_causal preprocessing pipeline" in res.stdout

