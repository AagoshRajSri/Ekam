"""
End-to-end smoke tests for the bake-off harness.
Zero external API calls: executes offline with fake providers.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BAKEOFF_SCRIPT = REPO_ROOT / "evals" / "bakeoff" / "run_bakeoff.py"


def test_dry_run_exits_cleanly():
    cmd = [
        sys.executable,
        str(BAKEOFF_SCRIPT),
        "--split", "dev",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res.returncode == 0
    assert "BAKE-OFF DRY-RUN ACCOUNTING" in res.stdout
    assert "DRY RUN ONLY" in res.stdout


def test_test_split_without_final_flag_fails():
    cmd = [
        sys.executable,
        str(BAKEOFF_SCRIPT),
        "--split", "test",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res.returncode != 0
    assert "requires explicit --final flag" in res.stderr


def test_synthetic_offline_bakeoff_run(tmp_path):
    report_out = tmp_path / "test_report.md"
    cmd = [
        sys.executable,
        str(BAKEOFF_SCRIPT),
        "--split", "dev",
        "--no-dry-run",
        "--use-fakes",
        "--output-report", str(report_out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    assert res.returncode == 0, f"Error: {res.stderr}\nOutput: {res.stdout}"
    assert report_out.exists(), "Report markdown file must be generated"

    content = report_out.read_text(encoding="utf-8")
    assert "SYNTHETIC, not a benchmark" in content
    assert "Speech-to-Text (STT) Candidates" in content
    assert "Fast LLM Candidates" in content
    assert "Text-to-Speech (TTS) Candidates" in content
    assert "single-speaker baseline" in content
