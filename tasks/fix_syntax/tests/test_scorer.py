"""Tests for the fix_syntax samples and scorer.

The sample-file tests run on the host and need nothing else. The other tests
write versions of a script into the real sandbox, then run the task's scorer
on them. No model is called: the solvers here replace the agent. Docker must
be running for those, or they're skipped.

Run from the repo root:
    uv run pytest tasks/fix_syntax/tests
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from inspect_ai import eval
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.util import sandbox

TASK_DIR = Path(__file__).resolve().parents[1]
TASK_FILE = TASK_DIR / "fix_syntax.py"
SAMPLES_DIR = TASK_DIR / "samples"

# Load the task module, so the tests use the same helpers and limits as the scorer.
_spec = importlib.util.spec_from_file_location("fix_syntax_task", TASK_FILE)
task_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(task_module)

SAMPLE_IDS = [s["id"] for s in json.loads((SAMPLES_DIR / "samples.json").read_text())]

# The sample the single-sample scorer tests use.
FOCUS = "missing_colon_if"


def sample_text(sample_id: str, name: str) -> str:
    return (SAMPLES_DIR / sample_id / name).read_text()


BROKEN = sample_text(FOCUS, "broken.py")
REFERENCE = sample_text(FOCUS, "fixed.py")
EXPECTED_OUTPUT = sample_text(FOCUS, "expected.txt")


def docker_running() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


needs_docker = pytest.mark.skipif(not docker_running(), reason="Docker isn't running")


def run_task(log_dir: Path, solver=None, task_args=None, sample_id=None) -> dict:
    """Run the task with the mock model, and return each sample's score by ID."""
    [log] = eval(
        # Inspect's task loader needs a relative path.
        os.path.relpath(TASK_FILE),
        model="mockllm/model",
        solver=solver,
        task_args=task_args or {},
        sample_id=sample_id,
        display="none",
        log_dir=str(log_dir),
    )
    assert log.status == "success", log.error
    return {sample.id: sample.scores["script_output"] for sample in log.samples}


@solver
def write_script(content: str):
    """Stand in for the agent: write the given content as the sample's script."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        await sandbox().write_file(state.metadata["script"], content)
        return state

    return solve


@solver
def edit_script_in_place():
    """Edit the script with sed -i as the sandbox's default user, the way an agent might."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        result = await sandbox().exec(["sed", "-i", "s/$//", state.metadata["script"]])
        if not result.success:
            raise RuntimeError(f"Agent user can't edit the script: {result.stderr}")
        return state

    return solve


def score_for(content: str, log_dir: Path):
    """Run the FOCUS sample with its script set to `content`, and return its score."""
    return run_task(log_dir, solver=[write_script(content)], sample_id=FOCUS)[FOCUS]


# --- Sample files (host only)


@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_sample_files_are_consistent(sample_id):
    broken = sample_text(sample_id, "broken.py")
    fixed = sample_text(sample_id, "fixed.py")
    # The broken script really has a syntax error. IndentationError is a kind of SyntaxError.
    with pytest.raises(SyntaxError):
        compile(broken, "broken.py", "exec")
    # The fix runs and prints exactly the expected output.
    result = subprocess.run([sys.executable, "-c", fixed], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == sample_text(sample_id, "expected.txt").strip()
    # The fix changes exactly one line, well within what the scorer allows.
    assert task_module.changed_lines(broken, fixed) == 1


def test_every_sample_folder_is_listed():
    folders = {p.name for p in SAMPLES_DIR.iterdir() if p.is_dir()}
    assert folders == set(SAMPLE_IDS)


# --- All samples, in the sandbox


@needs_docker
def test_all_reference_fixes_pass(tmp_path):
    scores = run_task(tmp_path, task_args={"solution": "reference"})
    assert set(scores) == set(SAMPLE_IDS)
    assert {sid: s.value for sid, s in scores.items()} == {sid: "C" for sid in SAMPLE_IDS}


@needs_docker
def test_all_broken_scripts_fail(tmp_path):
    scores = run_task(tmp_path, task_args={"solution": "none"})
    for sample_id, score in scores.items():
        assert score.value == "I", sample_id
        # Fails for the right reason: the real broken script ran in the task's own image.
        assert "Error" in score.explanation, sample_id


@needs_docker
def test_agent_user_can_edit_every_script(tmp_path):
    # run_task fails if the solver raises, which it does if sed -i can't edit the script.
    run_task(tmp_path, solver=[edit_script_in_place()])


# --- Scorer edge cases, on one sample


@needs_docker
def test_wrong_output_fails(tmp_path):
    # Runs cleanly, but prints the average to 2 decimal places instead of 1.
    near_miss = REFERENCE.replace("{avg:.1f}", "{avg:.2f}")
    assert near_miss != REFERENCE
    assert score_for(near_miss, tmp_path).value == "I"


@needs_docker
def test_error_exit_fails(tmp_path):
    # Prints exactly the right output, then exits with an error.
    assert score_for(REFERENCE + "raise SystemExit(1)\n", tmp_path).value == "I"


@needs_docker
def test_trailing_whitespace_passes(tmp_path):
    # The scorer strips surrounding whitespace, so an extra blank line is fine.
    assert score_for(REFERENCE + 'print("")\n', tmp_path).value == "C"


@needs_docker
def test_other_one_line_fix_passes(tmp_path):
    # A different valid fix: parentheses around the condition, plus the colon.
    other_fix = BROKEN.replace("if avg > 80\n", "if (avg > 80):\n")
    assert other_fix != BROKEN
    assert score_for(other_fix, tmp_path).value == "C"


@needs_docker
def test_hardcoded_output_fails(tmp_path):
    # Replaces the script with a print of the expected output, without fixing anything.
    # The output is right, but the scorer sees that the whole script changed.
    shortcut = f"print({EXPECTED_OUTPUT.strip()!r})\n"
    score = score_for(shortcut, tmp_path)
    assert score.value == "I"
    assert "lines changed" in score.explanation
