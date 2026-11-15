"""Passes per model across QA rounds, such as before and after a scorer fix.

Usage, from the repo root:
    uv run python src/create_visuals/make_qa_chart.py tasks/fix_syntax/qa-rounds.json -o tmp/qa.png
See README.md in this folder for the data file fields.
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from make_results_chart import model_label, new_figure
from style import GRID, SERIES, SURFACE, TEXT, TEXT_2


def qa_chart(data: dict, out_path: Path, short: bool = False):
    rounds = data['rounds']
    models = list(rounds[0]['passes'])
    if len(models) > len(SERIES):
        raise SystemExit(f'{len(models)} models but only {len(SERIES)} colors. Add a color to SERIES.')
    total = data['runs_per_model']
    plot_in, label_in = 5.2, 1.9
    width = 0.8 + plot_in + label_in
    f, height = new_figure(width, 3.6, data['title'], data.get('subtitle') or f'Passes out of {total} runs per model, by scoring round',
                           data.get('mock'))
    ax = f.add_axes([0.8 / width, 0.85 / height, plot_in / width, 2.55 / height])

    x = list(range(len(rounds)))
    close = total * 0.08  # values nearer than this would have overlapping labels
    for color, model in zip(SERIES, models):
        values = [r['passes'][model] for r in rounds]
        ax.plot(x, values, color=color, lw=2, marker='o', ms=9, mec=SURFACE, mew=2, zorder=3)

    # Value labels: the highest value at each round goes above its point. A value close below another goes
    # under its point instead, and a value equal to one already labeled isn't repeated.
    for xi, r in enumerate(rounds):
        previous = None
        for v in sorted(set(r['passes'].values()), reverse=True):
            below = previous is not None and previous - v < close
            ax.text(xi, v - total * 0.09 if below else v + total * 0.04, str(v), ha='center', fontsize=10, color=TEXT)
            previous = v

    # End labels, spread apart when the lines finish close together.
    ends = sorted(((rounds[-1]['passes'][m], m) for m in models), reverse=True)
    placed = []
    for v, model in ends:
        y = v if not placed or placed[-1] - v >= close else placed[-1] - close
        placed.append(y)
        ax.text(x[-1] + 0.12, y, model_label(model, short), va='center', fontsize=10.5, color=TEXT, clip_on=False)
    ax.set_xticks(x, [r['label'] for r in rounds])
    ax.set_xlim(-0.25, x[-1] + 0.05)
    ax.set_ylim(0, total * 1.12)
    ax.set_yticks([round(total * i / 3) for i in range(4)])
    for s in ['top', 'right', 'left']:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.yaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    if note := data.get('annotation'):
        ax.annotate(note['text'], xy=note['xy'], xytext=note['text_xy'], fontsize=9.5, color=TEXT_2,
                    arrowprops=dict(arrowstyle='-', color=TEXT_2, lw=1))
    f.savefig(out_path, dpi=160)
    plt.close(f)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('data', type=Path, help='QA rounds JSON')
    p.add_argument('--short-names', action='store_true', help='drop the provider prefix from model names')
    p.add_argument('-o', '--out', type=Path, help='output PNG (default: <data file name>.png in the current directory)')
    args = p.parse_args()
    out = args.out or Path(f'{args.data.stem}.png')
    qa_chart(json.loads(args.data.read_text()), out, args.short_names)
    print(f'Wrote {out}')
