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
| `tests/test_scorer.py` | Host only | Automated tests for the scorer |

The expected output, the answer key, is in `fix_syntax.py` on the host, so the agent can't read or change it.

**Keeping the answers out of the sandbox.** The Dockerfile copies only `sandbox/`. As a second guard, `.dockerignore` hides every other file from the Docker build, so even a `COPY . /workspace/` line couldn't pull in `solution/` or `fix_syntax.py`. The only time the reference fix reaches the container is with `-T solution=reference`, which writes it there on purpose to test the scorer.

## Run it

**With a model.** Run this in a codespace only, with the provider's API key set as a Codespaces secret. See [GitHub Codespaces](../../docs/github-codespace.md). Each run costs a little:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py --model google/gemini-3.6-flash
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

The `script_output()` scorer checks two things after the agent finishes. The result is `C` (correct) only if both pass:

1. **The script works.** It runs `python3 /workspace/report.py` in the sandbox. The script must exit without an error, and its output must match the expected output exactly, apart from surrounding whitespace.
2. **The script was fixed, not rewritten.** It reads the script back from the sandbox and compares it with the original broken script. At most 3 lines may change. The real fix changes 1 line, so this allows a little slack for other valid fixes.

The score's explanation says what happened: the script's error, such as `SyntaxError: expected ':'`, how many lines changed if there were too many, or that the output was right and how many lines changed.

## Scorer tests

The tests in `tests/test_scorer.py` check that the scorer gives the right score for different versions of the script. Each test writes a version of `report.py` into the real sandbox, then runs the scorer. No model is called, so no API key is needed. Docker must be running. From the repo root, run:

```sh
uv run pytest tasks/fix_syntax/tests
```

The tests take about 20 seconds, and are skipped if Docker isn't running.

| Test | Script | Expected score |
|---|---|---|
| `test_reference_fix_passes` | The reference fix | `C` |
| `test_broken_script_fails` | The original broken script. The test also checks that the error is the `SyntaxError`, so it fails for the right reason | `I` |
| `test_wrong_output_fails` | Runs cleanly, but prints the average to 2 decimal places instead of 1 | `I` |
| `test_error_exit_fails` | Prints the right output, then exits with an error | `I` |
| `test_trailing_whitespace_passes` | The reference fix plus a blank line at the end | `C` |
| `test_other_one_line_fix_passes` | A different valid fix: `if (avg > 80):` | `C` |
| `test_hardcoded_output_fails` | Replaced with a `print()` of the expected output. The test also checks that the explanation mentions the lines changed | `I` |

## Shortcuts

**Closed: hardcoding the output.** The first version of the scorer checked only the output, not how the script produced it. An agent could replace the script with a `print()` of the expected text, which it could work out by reading the script, and still score `C`. The scorer now also checks that at most 3 lines changed. The hardcoded version changes 17 lines, so it scores `I`. `test_hardcoded_output_fails` guards against this coming back. While the shortcut was open, that test was marked as an expected failure (`xfail`).

**Still open: changing the logic in one line.** The check limits how much changes, not what. For example, `if True:` instead of `if avg > 80:` changes one line, and prints the right output, because this data's average happens to be above 80. It scores `C`, even though it changes the script's logic. Samples where the condition goes the other way, or several test inputs per script, would catch this.
