from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import includes
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.util import sandbox

# Runs the sample's input as a shell command in the Docker sandbox, without
# calling a model, so it tests Docker on its own.
@solver
def run_in_sandbox():
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        result = await sandbox().exec(["sh", "-c", state.input_text])
        state.output = ModelOutput.from_content(model="sandbox", content=result.stdout)
        return state

    return solve

@task
def hello_docker():
    return Task(
        dataset=[Sample(input="echo hello from docker", target="hello from docker")],
        solver=run_in_sandbox(),
        scorer=includes(),
        sandbox="docker",
    )
