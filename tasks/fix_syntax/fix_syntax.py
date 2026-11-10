import difflib
import json
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


@scorer(metrics=[accuracy(), stderr()])
def script_output():
    """Run the script in the sandbox, compare its output to the expected output, and check the fix is small."""

    async def score(state: TaskState, target: Target) -> Score:
        script = state.metadata["script"]
        try:
            result = await sandbox().exec(["python3", script], cwd=WORKSPACE, timeout=30)
        except TimeoutError:
            return Score(value=INCORRECT, explanation="Script timed out")
        output = result.stdout.strip()
        if not (result.success and output == target.text.strip()):
            return Score(
                value=INCORRECT,
                answer=output,
                explanation=result.stderr.strip() or f"exit code {result.returncode}",
            )

        # The output is right. Check the script was fixed, not rewritten to print the answer.
        try:
            fixed_script = await sandbox().read_file(script)
        except FileNotFoundError:
            return Score(value=INCORRECT, answer=output, explanation="Script is missing")
        changed = changed_lines(sample_file(state, "broken.py"), fixed_script)
        if changed > MAX_CHANGED_LINES:
            return Score(
                value=INCORRECT,
                answer=output,
                explanation=f"Output is right, but {changed} lines changed (at most {MAX_CHANGED_LINES} allowed)",
            )
        return Score(value=CORRECT, answer=output, explanation=f"Output is right, and {changed} line(s) changed")

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
