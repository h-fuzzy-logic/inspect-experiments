# Engineering practices

The software and data engineering practices this repo demonstrates. Each heading is a practice, and its bullets are examples from the repo, with links to where they're shown.

## Testing

### Golden-file testing

- **Expected outputs:** each sample's `expected.txt` is the exact output of its reference fix, and the scorer compares the agent's output with it. See [How it's scored](../tasks/fix_syntax/README.md#how-its-scored).
- **Fixtures checked for consistency:** a test confirms every `broken.py` fails, every `fixed.py` prints exactly `expected.txt`, and the two differ by one line. See `test_sample_files_are_consistent` in [`test_scorer.py`](../tasks/fix_syntax/tests/test_scorer.py).

### Positive and negative controls

- **Known-good input must pass:** the `reference` solver writes each reference fix, and every one must score `C`. See [Run it](../tasks/fix_syntax/README.md#run-it).
- **Known-bad input must fail:** the `none` solver leaves every script broken, and every one must score `I`.
- **Other valid solutions must pass too:** another one-line fix, and a separate `if` in place of `elif`, both score `C`. See [Tests](../tasks/fix_syntax/README.md#tests).

### Assert the reason, not just the result

- **Tests check the verdict as well as the score,** so a test can't pass for the wrong reason. For example, a deleted script must fail as `missing`, not as a script error. See [Tests](../tasks/fix_syntax/README.md#tests).

### Adversarial testing

- **Red-teaming the scorer:** plausible wrong fixes were written on purpose, such as replacing the script with a `print()` of the answer, `if True:`, a hardcoded value, a looser comparison, or deleting the broken line, and each was run through the scorer. See [Spec and scorer review](../tasks/fix_syntax/QA.md#spec-and-scorer-review).
- **Literal compliance tested:** each wrong fix follows the instructions to the letter while breaking their intent. This is the same idea as mutation testing, applied to the scorer instead of to code.

### Regression tests for every fixed bug

- **Scoring shortcut:** `test_hardcoded_output_fails` guards the fix for QA-002.
- **File permissions:** `test_agent_user_can_edit_every_script` guards the fix for QA-001. See [Building](../tasks/fix_syntax/QA.md#building).

### Known bugs tracked as expected failures

- **Strict `xfail` tests:** each open scorer gap has a test marked `xfail(strict=True)`. When the gap is fixed, the test passes unexpectedly and pytest fails the run until the marker is removed. See [Tests](../tasks/fix_syntax/QA.md#tests).
- **Checked for the right failure:** the `xfail` tests were run with `--runxfail` to confirm each fails on its score assertion, not on a setup error.

### Test the tests

- **Refactors checked against the old output:** chart refactors were compared pixel by pixel with the previous images.
- **Data and its index kept in sync:** a test checks that every folder in `samples/` is listed in `samples.json`, and every entry has a folder.

## Software design

### Explicit states instead of free text

- **Named outcomes:** the `Verdict` enum (`fixed`, `still_broken`, `wrong_output`, `rewritten`, `missing`, `timed_out`) records why each run passed or failed, in every log. Tests and results read the enum value, not an explanation string. See [How it's scored](../tasks/fix_syntax/README.md#how-its-scored).

### Single source of truth

- **One place builds every score:** `verdict_score()` is the only way the scorer makes a score, so "only `fixed` counts as correct" lives in one line. See [`fix_syntax.py`](../tasks/fix_syntax/fix_syntax.py).
- **One style for every chart:** all charts take their colors and fonts from [`style.py`](../src/create_visuals/style.py).

### Data-driven design

- **Samples are data, not code:** adding a sample is a new folder and a line in `samples.json`. See [Samples](../tasks/fix_syntax/README.md#samples).
- **Parameterized scripts:** the chart scripts take the results file, chart kind, row labels, and output path as arguments, so they work for any task. See [`src/create_visuals/`](../src/create_visuals/README.md).

### Swappable components

- **One parameter swaps the solver:** `-T solution=agent|reference|none` changes what solves the task without changing the task or scorer. See [Run it](../tasks/fix_syntax/README.md#run-it).

### Ordered checks that report the true cause

- **Existence before execution:** the scorer checks the script exists before running it, so a deleted file shows as `missing`, not as a script error. See [`fix_syntax.py`](../tasks/fix_syntax/fix_syntax.py).

### Modeling with UML

The docs separate *what a thing is* from *where it runs* and *what happens over time*:

- [Class diagram](eval-architecture.md#class-diagram): the general concepts
- [Object diagram](eval-architecture.md#object-diagram): concrete instances, with `«instance of»` links
- [Composite structure](eval-architecture.md#evaluation-system-components): the whole system as nested parts
- [Deployment diagram](eval-architecture.md#deployment): parts mapped to machines and runtimes
- [Sequence diagrams](agent-sandbox-sequence.md): one agent turn, and a whole run

## Reliability

### Reproducible builds

- **Locked dependencies:** [`uv.lock`](../uv.lock) and [`.python-version`](../.python-version).
- **Dev container:** [`.devcontainer/`](../.devcontainer/devcontainer.json) builds the same environment in every Codespace, with uv at a pinned version. See [GitHub Codespaces](github-codespaces.md#whats-in-the-dev-container).
- **Environment as code:** each task's sandbox is built from its own [`Dockerfile`](../tasks/fix_syntax/Dockerfile).

### Isolation

- **A fresh container for every run:** each sample in each epoch starts from the original files, so one run can't affect another. See [Container lifecycle](eval-architecture.md#container-lifecycle).

### Timeouts on every external call

- **Model requests:** `--attempt-timeout` abandons and retries a request that doesn't answer. Inspect sets no timeout by default (QA-006). See [Run review](../tasks/fix_syntax/QA.md#run-review).
- **Runs:** a message limit in the task, and `--time-limit` on each run.
- **Agent code:** the scorer stops the agent's script after 30 seconds and records `timed_out`.

### Graceful degradation

- **Tests skip cleanly without Docker,** instead of failing.
- **Limit hits counted separately:** a run cut off by a limit is still scored on its files, and limit hits are reported per model (QA-005). See [Results](../tasks/fix_syntax/RESULTS.md#results).

## Security

### Least privilege

- **Non-root user:** the agent runs as a user that owns only `/workspace`.
- **No network:** the sandbox has no network access.
- **No credentials:** the sandbox gets no API keys, since the model is called from outside it. See [Deployment](eval-architecture.md#deployment).
- **Tested both ways:** a test confirms the agent can still edit every script, so the lock-down doesn't make the task unfair (QA-001).

### Defense in depth

- **Two guards on the answers:** only each sample's broken script enters its sandbox, and `.dockerignore` hides the whole task folder from the image build. A test build with `COPY .` confirmed nothing gets through (QA-003). See [Keeping the answers out of reach](safety-and-cost.md#keeping-the-answers-out-of-reach).

### Secrets management

- **Secrets in a secret store only:** API keys live in Codespaces secrets, never in files. See [Set up](github-codespaces.md#set-up).
- **Rules written down for every contributor,** including AI assistants, in [`CLAUDE.md`](../CLAUDE.md).

### Fail closed

- **No keys on the laptop:** a real model call there fails instead of running.
- **Guard script:** [`scripts/check_model.sh`](../scripts/check_model.sh) refuses to run outside a Codespace.

## Data engineering

### Data validation

- **Inputs checked before use:** the sample tests validate every sample's files before any eval runs.
- **Logs filtered on the way in:** [`summarize_results.py`](../src/create_visuals/summarize_results.py) can skip mock logs and logs with too few samples, and keeps only the newest log per model. See [Summarize the logs](../src/create_visuals/README.md#1-summarize-the-logs).

### Lineage and provenance

- **Every result traces to its source:** each eval log records the git commit it ran on, and `results.json` records which log each model's numbers came from. See [Results file fields](../src/create_visuals/README.md#results-file-fields).
- **Runs documented for reproduction:** [Reproduce](../tasks/fix_syntax/RESULTS.md#reproduce) lists the commit, Inspect version, run dates, and commands.

### Structured logging

- **Machine-readable metadata:** each score saves its verdict and lines changed, so results can be counted without parsing text.
- **Per-run records:** `summarize_results.py` extracts each run's epoch, score, verdict, limit, error, and time, plus token use and verdict counts per model.

### Reproducible pipelines

- **Results rebuilt from raw logs:** `results.json` and every figure are generated by scripts from the eval logs, with one set of commands. See [Reproduce](../tasks/fix_syntax/RESULTS.md#reproduce).

### Labeled synthetic data

- **Mock data marked everywhere:** in file names (`mock-*`), chart badges, and each page's status table. See the status table in [RESULTS.md](../tasks/fix_syntax/RESULTS.md).

## Analysis and reporting

### Quantified uncertainty

- **Error bars and stderr:** pass rates are shown with 95% confidence intervals. See [Results](../tasks/fix_syntax/RESULTS.md#results).
- **Sample size explained:** the task README shows how few samples limit what a score can say. See [Why several samples](../tasks/fix_syntax/README.md#why-several-samples).
- **Claims kept in proportion:** differences between models are described as differences between these evals, backed by repeat evals. See [Repeat evals](../tasks/fix_syntax/RESULTS.md#repeat-evals).

### Accessible visualization

- **Colorblind-safe colors,** checked with a validation script.
- **No color-only meaning:** outcomes always pair a color with a symbol (✓, ✗, L).

### Open issues stay visible

- **Gaps reported, not hidden:** open findings stay in the [QA log](../tasks/fix_syntax/QA.md#qa-log) and [Limitations](../tasks/fix_syntax/RESULTS.md#limitations) until fixed.

## Process

### Requirements traceability

- **Every instruction mapped to a scorer check,** and every check to an instruction, which shows where the gaps are. See [`task-decisions.md`](../tasks/fix_syntax/task-decisions.md#spec-review).
- **Terms defined before use:** "agent" has three meanings, and the docs say which one they use. See [Inspect and the Agent](eval-architecture.md#inspect-and-the-agent).

### Decision records

- **Choices written down with reasons:** a [template](task-decisions-template.md) lists every design and run decision, and [`fix_syntax`'s copy](../tasks/fix_syntax/task-decisions.md) records each choice.

### Issue tracking

- **A QA log with IDs:** each finding has a type, severity, how it was found, the fix, and how the fix was verified. See [QA log](../tasks/fix_syntax/QA.md#qa-log).

### Root-cause debugging

- **Reproduce before fixing:** a failing dev container build was reproduced locally with the same tool and CPU architecture as Codespaces, which found the real cause. See [Troubleshooting](github-codespaces.md#troubleshooting).
- **Read the source instead of assuming:** Inspect behaviors were confirmed in its source before being documented, such as how it picks a sandbox image. See [How Inspect picks the sandbox image](eval-architecture.md#how-inspect-picks-the-sandbox-image).
- **Measure, then decide:** a slow model was timed directly, to separate its latency from the setup's, with [`scripts/check_model.sh`](../scripts/check_model.sh).

### Cost controls

- **Free testing first:** the mock model and reference solutions cost nothing. See [Cost-saving measures](safety-and-cost.md#cost-saving-measures).
- **Limits on every run:** message limits, time limits, and request timeouts.
- **Usage tracked:** token use per run and per eval.
