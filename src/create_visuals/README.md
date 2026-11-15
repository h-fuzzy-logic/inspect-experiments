# create_visuals

Scripts that turn eval results into tables and charts. Each chart reads its data from a JSON file, so the same script draws mock data now and real results later.

| Script | What it does |
|---|---|
| `summarize_results.py` | Reads Inspect eval logs and writes a results file: accuracy, stderr, tokens, timing, and a pass rate for each sample |
| `make_results_chart.py` | Draws a chart from a results file: pass rate by model, a pass-rate grid by sample and model, or every run's pass or fail |
| `make_baseline_chart.py` | Draws human baseline times against model times, per sample, from a results file and a baseline file |
| `make_qa_chart.py` | Draws passes per model across QA rounds, such as before and after a scorer fix |
| `make_chart.py` | Draws faults fixed over elapsed time, for models vs the human baseline. Its data is written by hand for now |
| `style.py` | Colors, fonts, and the title block shared by all the charts |

## Setup

From the repo root, run:

```sh
uv sync
```

This installs matplotlib, which is a dev dependency, along with the rest of the project.

## Results charts, from eval logs

### 1. Summarize the logs

```sh
uv run python src/create_visuals/summarize_results.py --task fix_syntax --min-samples 8 --title "Fixing syntax errors"
```

This finds the logs in `logs/` that match, keeps the newest one for each model, and writes `results/fix_syntax.json`. It prints a line per model, such as:

```
anthropic/claude-haiku-5-5: accuracy 1.000 ± 0.000, 8 samples × 3 epochs, 0 limit hits, 90612 tokens
  verdicts: 24 fixed
```

The verdicts line counts the scorer's reason for each run's pass or fail, read from the `verdict` field in each score's metadata. Runs without one, such as runs scored before the scorer recorded verdicts, count as `not_recorded`.

| Option | What it does |
|---|---|
| `--task` | Only logs for this task |
| `--model` | Only logs for this model. Repeat it for more than one |
| `--min-samples` | Skip logs that ran fewer samples. Use it to leave out test runs made with `--limit`, or runs from an older version of the task |
| `--all` | Keep every matching log, not just the newest per model |
| `--include-mock` | Include `mockllm/` runs, which are skipped by default |
| `--log-dir` | Where to look for logs (default: `logs`) |
| `--scorer` | Which scorer to report, if the task has more than one (default: the first) |
| `--title` | The chart title saved in the results file (default: `<task> results`) |
| `-o` | Where to write the results file (default: `results/<task>.json`) |

You can also pass log files directly: `summarize_results.py logs/<file>.eval logs/<other>.eval`.

Logs are git-ignored, so the results file is what keeps the numbers. Commit it.

### 2. Draw the charts

```sh
uv run python src/create_visuals/make_results_chart.py results/fix_syntax.json --kind models -o docs/images/fix-syntax-models.png
uv run python src/create_visuals/make_results_chart.py results/fix_syntax.json --kind samples --row-label error -o docs/images/fix-syntax-samples.png
```

| `--kind` | Chart |
|---|---|
| `models` | One bar per model: its pass rate, with a 95% confidence interval (±1.96 × stderr) |
| `samples` | A grid with one row per sample and one column per model. Each cell is the share of that sample's epochs that passed |
| `runs` | Every run: one ✓/✗ cell per sample and epoch, in a block per model, with a pass count. `L` marks a failed run that a limit stopped |

| Option | What it does |
|---|---|
| `--model` | Only these models, in this order. Repeat it for more than one |
| `--short-names` | Drop the provider prefix, so `anthropic/claude-haiku-5-5` shows as `claude-haiku-5-5` |
| `--row-label` | Samples chart: label rows with a sample metadata field instead of the sample ID. For `fix_syntax`, `error` shows the error type |
| `--title`, `--subtitle` | Override the title from the results file, or the subtitle the script writes to describe the chart |
| `-o` | Output PNG (default: `<results file name>-<kind>.png` in the current directory) |

### Try it with mock data

`data/mock-results-fix-syntax.json` is a results file with made-up numbers for three models. It has `"mock": true`, so its charts carry a MOCK DATA badge:

```sh
uv run python src/create_visuals/make_results_chart.py src/create_visuals/data/mock-results-fix-syntax.json --kind models --short-names -o tmp/mock-models.png
uv run python src/create_visuals/make_results_chart.py src/create_visuals/data/mock-results-fix-syntax.json --kind samples --short-names --row-label error -o tmp/mock-samples.png
```

### Results file fields

| Field | What it holds |
|---|---|
| `title` | The chart title |
| `mock` | `true` shows the MOCK DATA badge |
| `generated` | When the file was written |
| `models` | One entry per log. See below |

Each entry in `models`:

