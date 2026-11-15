# fix_syntax

A very simple bug-fix task. Each sample is a short Python script with one syntax error. The agent has to find and fix the error so the script runs and prints the right output.

**Results and QA:** see [RESULTS.md](RESULTS.md) for model results and figures, and [QA.md](QA.md) for the QA log, tests, and failure review. Some sections are still mock and are labeled as such.

## Samples

There are 8 samples, each with a different kind of syntax error. They're listed in `samples/samples.json`.

| Sample | Script | Error |
|---|---|---|
| `missing_colon_if` | `report.py` | Missing colon after an `if` condition |
| `missing_colon_for` | `inventory.py` | Missing colon after a `for` loop |
| `unclosed_paren` | `temperatures.py` | Unclosed parenthesis in a `print` call |
| `unclosed_string` | `greeting.py` | Unclosed string literal |
| `bad_indent` | `shipping.py` | Indentation that matches no outer block (`IndentationError`) |
| `assign_in_condition` | `attendance.py` | `=` instead of `==` in a condition |
| `missing_comma` | `prices.py` | Missing comma between dictionary entries |
| `else_if` | `grades.py` | `else if` instead of `elif` |

Each fix changes exactly one line. Each sample's folder in `samples/` holds three files:

- `broken.py`: the script with the error. It's copied into the sandbox as `/workspace/<script>`.
- `fixed.py`: the reference fix. It stays on the host.
- `expected.txt`: the answer key, the output the fixed script should print. It stays on the host.

To add a sample, create a folder with those three files and add a line to `samples.json`. The tests check that the files are consistent.

### Why several samples

One sample can only tell you "passed once" or "failed once." Several samples turn that into a measurement:

- **Accuracy needs more than one data point.** With one sample, accuracy can only be 0 or 1, so a model that fixes syntax errors 90% of the time can't be told apart from one that manages 60%. The stderr Inspect reports shows how uncertain the score is, and it shrinks as samples are added. For a model that truly passes half the time:

  | Samples | Possible scores | Stderr | Roughly, the true rate is within |
  |---|---|---|---|
  | 1 | 0 or 1 | not meaningful | anything |
  | 8 | steps of 0.125 | about 0.18 | ±0.35 |
  | 100 | steps of 0.01 | about 0.05 | ±0.10 |

  Eight is still small. It's enough to show the workflow and catch big differences, but not to separate two similar models.
- **Coverage.** One script tests whether a model can fix that one error. Eight kinds of error test whether it can fix syntax errors in general, and let results be broken down by error type.
- **More chances to catch problems in the task.** Each sample is another check on the setup. For example, the file-permission test now covers all eight scripts.
- **Less luck.** Models are nondeterministic. With one sample, a single lucky or unlucky run decides the whole score.

Samples and epochs answer different questions. More samples measure how well a model handles different problems. More epochs (`--epochs 3`) measure how consistently it handles the same problems. A thorough eval uses both.

These errors are easy, so most models will probably score near 1.0. A task that every model aces can't tell models apart. That's fine for a warm-up whose purpose is practicing the workflow. Separating models is the job of harder tasks.

## Files

| File | Where it goes | Purpose |
|---|---|---|
| `fix_syntax.py` | Host | Task definition: dataset, solvers, scorer, and sandbox |
| `Dockerfile` | Host | Builds the sandbox: Python 3.12, a non-root `agent` user, and an empty `/workspace` |
| `.dockerignore` | Host | Hides every file in this folder from the Docker build |
| `samples/` | Host, except each `broken.py` | The samples, as described above |
| `tests/test_scorer.py` | Host only | Automated tests for the samples and the scorer |
| `RESULTS.md` | Host only | Results and figures |
| `QA.md` | Host only | QA log, tests, failure review, and transcripts |
| `results/` | Host only | Per-model results from the eval logs, plus mock data files (`mock-*.json`) for charts without real data yet |
| `figures/` | Host only | The charts in `RESULTS.md`. Files starting with `mock-` are mock |

