#!/usr/bin/env python3
"""Audit VTVgo EPG ID uniqueness and linkage in saved raw JSON batches.

Usage:
  python audit_vtvgo_ids.py --root out/vtvgo/raw --output id_audit

No network access. Does not modify source files. Python stdlib only.
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def write_csv(path, columns, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('out/vtvgo/raw'))
    parser.add_argument('--output', type=Path, default=Path('id_audit'))
    parser.add_argument('--max-examples', type=int, default=200)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    files = sorted(args.root.glob('group_*/*.json'))
    if not files:
        parser.error(f'No JSON files matching group_*/*.json beneath {args.root}')

    # key: ID; value: count, collection of distinct observed broadcast signatures,
    # distinct channel IDs, dates, versions, and related IDs.
    slot = {}
    program = {}
    version_counts = Counter()
    missing = Counter()
    channels_in_data = set()
    row_count = 0
    unique_occurrence = set()
    date_channel_count = Counter()

    for path in files:
        payload = json.loads(path.read_text(encoding='utf-8'))
        block = payload.get('data', {})
        if not isinstance(block, dict):
            raise ValueError(f'{path}: data is not an object')
        for outer_channel, entries in block.items():
            for entry in entries or []:
                schedule_date = entry.get('date', '')
                for obj in entry.get('programs') or []:
                    row_count += 1
                    sid = str(obj.get('slotId') or '')
                    pid = str(obj.get('programID') or '')
                    channel = str(obj.get('channelId') or outer_channel)
                    start = str(obj.get('startTime') or '')
                    end = str(obj.get('endTime') or '')
                    title = str(obj.get('title') or '')
                    ver = str(obj.get('version', ''))
                    channels_in_data.add(channel)
                    date_channel_count[(channel, schedule_date)] += 1
                    version_counts[ver] += 1
                    for name, value in [('slotId',sid), ('programID',pid), ('startTime',start), ('endTime',end)]:
                        if not value:
                            missing[name] += 1
                    # A broadcast occurrence is distinct from a saved row: duplicate
                    # rows can arise from overlapping queries or API duplication.
                    occurrence = (channel, start, end, pid, title)
                    unique_occurrence.add(occurrence)
                    if sid:
                        if sid not in slot:
                            slot[sid] = {'rows':0, 'signatures':set(), 'channels':set(), 'dates':set(), 'versions':set(), 'program_ids':set(), 'examples':[]}
                        s = slot[sid]
                        s['rows'] += 1
                        s['signatures'].add(occurrence)
                        s['channels'].add(channel)
                        s['dates'].add(schedule_date)
                        s['versions'].add(ver)
                        s['program_ids'].add(pid)
                        if len(s['examples']) < 3:
                            s['examples'].append((channel, schedule_date, start, end, pid, title, ver))
                    if pid:
                        if pid not in program:
                            program[pid] = {'rows':0, 'slots':set(), 'channels':set(), 'dates':set(), 'titles':set(), 'versions':set(), 'examples':[]}
                        p = program[pid]
                        p['rows'] += 1
                        if sid: p['slots'].add(sid)
                        p['channels'].add(channel)
                        p['dates'].add(schedule_date)
                        p['titles'].add(title)
                        p['versions'].add(ver)
                        if len(p['examples']) < 3:
                            p['examples'].append((channel, schedule_date, start, sid, title))

    slot_reused = {k:v for k,v in slot.items() if v['rows'] > 1}
    slot_conflicts = {k:v for k,v in slot.items() if len(v['signatures']) > 1}
    slot_multi_channel = {k:v for k,v in slot.items() if len(v['channels']) > 1}
    slot_multi_pid = {k:v for k,v in slot.items() if len(v['program_ids']) > 1}
    slot_multi_version = {k:v for k,v in slot.items() if len(v['versions']) > 1}
    program_multiple_slots = {k:v for k,v in program.items() if len(v['slots']) > 1}
    program_multiple_channels = {k:v for k,v in program.items() if len(v['channels']) > 1}
    program_multiple_titles = {k:v for k,v in program.items() if len(v['titles']) > 1}

    summary = {
        'input_files': len(files), 'rows': row_count,
        'channels_present': len(channels_in_data),
        'distinct_occurrences_by_channel_time_pid_title': len(unique_occurrence),
        'unique_slot_ids': len(slot), 'unique_program_ids': len(program),
        'missing_fields': dict(missing),
        'slot_ids_appearing_multiple_times': len(slot_reused),
        'slot_ids_with_different_occurrence_signatures': len(slot_conflicts),
        'slot_ids_spanning_multiple_channels': len(slot_multi_channel),
        'slot_ids_mapping_to_multiple_program_ids': len(slot_multi_pid),
        'slot_ids_with_multiple_versions': len(slot_multi_version),
        'program_ids_linked_to_multiple_slots': len(program_multiple_slots),
        'program_ids_spanning_multiple_channels': len(program_multiple_channels),
        'program_ids_associated_with_multiple_titles': len(program_multiple_titles),
        'version_distribution': dict(version_counts),
    }
    (args.output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    slot_rows = []
    for sid, s in sorted(slot.items(), key=lambda x:(-len(x[1]['signatures']),-x[1]['rows'],x[0])):
        if s['rows'] == 1: continue
        slot_rows.append({'slotId':sid, 'rows':s['rows'], 'distinct_occurrences':len(s['signatures']), 'channels': '|'.join(sorted(s['channels'])), 'date_count':len(s['dates']), 'programIDs':'|'.join(sorted(s['program_ids'])), 'versions':'|'.join(sorted(s['versions'])), 'example_rows':repr(s['examples'])})
    write_csv(args.output / 'repeated_slot_ids.csv', ['slotId','rows','distinct_occurrences','channels','date_count','programIDs','versions','example_rows'], slot_rows[:args.max_examples])

    program_rows = []
    for pid, p in sorted(program.items(), key=lambda x:(-len(x[1]['slots']),-len(x[1]['channels']),-x[1]['rows'],x[0])):
        if p['rows'] == 1: continue
        program_rows.append({'programID':pid, 'rows':p['rows'], 'slot_count':len(p['slots']), 'channel_count':len(p['channels']), 'date_count':len(p['dates']), 'distinct_titles':len(p['titles']), 'title_examples':' | '.join(sorted(p['titles'])[:4]), 'example_rows':repr(p['examples'])})
    write_csv(args.output / 'repeated_program_ids.csv', ['programID','rows','slot_count','channel_count','date_count','distinct_titles','title_examples','example_rows'], program_rows[:args.max_examples])

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f'\nReports saved to {args.output.resolve()}')
    print('Interpretation: repeated programID + multiple slotIds suggests a content-to-airing relation.')
    print('Repeated slotId with different occurrences is an ID collision or changed record requiring inspection.')
    print('Different titles under one programID need manual inspection before calling programID a stable content identifier.')


if __name__ == '__main__':
    main()

