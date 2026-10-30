# inspect-experiments

Hands-on LLM eval experiments with the Inspect framework.

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. From the repo root, run:

   ```sh
   uv sync
   ```

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

## Layout

- `src/inspect_experiments/`: package code
