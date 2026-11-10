"""Tests for the fix_syntax scorer.

Each test writes a version of report.py into the real sandbox, then runs the
task's scorer on it. No model is called: the mock model is never used, because
the solver below replaces the agent. Docker must be running.

Run from the repo root:
    uv run pytest tasks/fix_syntax/tests
"""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from inspect_ai import eval
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.util import sandbox

TASK_DIR = Path(__file__).resolve().parents[1]
TASK_FILE = TASK_DIR / "fix_syntax.py"

# Load the task module for its constants, so the tests use the same answer key.
_spec = importlib.util.spec_from_file_location("fix_syntax_task", TASK_FILE)
task_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task_module)

BROKEN = (TASK_DIR / "sandbox" / "report.py").read_text()
REFERENCE = (TASK_DIR / "solution" / "report.py").read_text()
EXPECTED_OUTPUT = task_module.EXPECTED_OUTPUT


def docker_running() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not docker_running(), reason="Docker isn't running")


@solver
def write_script(content: str):
    """Stand in for the agent: write the given content as the script."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        await sandbox().write_file(task_module.SCRIPT, content)
        return state

    return solve


def score_for(content: str | None, log_dir: Path):
    """Run the task with the script set to `content` (None leaves it broken), and return its score."""
    solvers = [] if content is None else [write_script(content)]
    [log] = eval(
        # Inspect's task loader needs a relative path.
        os.path.relpath(TASK_FILE),
        model="mockllm/model",
        solver=solvers,
        display="none",
        log_dir=str(log_dir),
    )
    assert log.status == "success", log.error
    return log.samples[0].scores["script_output"]


def test_reference_fix_passes(tmp_path):
    assert score_for(REFERENCE, tmp_path).value == "C"


def test_broken_script_fails(tmp_path):
    score = score_for(None, tmp_path)
    assert score.value == "I"
    # Fails for the right reason: the real broken script ran in the task's own image.
    assert "SyntaxError" in score.explanation


def test_wrong_output_fails(tmp_path):
    # Runs cleanly, but prints the average to 2 decimal places instead of 1.
    near_miss = REFERENCE.replace("{avg:.1f}", "{avg:.2f}")
    assert near_miss != REFERENCE
    assert score_for(near_miss, tmp_path).value == "I"


def test_error_exit_fails(tmp_path):
    # Prints exactly the right output, then exits with an error.
    assert score_for(REFERENCE + "raise SystemExit(1)\n", tmp_path).value == "I"


def test_trailing_whitespace_passes(tmp_path):
    # The scorer strips surrounding whitespace, so an extra blank line is fine.
    assert score_for(REFERENCE + 'print("")\n', tmp_path).value == "C"


def test_other_one_line_fix_passes(tmp_path):
    # A different valid fix: parentheses around the condition, plus the colon.
    other_fix = BROKEN.replace("if avg > 80\n", "if (avg > 80):\n")
    assert other_fix != BROKEN
    assert score_for(other_fix, tmp_path).value == "C"


def test_hardcoded_output_fails(tmp_path):
    # Replaces the script with a print of the expected output, without fixing anything.
    # The output is right, but the scorer sees that the whole script changed.
    shortcut = f"print({EXPECTED_OUTPUT!r})\n"
    score = score_for(shortcut, tmp_path)
    assert score.value == "I"
    assert "lines changed" in score.explanation
