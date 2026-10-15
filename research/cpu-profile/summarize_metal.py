#!/usr/bin/env python3
"""Summarize selected xctrace XML tables; keep process attribution explicit."""
import argparse
import collections
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def summarize(events, toc, pid):
    root = ET.parse(events).getroot()
    ids = {e.attrib['id']: e for e in root.iter() if 'id' in e.attrib}
    tables = ET.parse(toc).getroot().findall('./run/data/table')

    def resolve(e):
        while e is not None and 'ref' in e.attrib:
            e = ids.get(e.attrib['ref'])
            if e is None:
                raise ValueError('Unresolved XML reference')
        return e

    def processes(e):
        e = resolve(e)
        if e.tag == 'pid':
            return {int(e.text)}
        found = set()
        for child in e:
            found.update(processes(child))
        return found

    def number(e):
        return int(resolve(e).text)

    def union(intervals):
        end = total = 0
        for start, stop in sorted(intervals):
            total += max(0, stop - max(start, end))
            end = max(end, stop)
        return total

    def quantiles(values):
        values = sorted(values)
        if not values:
            return None
        return {name: values[round((len(values) - 1) * q)] / 1e6
                for name, q in [('p50_ms', .5), ('p95_ms', .95), ('p99_ms', .99), ('max_ms', 1)]}

    result = {'pid': pid, 'tables': {}, 'notes': [
        'Display swap intervals are not CPU frame times or input-to-photon latency.',
        'GPU interval union describes recorded attributed work, not hardware utilization.',
        'Compilation duration does not establish that compilation blocked a frame.',
        'Trace collection overhead and repeatability require separate validation.']}
    for node in root.findall('node'):
        index = int(re.search(r'table\[(\d+)\]', node.attrib['xpath'])[1]) - 1
        schema = tables[index].attrib['schema']
        rows = node.findall('row')
        selected = [row for row in rows if pid in processes(row)]
        intervals = []
        for row in selected:
            start, duration = row.find('start-time'), row.find('duration')
            if start is not None and duration is not None:
                intervals.append((number(start), number(start) + number(duration)))
        summary = {'all_rows': len(rows), 'target_rows': len(selected),
                   'interval_union_ms': union(intervals) / 1e6,
                   'duration_ms': quantiles([b - a for a, b in intervals])}
        if schema == 'displayed-surfaces-interval':
            groups = collections.defaultdict(list)
            for row in selected:
                display = resolve(row.find('display-name')).text
                groups[display].append(number(row.find('start-time')))
            summary['per_display'] = {}
            for display, starts in groups.items():
                starts = sorted(set(starts))
                gaps = [b - a for a, b in zip(starts, starts[1:])]
                summary['per_display'][display] = {
                    'unique_swap_times': len(starts), 'gap_ms': quantiles(gaps),
                    'span_seconds': (starts[-1] - starts[0]) / 1e9 if len(starts) > 1 else 0,
                    'swaps_per_second_over_span': (len(starts) - 1) * 1e9 / (starts[-1] - starts[0])
                    if len(starts) > 1 else None,
                    'gaps_over_33_34ms': sum(g > 33340000 for g in gaps)}
        result['tables'][schema] = summary
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('events', type=Path)
    p.add_argument('toc', type=Path)
    p.add_argument('--pid', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = summarize(args.events, args.toc, args.pid)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
