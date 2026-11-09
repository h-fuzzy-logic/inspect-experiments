# fix_syntax

A very simple bug-fix task. A short Python script, `report.py`, fails with a syntax error: an `if` statement is missing its colon. The agent has to find and fix the error so the script runs and prints the right output.

## Files

| File | Where it goes | Purpose |
|---|---|---|
| `fix_syntax.py` | Host | Task definition: dataset, solvers, scorer, and sandbox |
| `Dockerfile` | Host | Builds the sandbox: Python 3.12, a non-root `agent` user, and `/workspace` |
| `.dockerignore` | Host | Hides everything except `sandbox/` from the Docker build |
| `sandbox/report.py` | Container | The broken script, copied to `/workspace/report.py` |
| `solution/report.py` | Host only | The reference fix. Never copied into the container |

The expected output, the answer key, is in `fix_syntax.py` on the host, so the agent can't read or change it.

**Keeping the answers out of the sandbox.** The Dockerfile copies only `sandbox/`. As a second guard, `.dockerignore` hides every other file from the Docker build, so even a `COPY . /workspace/` line couldn't pull in `solution/` or `fix_syntax.py`. The only time the reference fix reaches the container is with `-T solution=reference`, which writes it there on purpose to test the scorer.

## Run it

**With a model.** Run this in a codespace only, with the provider's API key set as a Codespaces secret. See [API keys](../../README.md#api-keys). Each run costs a little:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py --model google/gemini-2.5-flash
```

The agent is Inspect's `react()` agent with one tool, `bash()`. It runs commands in the sandbox, then submits.

**Without a model, to test the scorer.** The `solution` option swaps the agent for a fixed solver:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=reference --model mockllm/model
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=none --model mockllm/model
```

| `solution` | What it does | Expected accuracy |
|---|---|---|
| `agent` (default) | The model tries to fix the script | 1 if it succeeds |
| `reference` | Writes `solution/report.py` into the sandbox | 1 |
| `none` | Leaves the script broken | 0 |

If `reference` scores 1 and `none` scores 0, the scorer can tell a fixed script from a broken one.

## How it's scored

The `script_output()` scorer runs `python3 /workspace/report.py` in the sandbox after the agent finishes. The result is `C` (correct) only if the script exits without an error **and** its output matches the expected output exactly. The score's explanation shows the script's error, such as `SyntaxError: expected ':'`, or its exit code.

## Known shortcut

The scorer checks the output, not how the script produced it. An agent could replace the script with `print()` calls that write out the expected text and still score `C`. It could work out the text by reading the script. A stricter scorer could also check that the fixed file differs from the original by only a line or two. This is the kind of misspecification the QA pass is meant to catch.
