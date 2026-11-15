"""Summarize Inspect eval logs into a results file for tables and charts.

Usage, from the repo root:
    uv run python src/create_visuals/summarize_results.py --task fix_syntax
    uv run python src/create_visuals/summarize_results.py --task fix_syntax --model anthropic/claude-haiku-5-5 -o tmp/haiku.json
See README.md in this folder for the options and the output format.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from inspect_ai.log import EvalLog, read_eval_log

# How Inspect's letter scores count toward a pass rate.
SCORE_VALUES = {'C': 1.0, 'I': 0.0, 'P': 0.5, 'N': 0.0}

# Score metadata field that holds the scorer's reason for a pass or fail, such as fix_syntax's Verdict.
VERDICT_KEY = 'verdict'
# Counted in place of a verdict for runs without one: unscored runs, or logs from before the scorer recorded verdicts.
NO_VERDICT = 'not_recorded'


def score_to_float(value) -> float:
    """Turn a score value (C/I/P/N, a bool, or a number) into a pass rate between 0 and 1."""
    if isinstance(value, (bool, int, float)):
        return float(value)
    if value in SCORE_VALUES:
        return SCORE_VALUES[value]
    raise ValueError(f'Unknown score value: {value!r}')


def sample_count(log: EvalLog) -> int:
    """Number of distinct samples run, not counting epochs."""
    epochs = log.eval.config.epochs or 1
    return (log.results.total_samples // epochs) if log.results else 0


def find_logs(log_dir: Path, task: str | None = None, models: list[str] | None = None,
              include_mock: bool = False, min_samples: int = 1, latest_only: bool = True) -> list[Path]:
    """Find finished logs that match the filters. With latest_only, keep the newest log for each model."""
    matches = []
    # Log file names start with a timestamp, so sorting by name sorts by time.
    for path in sorted(log_dir.glob('*.eval')):
        log = read_eval_log(str(path), header_only=True)
        if log.status != 'success' or not log.results:
            continue
        if task and log.eval.task != task:
            continue
        if models and log.eval.model not in models:
            continue
        if not include_mock and log.eval.model.startswith('mockllm/'):
            continue
        if sample_count(log) < min_samples:
            continue
        matches.append((path, log.eval.model))
    if latest_only:
        return list({model: path for path, model in matches}.values())
    return [path for path, _ in matches]


def summarize_log(path: Path, scorer: str | None = None) -> dict:
    """Summarize one log: overall metrics, token use, timing, and a pass rate for each sample."""
    log = read_eval_log(str(path))
    score = next(s for s in log.results.scores if scorer in (None, s.name))
    samples = log.samples or []

    per_sample = {}
    verdicts = Counter()
    for s in sorted(samples, key=lambda s: s.epoch):
        entry = per_sample.setdefault(str(s.id), {'metadata': s.metadata or {}, 'values': [], 'epochs': []})
        sample_score = (s.scores or {}).get(score.name)
        # A run that was never scored, such as one that errored, counts as a fail.
        value = score_to_float(sample_score.value) if sample_score else 0.0
        verdict = ((sample_score.metadata or {}).get(VERDICT_KEY) if sample_score else None) or NO_VERDICT
        verdicts[verdict] += 1
        entry['values'].append(value)
        entry['epochs'].append({'epoch': s.epoch, 'score': value, 'verdict': verdict,
                                'limit': s.limit.type if s.limit else None, 'error': bool(s.error),
                                'seconds': s.total_time})

    usage = log.stats.model_usage.get(log.eval.model)
    started = datetime.fromisoformat(log.stats.started_at)
    completed = datetime.fromisoformat(log.stats.completed_at)
    times = [s.total_time for s in samples if s.total_time is not None]
    metrics = score.metrics

    return {
        'model': log.eval.model,
        'task': log.eval.task,
        'log': path.name,
        'created': log.eval.created,
        'scorer': score.name,
        'samples': len(per_sample),
        'epochs': log.eval.config.epochs or 1,
        'scored_runs': len(samples),
        'accuracy': metrics['accuracy'].value if 'accuracy' in metrics else None,
        'stderr': metrics['stderr'].value if 'stderr' in metrics else None,
        'limit_hits': sum(1 for s in samples if s.limit),
        'errors': sum(1 for s in samples if s.error),
        'verdicts': dict(verdicts.most_common()),
        'mean_messages': round(mean(len(s.messages) for s in samples), 1) if samples else None,
        'mean_seconds_per_run': round(mean(times), 1) if times else None,
        'duration_seconds': round((completed - started).total_seconds(), 1),
        'tokens': {
            'input': usage.input_tokens if usage else None,
            'output': usage.output_tokens if usage else None,
            'cache_write': usage.input_tokens_cache_write if usage else None,
            'cache_read': usage.input_tokens_cache_read if usage else None,
            'reasoning': usage.reasoning_tokens if usage else None,
            'total': usage.total_tokens if usage else None,
        },
        'per_sample': {
            sample_id: {'pass_rate': round(mean(e['values']), 3), 'runs': len(e['values']), 'epochs': e['epochs'],
                        'metadata': e['metadata']}
            for sample_id, e in per_sample.items()
        },
    }


def summarize(paths: list[Path], title: str, mock: bool = False, scorer: str | None = None) -> dict:
    """Combine several logs into one results file, one entry per log."""
    return {
        'title': title,
        'mock': mock,
        'generated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'models': [summarize_log(p, scorer) for p in paths],
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('logs', nargs='*', type=Path, help='specific .eval files to summarize (default: search --log-dir)')
    p.add_argument('--log-dir', type=Path, default=Path('logs'), help='folder to search for logs (default: logs)')
    p.add_argument('--task', help='only logs for this task, such as fix_syntax')
    p.add_argument('--model', action='append', dest='models', help='only logs for this model (repeat for more than one)')
    p.add_argument('--include-mock', action='store_true', help='include mockllm/ runs, which are skipped by default')
    p.add_argument('--min-samples', type=int, default=1, help='skip logs that ran fewer samples, such as --limit test runs')
    p.add_argument('--all', action='store_true', help='keep every matching log, not just the newest per model')
    p.add_argument('--scorer', help='scorer to report, if the task has more than one (default: the first)')
    p.add_argument('--title', help='chart title (default: "<task> results")')
    p.add_argument('-o', '--out', type=Path, help='output JSON (default: results/<task>.json)')
    args = p.parse_args()

    paths = args.logs or find_logs(args.log_dir, args.task, args.models, args.include_mock, args.min_samples, not args.all)
    if not paths:
        raise SystemExit('No matching logs found. Check --log-dir, --task, and --model, or pass log files directly.')
    task = args.task or read_eval_log(str(paths[0]), header_only=True).eval.task
    results = summarize(paths, args.title or f'{task} results', scorer=args.scorer)
    out = args.out or Path('results') / f'{task}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + '\n')
    print(f'Wrote {out}: {len(paths)} log(s)')
    for m in results['models']:
        print(f"  {m['model']}: accuracy {m['accuracy']:.3f} ± {m['stderr']:.3f}, {m['samples']} samples × {m['epochs']} epochs, "
              f"{m['limit_hits']} limit hits, {m['tokens']['total']} tokens")
        print('    verdicts: ' + ', '.join(f'{count} {verdict}' for verdict, count in m['verdicts'].items()))
