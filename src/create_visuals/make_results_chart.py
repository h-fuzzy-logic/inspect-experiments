"""Charts from a results file made by summarize_results.py.

Usage, from the repo root:
    uv run python src/create_visuals/make_results_chart.py results/fix_syntax.json --kind models -o tmp/models.png
    uv run python src/create_visuals/make_results_chart.py results/fix_syntax.json --kind samples -o tmp/samples.png
See README.md in this folder for the options.
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import Rectangle

from style import BLUE_RAMP, GRID, MISSING, RUN_FAIL, RUN_LIMIT, RUN_PASS, SERIES, SURFACE, TEXT, TEXT_2, header

# Height reserved at the top of each figure for the title and subtitle, in inches.
HEADER_IN = 0.95
# Light to mid-dark: stopping short of the darkest steps keeps a mostly-100% grid from reading as solid navy.
PASS_RATE_CMAP = LinearSegmentedColormap.from_list('pass_rate', BLUE_RAMP[:5])


def default_subtitle(data: dict, kind: str) -> str:
    """A subtitle describing the chart, from the first model's sample and epoch counts."""
    first = data['models'][0]
    runs = f"{first['samples']} samples × {first['epochs']} epochs"
    if kind == 'models':
        return f'Pass rate by model, {runs}, with 95% confidence intervals'
    if kind == 'runs':
        return f'Every run: one cell per sample and epoch, {runs} per model'
    return f"Share of each sample's {first['epochs']} epochs that passed, by model"


def model_label(model: str, short: bool) -> str:
    """'anthropic/claude-haiku-5-5' becomes 'claude-haiku-5-5' when short."""
    return model.split('/', 1)[-1] if short else model


def ink_for(fill: str) -> str:
    """Dark text on light fills, light text on dark fills."""
    r, g, b = to_rgb(fill)
    return TEXT if (0.2126 * r + 0.7152 * g + 0.0722 * b) > 0.5 else SURFACE


def new_figure(width: float, plot_height: float, title: str, subtitle: str, mock: bool):
    """A figure with room for the header above a plot of the given height, in inches."""
    height = plot_height + HEADER_IN
    f = plt.figure(figsize=(width, height))
    header(f, title, subtitle, mock, title_y=1 - 0.25 / height, subtitle_y=1 - 0.58 / height)
    return f, height


def models_chart(data: dict, out_path: Path, short: bool = False):
    """Horizontal bars: each model's pass rate, with a 95% confidence interval."""
    models = data['models']
    n = len(models)
    names = [model_label(m['model'], short) for m in models]
    label_in = 0.35 + 0.095 * max(len(s) for s in names)  # room for model names, in inches
    plot_in, value_in = 4.4, 1.3  # bar area, and room for the value labels to its right
    width = label_in + plot_in + value_in
    f, height = new_figure(width, 0.9 + 0.55 * n, data['title'], data['subtitle'], data.get('mock'))
    ax = f.add_axes([label_in / width, 0.55 / height, plot_in / width, (0.55 * n + 0.1) / height])

    y = list(range(n))[::-1]  # first model on top
    for yi, m in zip(y, models):
        acc = m['accuracy']
        ci = 1.96 * (m.get('stderr') or 0)
        lo, hi = max(0.0, acc - ci), min(1.0, acc + ci)
        ax.barh(yi, acc, height=0.5, color=SERIES[0], zorder=2)
        if ci:
            ax.errorbar(acc, yi, xerr=[[acc - lo], [hi - acc]], fmt='none', ecolor=TEXT_2, elinewidth=1.5, capsize=4, zorder=3)
        label = f'{acc:.0%}' + (f' ± {ci:.0%}' if ci else '')
        ax.text(hi + 0.02, yi, label, va='center', fontsize=10.5, color=TEXT, clip_on=False)

    ax.set_yticks(y, names, color=TEXT)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ['0%', '25%', '50%', '75%', '100%'])
    ax.set_xlabel('Pass rate')
    for s in ['top', 'right', 'left']:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    f.savefig(out_path, dpi=160)
    plt.close(f)