**Keeping the answers out of the sandbox.** The Docker image contains no scripts. When a sample starts, Inspect copies only that sample's `broken.py` into its sandbox. The fixes and expected outputs never enter the container. As a second guard, `.dockerignore` hides this whole folder from the Docker build, so even a `COPY . /workspace/` line couldn't pull them into the image. The only time a fix reaches the container is with `-T solution=reference`, which writes it there on purpose to test the scorer.

## Run it

**With a model.** Run this in a codespace only, with the provider's API key set as a Codespaces secret. See [GitHub Codespaces](../../docs/github-codespace.md). Each run costs a little:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py --model google/gemini-3.6-flash
```

The agent is Inspect's `react()` agent with one tool, `bash()`. It runs commands in the sandbox, then submits. Each sample gets its own sandbox. On a free tier, add `--max-connections 1` so the samples don't hit the rate limit all at once.

To run a few samples first, add `--limit 2`. To run one sample, add `--sample-id missing_comma`.

**Without a model, to test the scorer.** The `solution` option swaps the agent for a fixed solver:

```sh
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=reference --model mockllm/model
uv run inspect eval tasks/fix_syntax/fix_syntax.py -T solution=none --model mockllm/model
```

| `solution` | What it does | Expected accuracy |
|---|---|---|
| `agent` (default) | The model tries to fix each script | The share of samples it fixes |
| `reference` | Writes each sample's `fixed.py` into its sandbox | 1 |
| `none` | Leaves every script broken | 0 |

If `reference` scores 1 and `none` scores 0, the scorer can tell fixed scripts from broken ones.

## What the agent sees

The agent gets two messages: a system message from Inspect's `react()` agent, and the task's instructions.

**System message.** This is `react()`'s **default prompt**. The task doesn't set or change it:

```text
You are a helpful assistant attempting to submit the best possible answer. You have several tools available to help with finding the answer. You will see the result of tool calls right after sending the message. Prioritize parallel tool calls: when operations are independent, run them in one response — e.g. reading several files or running several searches at once — rather than one at a time. Only sequence calls when one depends on another's result. Do some reasoning before your actions, describing what tool calls you are going to use and how they fit into your plan.

