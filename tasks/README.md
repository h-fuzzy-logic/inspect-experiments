# Tasks

Work through the tasks in this order. Each one adds one new piece.

| # | Task | What it tests | Needs |
|---|---|---|---|
| 1 | [hello](hello/hello.py) | Inspect runs and writes a log | Nothing (mock model) |
| 2 | [hello_docker](hello_docker/README.md) | Inspect starts a Docker sandbox and runs a command in it | Docker (mock model) |
| 3 | [fix_syntax](fix_syntax/README.md) | An agent fixes a syntax error in a Python file, scored by running the script | Docker and an API key. The scorer can be tested without a key |

Run any task from the repo root by its file path, for example:

```sh
uv run inspect eval tasks/hello/hello.py --model mockllm/model
```