def samples_chart(data: dict, out_path: Path, short: bool = False, row_label: str | None = None):
    """A grid of pass rates: one row per sample, one column per model."""
    models = data['models']
    rows, labels = sample_rows(models, row_label)
    n_rows, n_cols = len(rows), len(models)
    names = [model_label(m['model'], short) for m in models]
    label_in = 0.35 + 0.095 * max(len(s) for s in labels)  # room for row labels, in inches
    col_in = max(1.5, 0.3 + 0.095 * max(len(s) for s in names))  # each column fits its model name
    width = label_in + col_in * n_cols + 0.4
    f, height = new_figure(width, 0.75 + 0.4 * n_rows, data['title'], data['subtitle'], data.get('mock'))
    ax = f.add_axes([label_in / width, 0.15 / height, col_in * n_cols / width, 0.4 * n_rows / height])

    gap = 0.04  # leaves a thin surface-colored gap between cells
    for c, m in enumerate(models):
        for r, sid in enumerate(rows):
            entry = m['per_sample'].get(sid)
            fill = PASS_RATE_CMAP(entry['pass_rate']) if entry else MISSING
            fill_hex = '#%02x%02x%02x' % tuple(int(v * 255) for v in to_rgb(fill))
            ax.add_patch(Rectangle((c + gap, r + gap), 1 - 2 * gap, 1 - 2 * gap, facecolor=fill_hex, edgecolor='none'))
            text = f"{entry['pass_rate']:.0%}" if entry else '–'
            ax.text(c + 0.5, r + 0.5, text, ha='center', va='center', fontsize=10, color=ink_for(fill_hex) if entry else TEXT_2)

    ax.set_xlim(0, n_cols)
    ax.set_ylim(n_rows, 0)  # first sample on top
    ax.set_yticks([r + 0.5 for r in range(n_rows)], labels, color=TEXT)
    ax.set_xticks([c + 0.5 for c in range(n_cols)], names, color=TEXT)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    f.savefig(out_path, dpi=160)
    plt.close(f)


def sample_rows(models: list[dict], row_label: str | None) -> tuple[list[str], list[str]]:
    """Sample IDs in first-seen order, and the label to show for each."""
    rows = []
    for m in models:
        rows += [sid for sid in m['per_sample'] if sid not in rows]

    def row_name(sid):
        for m in models:
            meta = m['per_sample'].get(sid, {}).get('metadata', {})
            if row_label and row_label in meta:
                return str(meta[row_label])
        return sid

    return rows, [row_name(sid) for sid in rows]


