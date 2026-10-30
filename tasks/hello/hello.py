from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.solver import generate

@task
def hello():
    return Task(
        dataset=[
            Sample(input="What is 12 * 12? Answer with the number only.", target="144"),
            Sample(input="What is the capital of Tennessee? One word.", target="Nashville"),
        ],
        solver=generate(),
        scorer=includes(),
    )