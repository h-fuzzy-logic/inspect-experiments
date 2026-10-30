# inspect-experiments

Hands-on LLM eval experiments with the Inspect framework.

## Pre-Reqs

1. Install [uv](https://docs.astral.sh/uv/).
2. Install the **Inspect AI** extension in VS Code (publisher: UK AISI, ID `ukaisi.inspect-ai`). 

## Setup

1. From the repo root, run:

   ```sh
   uv sync
   ```

2. In VS Code, select the project interpreter at `.venv/bin/python` (see Python: Select Interpreter). The extension needs it to find `inspect-ai`.

## Environment variables

Secrets go in a `.env` file at the repo root. This file is git-ignored, so create your own:

```sh
SOME_API_KEY=your-key-here
```

Replace the placeholder with the keys the experiments need. `python-dotenv` is not a dependency yet, so code does not load `.env` automatically. To add it, run `uv add python-dotenv`.

## Running

```sh
uv run inspect-experiments
```

This currently prints a placeholder message.

## Run Eval

Run the `hello` task against the built-in mock model, which needs no API key:

```sh
uv run inspect eval tasks/hello/hello.py --model mockllm/model
```

Results are written to `logs/`. To view them, run `uv run inspect view --log-dir logs`.

## Layout

- `src/inspect_experiments/`: package code shared by tasks, such as scorers, solvers, and dataset helpers
- `tasks/<name>/`: one folder per experiment, holding the task file and its data or notes. Run a task by path:

  ```sh
  uv run inspect eval tasks/hello/hello.py
  ```

- `logs/`: eval output (`.eval` files), created by Inspect runs. Git-ignored.
