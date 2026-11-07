# create_visuals

Scripts that turn eval results into the charts in the main README. Each chart reads its data from a JSON file, so the same script draws mock data now and real results later.

So far there's one chart:

- `make_chart.py`: faults fixed over elapsed time, for models vs the human baseline. Its mock data is in `data/mock-progress-over-time.json`.

## Setup

From the repo root, run:

```sh
uv sync
```

This installs matplotlib, which is a dev dependency, along with the rest of the project.

## Make a mock chart

From the repo root, run:

```sh
uv run python src/create_visuals/make_chart.py src/create_visuals/data/mock-progress-over-time.json
```

This saves `mock-progress-over-time.png` in the current directory. To update the image the main README shows, write it to `docs/images` instead:

```sh
uv run python src/create_visuals/make_chart.py src/create_visuals/data/mock-progress-over-time.json \
  -o docs/images/mock-progress-over-time.png
```

## Make a chart from real results

1. **Copy the mock file** to a new name that doesn't start with `mock-`, such as `data/progress-over-time-v1.json`.
2. **Fill in your results.** Nothing reads them from the eval logs yet, so copy the numbers from `inspect view` or your notes. See the fields below.
3. **Set `"mock": false`.** This removes the red MOCK DATA badge.
4. **Run the script** on the new file:

   ```sh
   uv run python src/create_visuals/make_chart.py src/create_visuals/data/progress-over-time-v1.json \
     -o docs/images/progress-over-time-v1.png
   ```

5. **Update the main README** to point to the new image, and change its caption if the results tell a different story.

## Data file fields

| Field | What it sets |
|---|---|
| `title`, `subtitle` | The text above the chart. |
| `mock` | `true` shows the MOCK DATA badge. Use `false` for real results. |
| `total_faults` | The top of the y-axis, the number of faults in the task. |
| `max_hours` | The right edge of the x-axis, in hours. |
| `series` | One entry per line: `name`, `hours`, and `faults`. `hours` and `faults` are paired lists: the time of each step and the faults fixed by then. Add `"baseline": true` to the human baseline to draw it as a black dashed line. |
| `annotation` | Optional. A note with a line pointing to a spot on the chart: `text`, `xy` (the point, in hours and faults), and `text_xy` (where the text goes). Leave it out when there's nothing to point at. |

Models are drawn in blue, then orange, in the order they're listed. The script stops with an error if there are more than two models. To add a third, add a color to `MODEL_COLORS` in `make_chart.py`.
