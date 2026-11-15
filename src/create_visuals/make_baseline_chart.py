"""Human baseline vs model time, per sample.

Usage, from the repo root:
    uv run python src/create_visuals/make_baseline_chart.py results/fix_syntax.json tasks/fix_syntax/human-baseline.json -o tmp/baseline.png
See README.md in this folder for the baseline file fields.
"""
import argparse
import json
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from make_results_chart import model_label, new_figure
from style import GRID, SERIES, SURFACE, TEXT, TEXT_2


def model_minutes(sample: dict) -> float | None:
    """Median minutes per run for one sample, or None if the results have no timings."""
    seconds = [e['seconds'] for e in sample.get('epochs', []) if e.get('seconds') is not None]
    return median(seconds) / 60 if seconds else None


def baseline_chart(results: dict, baseline: dict, out_path: Path, short: bool = False, row_label: str | None = None):
    models = results['models']
    if len(models) > len(SERIES):
        raise SystemExit(f'{len(models)} models but only {len(SERIES)} colors. Pick models with --model, or add a color to SERIES.')
    rows = list(baseline['samples'])

    def row_name(sid):
        for m in models:
            meta = m['per_sample'].get(sid, {}).get('metadata', {})
            if row_label and row_label in meta:
                return str(meta[row_label])
        return sid

    labels = [row_name(sid) for sid in rows]
    label_in = 0.35 + 0.095 * max(len(s) for s in labels)
    plot_in = 6.0
    width = label_in + plot_in + 0.4
    f, height = new_figure(width, 1.3 + 0.42 * len(rows), results['title'], baseline.get('subtitle') or
                           'Minutes per sample: human baseline vs median model time per run',
                           results.get('mock') or baseline.get('mock'))
    ax = f.add_axes([label_in / width, 0.85 / height, plot_in / width, 0.42 * len(rows) / height])

    x_max = 0
    for r, sid in enumerate(rows):
        b = baseline['samples'][sid]
        points = [b.get('measured_minutes'), b.get('estimate_minutes')]
        for m in models:
            points.append(model_minutes(m['per_sample'].get(sid, {})))
        points = [p for p in points if p is not None]
        if not points:
            continue
        x_max = max(x_max, *points)
        ax.plot([min(points), max(points)], [r, r], color=GRID, lw=2, zorder=1)
        if b.get('estimate_minutes') is not None:
            ax.plot(b['estimate_minutes'], r, marker='|', ms=12, mew=2, color=TEXT_2, zorder=2)
        if b.get('measured_minutes') is not None:
            ax.plot(b['measured_minutes'], r, marker='s', ms=9, color=TEXT, mec=SURFACE, mew=1.5, zorder=3)
        for color, m in zip(SERIES, models):
            sample = m['per_sample'].get(sid)
            minutes = model_minutes(sample or {})
            if minutes is None:
                continue
            never_passed = sample['pass_rate'] == 0
            ax.plot(minutes, r, marker='o', ms=9, mfc=SURFACE if never_passed else color, mec=color, mew=2, zorder=4)

    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_yticks(range(len(rows)), labels, color=TEXT)
    ax.set_xlim(0, x_max * 1.08 if x_max else 1)
    ax.set_xlabel('Minutes')
    for s in ['top', 'right', 'left']:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.xaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)

    handles = [Line2D([], [], marker='s', ls='', color=TEXT, ms=8), Line2D([], [], marker='|', ls='', color=TEXT_2, mew=2, ms=11)]
    names = ['Human, measured', 'Human, estimated']
    for color, m in zip(SERIES, models):
        handles.append(Line2D([], [], marker='o', ls='', color=color, ms=8))
        names.append(model_label(m['model'], short))
    handles.append(Line2D([], [], marker='o', ls='', mfc=SURFACE, mec=TEXT_2, mew=2, ms=8))
    names.append('Hollow: never passed')
    ax.legend(handles, names, ncol=3, frameon=False, loc='upper left', bbox_to_anchor=(-label_in / plot_in, -0.1),
              fontsize=9.5, labelcolor=TEXT, handletextpad=0.3, columnspacing=1.2)
    f.savefig(out_path, dpi=160)
    plt.close(f)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('results', type=Path, help='results JSON from summarize_results.py')
    p.add_argument('baseline', type=Path, help='human baseline JSON, one entry per sample')
    p.add_argument('--model', action='append', dest='models', help='only these models, in this order (repeat for more than one)')
    p.add_argument('--short-names', action='store_true', help='drop the provider prefix from model names')
    p.add_argument('--row-label', help='label rows with this sample metadata field, such as error')
    p.add_argument('-o', '--out', type=Path, help='output PNG (default: <baseline file name>.png in the current directory)')
    args = p.parse_args()

    results = json.loads(args.results.read_text())
    if args.models:
        by_name = {m['model']: m for m in results['models']}
        results['models'] = [by_name[name] for name in args.models]
    out = args.out or Path(f'{args.baseline.stem}.png')
    baseline_chart(results, json.loads(args.baseline.read_text()), out, args.short_names, args.row_label)
    print(f'Wrote {out}')