| Field | What it holds |
|---|---|
| `model`, `task`, `log`, `created`, `scorer` | Which run this is |
| `samples`, `epochs`, `scored_runs` | Distinct samples, epochs per sample, and their product |
| `accuracy`, `stderr` | The task's overall metrics, as Inspect reported them |
| `limit_hits`, `errors` | Runs stopped by a limit, and runs that errored. A run that errored counts as a fail |
| `verdicts` | How many runs got each verdict, most common first, such as `{"fixed": 22, "rewritten": 1, "still_broken": 1}`. Runs without a verdict count as `not_recorded` |
| `mean_messages`, `mean_seconds_per_run`, `duration_seconds` | Average conversation length and run time, and the whole eval's wall-clock time |
| `tokens` | Token use: `input`, `output`, `cache_write`, `cache_read`, `reasoning`, and `total` |
| `per_sample` | For each sample ID: `pass_rate` across its epochs, `runs`, `epochs` (each run's `epoch`, `score`, `verdict`, `limit`, `error`, and `seconds`), and the sample's `metadata` |

## Human baseline chart

```sh
uv run python src/create_visuals/make_baseline_chart.py tasks/fix_syntax/results/results.json \
  tasks/fix_syntax/results/mock-human-baseline.json --row-label error -o tmp/baseline.png
```

Each row is a sample. It shows the human's measured time (square), the human's estimate (tick), and each model's median time per run (circle, hollow if the model never passed that sample). Model times come from the results file. Human times come from a baseline file:

| Field | What it holds |
|---|---|
| `mock` | `true` shows the MOCK DATA badge |
| `samples` | For each sample ID: `estimate_minutes` and `measured_minutes` |
| `subtitle` | Optional. Replaces the default subtitle |

The chart has three model colors. With more models, choose up to three with `--model`.

## QA rounds chart

```sh
uv run python src/create_visuals/make_qa_chart.py tasks/fix_syntax/results/mock-qa-rounds.json --short-names -o tmp/qa.png
```

One line per model, showing its passes in each scoring round. Use it to show how much a scorer or task fix changed the numbers. The data file fields:

| Field | What it holds |
|---|---|
| `title`, `mock` | The chart title, and whether to show the MOCK DATA badge |
| `runs_per_model` | The top of the y-axis |
| `rounds` | One entry per round: a `label` (use `\n` for a second line) and `passes`, a count for each model |
| `annotation` | Optional. A note with a line pointing to a spot: `text`, `xy`, and `text_xy` |
| `subtitle` | Optional. Replaces the default subtitle |

### Tests

```sh
uv run pytest src/create_visuals/tests
```

The tests check score conversion, render every chart type from the mock data, and run `fix_syntax` with the mock model to make real logs, then check the summary of them. That last test needs Docker and is skipped without it.

## Progress chart, written by hand

`make_chart.py` draws faults fixed over elapsed time. Its data isn't read from logs yet, so you write the JSON yourself.

### Make a mock chart

```sh
uv run python src/create_visuals/make_chart.py src/create_visuals/data/mock-progress-over-time.json
```

This saves `mock-progress-over-time.png` in the current directory. To update the image the main README shows, write it to `docs/images` instead:

```sh
uv run python src/create_visuals/make_chart.py src/create_visuals/data/mock-progress-over-time.json \
  -o docs/images/mock-progress-over-time.png
```

### Make a chart from real results

1. **Copy the mock file** to a new name that doesn't start with `mock-`, such as `data/progress-over-time-v1.json`.
2. **Fill in your results.** Copy the numbers from `inspect view` or your notes. See the fields below.
3. **Set `"mock": false`.** This removes the red MOCK DATA badge.
4. **Run the script** on the new file:

   ```sh
   uv run python src/create_visuals/make_chart.py src/create_visuals/data/progress-over-time-v1.json \
     -o docs/images/progress-over-time-v1.png
   ```

5. **Update the main README** to point to the new image, and change its caption if the results tell a different story.

### Data file fields

| Field | What it sets |
|---|---|
| `title`, `subtitle` | The text above the chart. |
| `mock` | `true` shows the MOCK DATA badge. Use `false` for real results. |
| `total_faults` | The top of the y-axis, the number of faults in the task. |
| `max_hours` | The right edge of the x-axis, in hours. |
| `series` | One entry per line: `name`, `hours`, and `faults`. `hours` and `faults` are paired lists: the time of each step and the faults fixed by then. Add `"baseline": true` to the human baseline to draw it as a black dashed line. |
| `annotation` | Optional. A note with a line pointing to a spot on the chart: `text`, `xy` (the point, in hours and faults), and `text_xy` (where the text goes). Leave it out when there's nothing to point at. |

Models are drawn in blue, orange, then aqua, in the order they're listed. The script stops with an error if there are more than three models. To add a fourth, add the next color from the palette to `SERIES` in `style.py`, and check it with the colorblind-safety validator.
