import difflib
import json
from enum import StrEnum
from pathlib import Path
from typing import Literal

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target, accuracy, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.tool import bash
from inspect_ai.util import sandbox

TASK_DIR = Path(__file__).parent
SAMPLES_DIR = TASK_DIR / "samples"
WORKSPACE = "/workspace"

PROMPT = """The Python script {script} fails with a syntax error.
Fix the error so that `python3 {script}` runs successfully.
Change as little as possible, and don't change what the script prints.
When you're done, submit."""

# Each fix is one line. This allows a little slack for other valid fixes,
# but fails a rewrite, such as replacing the script with print() calls.
MAX_CHANGED_LINES = 3


class Verdict(StrEnum):
    """Why a run passed or failed. Saved in each score's metadata, so tests and results can check the reason."""

    FIXED = "fixed"  # runs, prints the expected output, and the edit is small
    STILL_BROKEN = "still_broken"  # the script errors or exits with a non-zero code
    WRONG_OUTPUT = "wrong_output"  # the script runs but prints something else
    REWRITTEN = "rewritten"  # right output, but too many lines changed: replaced, not fixed
    MISSING = "missing"  # the script was deleted or moved
    TIMED_OUT = "timed_out"  # the script itself hung


def load_samples() -> list[Sample]:
    """One sample per folder in samples/, listed in samples/samples.json."""
    samples = []
    for entry in json.loads((SAMPLES_DIR / "samples.json").read_text()):
        sample_dir = SAMPLES_DIR / entry["id"]
        script = f"{WORKSPACE}/{entry['script']}"
        samples.append(
            Sample(
                id=entry["id"],
                input=PROMPT.format(script=script),
                # The answer key. It stays on the host, so the agent can't read or change it.
                target=(sample_dir / "expected.txt").read_text(),
                # Only the broken script is copied into the sandbox. fixed.py stays on the host.
                files={script: str(sample_dir / "broken.py")},
                metadata={"script": script, "error": entry["error"]},
            )
        )
    return samples


def sample_file(state: TaskState, name: str) -> str:
    """Read one of the sample's files on the host, such as broken.py or fixed.py."""
    return (SAMPLES_DIR / str(state.sample_id) / name).read_text()


def changed_lines(before: str, after: str) -> int:
    """Count lines changed between two scripts. A replaced line counts once, and trailing whitespace is ignored."""
    a = [line.rstrip() for line in before.splitlines()]
    b = [line.rstrip() for line in after.splitlines()]
    removed = added = 0
    for line in difflib.ndiff(a, b):
        if line.startswith("- "):
            removed += 1
        elif line.startswith("+ "):
            added += 1
    return max(removed, added)


@solver
def reference_fix():
    """Write the sample's known-good fix into the sandbox. Checks that the scorer passes a correct answer."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        await sandbox().write_file(state.metadata["script"], sample_file(state, "fixed.py"))
        return state

    return solve


@solver
def no_fix():
    """Leave the script broken. Checks that the scorer fails the original file."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        return state

    return solve


def verdict_score(verdict: Verdict, explanation: str, output: str | None = None, changed: int | None = None) -> Score:
    """A score for a verdict. Only FIXED counts as correct."""
    return Score(
        value=CORRECT if verdict is Verdict.FIXED else INCORRECT,
        answer=output,
        explanation=explanation,
        metadata={"verdict": verdict.value, "lines_changed": changed},
    )


@scorer(metrics=[accuracy(), stderr()])
def script_output():
    """Check the script still exists, runs, prints the expected output, and was fixed rather than rewritten."""

    async def score(state: TaskState, target: Target) -> Score:
        script = state.metadata["script"]
        try:
            current_script = await sandbox().read_file(script)
        except FileNotFoundError:
            return verdict_score(Verdict.MISSING, "Script is missing")
        changed = changed_lines(sample_file(state, "broken.py"), current_script)

        try:
            result = await sandbox().exec(["python3", script], cwd=WORKSPACE, timeout=30)
        except TimeoutError:
            return verdict_score(Verdict.TIMED_OUT, "Script timed out", changed=changed)
        output = result.stdout.strip()
        if not result.success:
            explanation = result.stderr.strip() or f"exit code {result.returncode}"
            return verdict_score(Verdict.STILL_BROKEN, explanation, output, changed)
        if output != target.text.strip():
            return verdict_score(Verdict.WRONG_OUTPUT, "Script runs, but its output doesn't match", output, changed)

        # The output is right. Check the script was fixed, not rewritten to print the answer.
        if changed > MAX_CHANGED_LINES:
            explanation = f"Output is right, but {changed} lines changed (at most {MAX_CHANGED_LINES} allowed)"
            return verdict_score(Verdict.REWRITTEN, explanation, output, changed)
        return verdict_score(Verdict.FIXED, f"Output is right, and {changed} line(s) changed", output, changed)

    return score


@task
def fix_syntax(solution: Literal["agent", "reference", "none"] = "agent"):
    solvers = {
        "agent": react(tools=[bash(timeout=60)]),
        "reference": reference_fix(),
        "none": no_fix(),
    }
    return Task(
        dataset=load_samples(),
        solver=solvers[solution],
        scorer=script_output(),
        sandbox="docker",
        # A one-line fix needs only a few turns. This stops a stuck agent from running up costs.
        message_limit=30,
    )
