#!/usr/bin/env python3
"""Audit SCTV raw EPG responses, annual coverage, and historical gaps."""
import argparse
import collections
import json
from datetime import date, timedelta
from pathlib import Path


def days_between(start, end):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def ranges_of_days(days):
    """Coalesce sorted dates into inclusive contiguous intervals."""
    values = sorted(days)
    if not values:
        return []
    result = []
    start = end = values[0]
    for day in values[1:]:
        if (day - end).days == 1:
            end = day
        else:
            result.append({'from': start.isoformat(), 'to': end.isoformat(), 'days': (end - start).days + 1})
            start = end = day
    result.append({'from': start.isoformat(), 'to': end.isoformat(), 'days': (end - start).days + 1})
    return result


def audit(root: Path):
    base = root / 'data'
    if not base.is_dir():
        raise FileNotFoundError(f'Expected data directory: {base}')
    counts = collections.Counter()
    by_channel = {}
    observed = collections.defaultdict(lambda: {'nonempty': set(), 'empty': set(), 'files': set(), 'events_by_year': collections.Counter()})
    errors = []
    for path in sorted(base.glob('*/*/*.json')):
        counts['files'] += 1
        channel = path.parent.parent.name
        try:
            day = date.fromisoformat(path.parent.name + '-' + path.stem)
            with path.open(encoding='utf-8') as fh:
                payload = json.load(fh)
            if not isinstance(payload, dict):
                raise ValueError('Top-level JSON must be an object')
            schedule = payload.get('LichPhatSong')
            if schedule is None:
                counts['empty'] += 1
                observed[channel]['empty'].add(day)
            else:
                if not isinstance(schedule, dict):
                    raise ValueError('LichPhatSong is neither null nor object')
                events = schedule.get('EventList')
                if not isinstance(events, list):
                    raise ValueError('EventList is not a list')
                if str(schedule.get('ChannelId')) != channel:
                    counts['channel_mismatch'] += 1
                if not events:
                    counts['empty'] += 1
                    observed[channel]['empty'].add(day)
                else:
                    counts['nonempty'] += 1
                    counts['events'] += len(events)
                    observed[channel]['nonempty'].add(day)
                    observed[channel]['events_by_year'][day.year] += len(events)
                    stat = by_channel.setdefault(channel, {'first': day, 'last': day, 'days': 0, 'events': 0})
                    stat['first'] = min(stat['first'], day)
                    stat['last'] = max(stat['last'], day)
                    stat['days'] += 1
                    stat['events'] += len(events)
            observed[channel]['files'].add(day)
        except (ValueError, OSError, TypeError) as exc:
            counts['invalid'] += 1
            errors.append({'file': str(path), 'error': str(exc)})

    status_path = root / 'status.json'
    requested_from = requested_to = None
    if status_path.is_file():
        try:
            status = json.loads(status_path.read_text(encoding='utf-8'))
            requested_from = date.fromisoformat(status['range']['from'])
            requested_to = date.fromisoformat(status['range']['to'])
            if requested_from > requested_to:
                raise ValueError('Invalid requested range')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({'file': str(status_path), 'error': f'Could not read requested range: {exc}'})
            requested_from = requested_to = None

    channel_results = {}
    for channel, data in sorted(observed.items()):
        active = data['nonempty']
        files = data['files']
        empty = data['empty']
        if active:
            first, last = min(active), max(active)
            interior = set(days_between(first, last)) - active
            gaps = ranges_of_days(interior)
            runs = ranges_of_days(active)
            longest = max(runs, key=lambda r: r['days'])
        else:
            first = last = None
            gaps = []
            longest = None
        window_from = requested_from or min(files)
        window_to = requested_to or max(files)
        annual = {}
        for year in range(window_from.year, window_to.year + 1):
            lo = max(window_from, date(year, 1, 1))
            hi = min(window_to, date(year, 12, 31))
            if lo > hi:
                continue
            expected = (hi - lo).days + 1
            n_active = sum(lo <= d <= hi for d in active)
            n_empty = sum(lo <= d <= hi for d in empty)
            n_files = sum(lo <= d <= hi for d in files)
            annual[str(year)] = {
                'expected_days': expected,
                'downloaded_days': n_files,
                'active_days': n_active,
                'empty_days': n_empty,
                'missing_files': expected - n_files,
                'events': data['events_by_year'][year],
                'coverage_pct': round(100 * n_active / expected, 2),
            }
        channel_results[channel] = {
            'first': first.isoformat() if first else None,
            'last': last.isoformat() if last else None,
            'days': len(active),
            'events': sum(data['events_by_year'].values()),
            'years': annual,
            'continuity': {
                'window': 'first_to_last_nonempty',
                'gap_days': sum(g['days'] for g in gaps),
                'gap_count': len(gaps),
                'gaps': [{**g, 'empty_responses': sum(g['from'] <= d.isoformat() <= g['to'] for d in empty),
                          'missing_files': sum(g['from'] <= d.isoformat() <= g['to'] for d in set(days_between(date.fromisoformat(g['from']), date.fromisoformat(g['to']))) - files)} for g in gaps],
                'longest_active_run': longest,
            },
        }
    return {
        'counts': dict(counts),
        'channels': channel_results,
        'errors': errors[:100],
        'errors_truncated': max(0, len(errors) - 100),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='Root output directory containing data/')
    parser.add_argument('--output', type=Path, help='Optional audit report JSON path')
    args = parser.parse_args()
    result = audit(args.root)
    report = json.dumps(result, ensure_ascii=False, indent=2)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