When you have completed the task and have an answer, call the submit() tool to report it.
```

**Instructions**, from `PROMPT` in `fix_syntax.py`. The script path changes per sample:

```text
The Python script /workspace/report.py fails with a syntax error.
Fix the error so that `python3 /workspace/report.py` runs successfully.
Change as little as possible, and don't change what the script prints.
When you're done, submit.
```

The default prompt has three parts, set by `react()`'s `prompt` argument (an `AgentPrompt`):

| Part | Default | Sent in this task? |
|---|---|---|
| `instructions` | Empty | No |
| `handoff_prompt` | A paragraph about multi-agent systems and `transfer_to_<agent_name>` handoffs | No. It's only added when the agent has handoff tools, and this one doesn't |
| `assistant_prompt` | "You are a helpful assistant…" | Yes |
| `submit_prompt` | "…call the {submit}() tool to report it." | Yes, with `{submit}` replaced by `submit` |

The eval log records all four parts in the solver's settings, including the handoff paragraph. The system message in each sample's transcript is what the model actually received.

To change the prompt, pass `prompt=AgentPrompt(...)` to `react()`. Setting a part to `None` leaves it out. Results from a changed prompt aren't comparable with runs using the default, so record the change with the results.

## How it's scored

The `script_output()` scorer checks two things after the agent finishes. The result is `C` (correct) only if both pass:

1. **The script works.** It runs the sample's script in the sandbox. The script must exit without an error, and its output must match `expected.txt` exactly, apart from surrounding whitespace.
2. **The script was fixed, not rewritten.** It reads the script back from the sandbox and compares it with `broken.py`. At most 3 lines may change. Each real fix changes 1 line, so this allows a little slack for other valid fixes.

Each score also records a **verdict**: the reason it passed or failed, from the `Verdict` enum in `fix_syntax.py`. It's saved in the score's metadata as `verdict`, along with `lines_changed`. Only `fixed` counts as correct:

| Verdict | Meaning |
|---|---|
| `fixed` | The script runs, prints the expected output, and at most 3 lines changed |
| `still_broken` | The script errors or exits with a non-zero code |
| `wrong_output` | The script runs, but prints something else |
| `rewritten` | The output is right, but too many lines changed: the script was replaced, not fixed |
| `missing` | The script was deleted or moved |
| `timed_out` | The script itself ran for more than 30 seconds |

The score's explanation adds the detail: the script's error, such as `SyntaxError: expected ':'`, or how many lines changed.

## Tests

`tests/test_scorer.py` has three groups of tests. No model is called, so no API key is needed. From the repo root, run:

```sh
uv run pytest tasks/fix_syntax/tests
```

The tests take about 35 seconds. The sandbox tests need Docker and are skipped if it isn't running.

**Sample files, on the host.** These run without Docker:

| Test | What it checks |
|---|---|
| `test_sample_files_are_consistent` | For each sample: `broken.py` really has a syntax error, `fixed.py` runs and prints exactly `expected.txt`, and the two differ by exactly one line |
| `test_every_sample_folder_is_listed` | Every folder in `samples/` is in `samples.json`, and every entry has a folder |

**All samples, in the sandbox:**

| Test | What it checks |
|---|---|
| `test_all_reference_fixes_pass` | Every reference fix scores `C`, with the verdict `fixed` |
| `test_all_broken_scripts_fail` | Every broken script scores `I`, with the verdict `still_broken` and an error in the explanation, so it fails for the right reason |
| `test_agent_user_can_edit_every_script` | The non-root `agent` user can edit each copied script with `sed -i`, so a failed run isn't caused by file permissions |

**Scorer edge cases, on the `missing_colon_if` sample:**

| Test | Script | Expected score | Expected verdict |
|---|---|---|---|
| `test_wrong_output_fails` | Runs cleanly, but prints the average to 2 decimal places instead of 1 | `I` | `wrong_output` |
| `test_error_exit_fails` | Prints the right output, then exits with an error | `I` | `still_broken` |
| `test_trailing_whitespace_passes` | The reference fix plus a blank line at the end | `C` | `fixed` |
| `test_other_one_line_fix_passes` | A different valid fix: `if (avg > 80):` | `C` | `fixed` |
| `test_hardcoded_output_fails` | Replaced with a `print()` of the expected output. The test also checks that more than 3 lines changed | `I` | `rewritten` |
| `test_deleted_script_fails` | Deleted | `I` | `missing` |
| `test_separate_if_instead_of_elif_passes` | `else_if` sample: a separate `if` in place of `elif`, which behaves the same for every input | `C` | `fixed` |

Each test checks the verdict as well as the score, so a test can't pass for the wrong reason. For example, a deleted script must fail as `missing`, not as a script error.

## Shortcuts

**Closed: hardcoding the output.** The first version of the scorer checked only the output, not how the script produced it. An agent could replace the script with a `print()` of the expected text, which it could work out by reading the script, and still score `C`. The scorer now also checks that at most 3 lines changed. The hardcoded version of `report.py` changes 17 lines, so it scores `I`. `test_hardcoded_output_fails` guards against this coming back. While the shortcut was open, that test was marked as an expected failure (`xfail`).

**Still open: changing the logic in one line.** The check limits how much changes, not what. For example, `if True:` instead of `if avg > 80:` changes one line and prints the right output, because that script's data puts the average above 80. It scores `C`, even though it changes the script's logic. More samples don't fully close this: the agent sees each script's data, so it could choose a constant that works for that script. Running each fixed script on a second, hidden input, written into the sandbox only at scoring time, would catch it.

Red-teaming the scorer found three more gaps of the same kind: hardcoding a value such as `avg = 84.7` (QA-009), loosening `==` to `>=` (QA-010), and deleting a broken line that doesn't affect the output (QA-011). Each is tracked by a test marked `xfail` (expected to fail) until the scorer catches it. See [QA.md](QA.md#spec-and-scorer-review).