def runs_chart(data: dict, out_path: Path, short: bool = False, row_label: str | None = None):
    """Every run: a pass/fail cell for each sample and epoch, one block of columns per model."""
    models = data['models']
    for m in models:
        if any('epochs' not in s for s in m['per_sample'].values()):
            raise SystemExit(f"No per-epoch results for {m['model']}. Re-run summarize_results.py to add them.")
    rows, labels = sample_rows(models, row_label)
    n_epochs = max(m['epochs'] for m in models)
    n_rows = len(rows)

    # Each model gets a block of columns: its epochs, then its pass count. A gap column separates blocks.
    names = [model_label(m['model'], short) for m in models]
    cell_in = 0.45
    block = max(n_epochs + 1.4, 0.095 * max(len(n) + 8 for n in names) / cell_in)  # wide enough for the block header
    n_cols = block * len(models) + 0.6 * (len(models) - 1)
    label_in = 0.35 + 0.095 * max(len(s) for s in labels)
    width = label_in + cell_in * n_cols + 0.3
    f, height = new_figure(width, 1.45 + 0.4 * n_rows, data['title'], data['subtitle'], data.get('mock'))
    ax = f.add_axes([label_in / width, 0.65 / height, cell_in * n_cols / width, 0.4 * n_rows / height])

    # Outcome: symbol, fill, and legend label. Partial credit only appears in the legend if a run has it.
    cell_style = {'pass': ('✓', RUN_PASS, 'Pass ✓'), 'fail': ('✗', RUN_FAIL, 'Fail ✗'),
                  'limit': ('L', RUN_LIMIT, 'Time limit L'), 'partial': ('½', BLUE_RAMP[1], 'Partial credit ½')}
    used = set()
    gap = 0.06
    for mi, (m, name) in enumerate(zip(models, names)):
        x0 = mi * (block + 0.6)
        passed = sum(e['score'] for s in m['per_sample'].values() for e in s['epochs'])
        total = sum(len(s['epochs']) for s in m['per_sample'].values())
        ax.text(x0 + (n_epochs + 1.4) / 2, -0.75, f'{name} · {passed:g}/{total}', ha='center', va='bottom',
                fontsize=10.5, fontweight='bold', color=TEXT)
        for e in range(n_epochs):
            ax.text(x0 + e + 0.5, -0.12, f'e{e + 1}', ha='center', va='bottom', fontsize=9.5, color=TEXT_2)
        ax.text(x0 + n_epochs + 0.7, -0.12, 'passed', ha='center', va='bottom', fontsize=9, color=TEXT_2)
        for r, sid in enumerate(rows):
            sample = m['per_sample'].get(sid)
            runs = {e['epoch']: e for e in sample['epochs']} if sample else {}
            for e in range(n_epochs):
                run = runs.get(e + 1)
                if run is None:
                    symbol, fill, ink = '–', MISSING, TEXT_2
                else:
                    outcome = ('pass' if run['score'] >= 1 else 'limit' if run['limit']
                               else 'partial' if run['score'] > 0 else 'fail')
                    used.add(outcome)
                    symbol, fill, _ = cell_style[outcome]
                    ink = ink_for(fill)
                ax.add_patch(Rectangle((x0 + e + gap, r + gap), 1 - 2 * gap, 1 - 2 * gap, facecolor=fill, edgecolor='none'))
                ax.text(x0 + e + 0.5, r + 0.5, symbol, ha='center', va='center', fontsize=12, fontweight='bold', color=ink)
            count = f"{sum(run['score'] for run in runs.values()):g}/{len(runs)}" if runs else '–'
            ax.text(x0 + n_epochs + 0.7, r + 0.5, count, ha='center', va='center', fontsize=10, color=TEXT)

    ax.set_xlim(0, n_cols)
    ax.set_ylim(n_rows, 0)
    ax.set_yticks([r + 0.5 for r in range(n_rows)], labels, color=TEXT)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    shown = ['pass', 'fail', 'limit'] + (['partial'] if 'partial' in used else [])
    ax.legend([Rectangle((0, 0), 1, 1, facecolor=cell_style[k][1]) for k in shown], [cell_style[k][2] for k in shown],
              ncol=len(shown), frameon=False, loc='upper left', bbox_to_anchor=(-label_in / (cell_in * n_cols), -0.04),
              fontsize=9.5, labelcolor=TEXT, handlelength=1.2)
    f.savefig(out_path, dpi=160)
    plt.close(f)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('data', type=Path, help='results JSON from summarize_results.py')
    p.add_argument('--kind', choices=['models', 'samples', 'runs'], default='models',
                   help='models: pass rate by model with 95%% CI. samples: pass rate grid by sample and model. '
                        'runs: pass/fail for every sample and epoch')
    p.add_argument('--model', action='append', dest='models', help='only these models, in this order (repeat for more than one)')
    p.add_argument('--short-names', action='store_true', help='drop the provider prefix from model names')
    p.add_argument('--row-label', help='samples chart: label rows with this sample metadata field, such as error')
    p.add_argument('--title', help='override the title in the results file')
    p.add_argument('--subtitle', help='override the subtitle, which otherwise describes the chart')
    p.add_argument('-o', '--out', type=Path, help='output PNG (default: <results file name>-<kind>.png in the current directory)')
    args = p.parse_args()

    data = json.loads(args.data.read_text())
    if args.models:
        by_name = {m['model']: m for m in data['models']}
        missing = [name for name in args.models if name not in by_name]
        if missing:
            raise SystemExit(f'Not in the results file: {", ".join(missing)}')
        data['models'] = [by_name[name] for name in args.models]
    data['title'] = args.title or data['title']
    data['subtitle'] = args.subtitle or default_subtitle(data, args.kind)
    out = args.out or Path(f'{args.data.stem}-{args.kind}.png')
    if args.kind == 'models':
        models_chart(data, out, args.short_names)
    elif args.kind == 'runs':
        runs_chart(data, out, args.short_names, args.row_label)
    else:
        samples_chart(data, out, args.short_names, args.row_label)
    print(f'Wrote {out}')
