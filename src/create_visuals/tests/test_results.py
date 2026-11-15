"""Tests for summarize_results.py and make_results_chart.py.

Run from the repo root:
    uv run pytest src/create_visuals/tests
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from inspect_ai import eval

VISUALS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VISUALS_DIR))

import make_baseline_chart  # noqa: E402
import make_qa_chart  # noqa: E402
import make_results_chart  # noqa: E402
import summarize_results  # noqa: E402

MOCK_RESULTS = VISUALS_DIR / 'data' / 'mock-results-fix-syntax.json'
FIX_SYNTAX_DIR = VISUALS_DIR.parents[1] / 'tasks' / 'fix_syntax'
FIX_SYNTAX = FIX_SYNTAX_DIR / 'fix_syntax.py'


def docker_running() -> bool:
    if shutil.which('docker') is None:
        return False
    return subprocess.run(['docker', 'info'], capture_output=True).returncode == 0


@pytest.mark.parametrize('value, expected', [('C', 1.0), ('I', 0.0), ('P', 0.5), ('N', 0.0), (True, 1.0), (0.25, 0.25)])
def test_score_to_float(value, expected):
    assert summarize_results.score_to_float(value) == expected


def test_score_to_float_rejects_unknown_values():
    with pytest.raises(ValueError):
        summarize_results.score_to_float('X')


@pytest.mark.parametrize('kind', ['models', 'samples', 'runs'])
def test_charts_render_from_mock_results(tmp_path, kind):
    data = json.loads(MOCK_RESULTS.read_text())
    data['subtitle'] = make_results_chart.default_subtitle(data, kind)
    out = tmp_path / f'{kind}.png'
    if kind == 'models':
        make_results_chart.models_chart(data, out)
    elif kind == 'runs':
        make_results_chart.runs_chart(data, out, row_label='error')
    else:
        make_results_chart.samples_chart(data, out, row_label='error')
    assert out.stat().st_size > 10_000


def test_runs_chart_needs_per_epoch_results(tmp_path):
    data = json.loads(MOCK_RESULTS.read_text())
    data['subtitle'] = 'test'
    for sample in data['models'][0]['per_sample'].values():
        del sample['epochs']
    with pytest.raises(SystemExit):
        make_results_chart.runs_chart(data, tmp_path / 'runs.png')


def test_baseline_and_qa_charts_render(tmp_path):
    results = json.loads(MOCK_RESULTS.read_text())
    baseline = json.loads((FIX_SYNTAX_DIR / 'results' / 'mock-human-baseline.json').read_text())
    # The mock results have no timings, so give each run one, in seconds.
    for m in results['models']:
        for sample in m['per_sample'].values():
            for run in sample['epochs']:
                run['seconds'] = 30
    make_baseline_chart.baseline_chart(results, baseline, tmp_path / 'baseline.png', row_label='error')
    make_qa_chart.qa_chart(json.loads((FIX_SYNTAX_DIR / 'results' / 'mock-qa-rounds.json').read_text()), tmp_path / 'qa.png')
    assert (tmp_path / 'baseline.png').stat().st_size > 10_000
    assert (tmp_path / 'qa.png').stat().st_size > 10_000


@pytest.mark.skipif(not docker_running(), reason="Docker isn't running")
def test_summarize_real_logs(tmp_path):
    # Make two real logs with the mock model: every sample fixed, then every sample left broken.
    for solution in ['reference', 'none']:
        eval(os.path.relpath(FIX_SYNTAX), model='mockllm/model', task_args={'solution': solution},
             display='none', log_dir=str(tmp_path))

    # mockllm runs are skipped by default.
    assert summarize_results.find_logs(tmp_path, task='fix_syntax') == []

    paths = summarize_results.find_logs(tmp_path, task='fix_syntax', include_mock=True, latest_only=False)
    results = summarize_results.summarize(paths, 'test')
    by_accuracy = sorted(results['models'], key=lambda m: m['accuracy'])
    assert [m['accuracy'] for m in by_accuracy] == [0.0, 1.0]
    # The scorer's recorded reasons: every broken script still errors, and every reference fix is fixed.
    assert [m['verdicts'] for m in by_accuracy] == [{'still_broken': 8}, {'fixed': 8}]
    for m in by_accuracy:
        assert m['samples'] == 8 and m['epochs'] == 1 and m['scored_runs'] == 8
        assert {s['pass_rate'] for s in m['per_sample'].values()} == {m['accuracy']}
        assert all('error' in s['metadata'] for s in m['per_sample'].values())
        for s in m['per_sample'].values():
            [run] = s['epochs']
            assert run['epoch'] == 1 and run['score'] == m['accuracy'] and run['limit'] is None
            assert run['verdict'] == ('fixed' if m['accuracy'] else 'still_broken')
            assert run['seconds'] is not None

    # With latest_only, the two mockllm logs collapse to the newer one.
    assert len(summarize_results.find_logs(tmp_path, task='fix_syntax', include_mock=True)) == 1
