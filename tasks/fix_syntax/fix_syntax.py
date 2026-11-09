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
SCRIPT = "/workspace/report.py"

PROMPT = f"""The Python script {SCRIPT} fails with a syntax error.
Fix the error so that `python3 {SCRIPT}` runs successfully.
Change as little as possible, and don't change what the script prints.
When you're done, submit."""

# The answer key. It lives here on the host, so the agent can't read or change it.
EXPECTED_OUTPUT = """alice: 91
bob: 78
carol: 85
average: 84.7
Class average is above 80"""


@solver
def reference_fix():
    """Write the known-good fix into the sandbox. Checks that the scorer passes a correct answer."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        await sandbox().write_file(SCRIPT, (TASK_DIR / "solution" / "report.py").read_text())
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
    """Run the script in the sandbox and compare its output to the expected output."""

    async def score(state: TaskState, target: Target) -> Score:
        try:
            result = await sandbox().exec(["python3", SCRIPT], cwd="/workspace", timeout=30)
        except TimeoutError:
            return Score(value=INCORRECT, explanation="Script timed out")
        output = result.stdout.strip()
        correct = result.success and output == target.text.strip()
        return Score(
            value=CORRECT if correct else INCORRECT,
            answer=output,
            explanation=result.stderr.strip() or f"exit code {result.returncode}",
        )

    return score


@task
def fix_syntax(solution: Literal["agent", "reference", "none"] = "agent"):
    solvers = {
        "agent": react(tools=[bash(timeout=60)]),
        "reference": reference_fix(),
        "none": no_fix(),
    }
    return Task(
        dataset=[Sample(input=PROMPT, target=EXPECTED_OUTPUT)],
        solver=solvers[solution],
        scorer=script_output(),
        sandbox="docker",
        # A one-line fix needs only a few turns. This stops a stuck agent from running up costs.
        message_limit=30,
    )
