"""Faults fixed over elapsed time, for models vs the human baseline.

Usage, from the repo root:
    uv run python src/create_visuals/make_chart.py src/create_visuals/data/mock-progress-over-time.json
    uv run python src/create_visuals/make_chart.py src/create_visuals/data/mock-progress-over-time.json -o tmp/out.png
See README.md in this folder for the data file fields.
"""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from style import GRID as GR, SERIES as MODEL_COLORS, TEXT as T1, TEXT_2 as T2, header


def make_chart(data, out_path):
    f,ax=plt.subplots(figsize=(8,4.6));f.subplots_adjust(top=0.78,bottom=0.14,left=0.1,right=0.78)
    header(f,data['title'],data['subtitle'],data.get('mock'))
    for s in ['top','right','left']: ax.spines[s].set_visible(False)
    ax.tick_params(length=0);ax.yaxis.grid(True,color=GR,lw=1);ax.set_axisbelow(True)

    total,max_h=data['total_faults'],data['max_hours']
    models=[s for s in data['series'] if not s.get('baseline')]
    if len(models)>len(MODEL_COLORS):
        raise ValueError(f'{len(models)} models but only {len(MODEL_COLORS)} colors; add one to MODEL_COLORS')
    colors=iter(MODEL_COLORS)
    for s in data['series']:
        c,ls,z=(T1,(0,(5,2)),5) if s.get('baseline') else (next(colors),'-',3)
        ax.step(s['hours'],s['faults'],where='post',color=c,lw=2,ls=ls,zorder=z)
        ax.text(max_h+0.1,s['faults'][-1],s['name'],color=T1,va='center',fontsize=10.5)
    ax.set_xlim(0,max_h);ax.set_ylim(-0.2,total+0.4);ax.set_yticks(range(total+1))
    hours=range(int(max_h)+1)
    ax.set_xticks(hours,[f'{h} h' for h in hours])
    ax.set_xlabel('Elapsed time');ax.set_ylabel('Faults fixed')
    if note:=data.get('annotation'):
        ax.annotate(note['text'],xy=note['xy'],xytext=note['text_xy'],fontsize=9.5,color=T2,
                    arrowprops=dict(arrowstyle='-',color=T2,lw=1))
    f.savefig(out_path,dpi=160)
    plt.close(f)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('data',type=Path,help='JSON file with the chart data')
    p.add_argument('-o','--out',type=Path,help='output PNG (default: <data file name>.png in the current directory)')
    args=p.parse_args()
    make_chart(json.loads(args.data.read_text()),args.out or Path(args.data.stem+'.png'))
