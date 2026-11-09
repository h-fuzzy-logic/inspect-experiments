# CLAUDE.md

## Model calls

- Locally, run evals only with `--model mockllm/model`. Never run an eval with a real model (such as `anthropic/…`, `google/…`, or `openai/…`) on this machine.
- Real model runs happen only in cloud resources, like GitHub Codespace or AWS, and the user starts them. Don't start one. Give the user the command to run instead.
- To test a task without a model, use the mock model or the task's reference solution, such as `-T solution=reference`.

## API keys

- Never write an API key to any file, including `.env`, and never print one.
- Keys live only in Codespaces secrets, such as `GOOGLE_API_KEY`. Nothing in this repo or on this machine should hold a real key.

## Repo

- Tasks are in `tasks/<name>/`, listed in order in `tasks/README.md`.
- Eval logs go to `logs/`, and scratch files go to `tmp/`. Both are git-ignored.
