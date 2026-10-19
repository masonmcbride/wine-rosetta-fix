#!/usr/bin/env python3
"""Correlate target display gaps with recorded GPU/compiler/submission intervals."""
import argparse, collections, json, re
from pathlib import Path
import xml.etree.ElementTree as E


def union_length(intervals, start, end):
    last = start
    total = 0
    for a, b in sorted(intervals):
        a, b = max(start, a), min(end, b)
        if b > a:
            total += max(0, b - max(a, last))
            last = max(last, b)
    return total


def analyze(events, toc, pid):
    root = E.parse(events).getroot()
    ids = {x.attrib['id']: x for x in root.iter() if 'id' in x.attrib}
    tables = E.parse(toc).getroot().findall('./run/data/table')
    def resolve(x):
        while x is not None and 'ref' in x.attrib:
            x = ids[x.attrib['ref']]
        return x
    def value(x):
        return int(resolve(x).text)
    def pids(x):
        x = resolve(x)
        if x.tag == 'pid':
            return {int(x.text)}
        return set().union(*(pids(c) for c in x))
    def label(x):
        x = resolve(x)
        return x.attrib.get('fmt', x.text or '')
    intervals, displays = {}, collections.defaultdict(list)
    threads = collections.Counter()
    thread_seconds = collections.defaultdict(collections.Counter)
    for node in root.findall('node'):
        i = int(re.search(r'table\[(\d+)\]', node.attrib['xpath'])[1]) - 1
        name = tables[i].attrib['schema']
        data = []
        for row in node.findall('row'):
            if pid not in pids(row):
                continue
            start = value(row.find('start-time'))
            duration = row.find('duration')
            data.append((start, start + value(duration) if duration is not None else start))
            if name == 'displayed-surfaces-interval':
                displays[label(row.find('display-name'))].append(start)
            if name == 'metal-application-command-buffer-submissions':
                t = row.find('thread')
                if t is not None:
                    threads[label(t)] += 1
                    thread_seconds[int(start / 1e9)][label(t)] += 1
        intervals[name] = sorted(data)
    gaps = []
    for display, starts in displays.items():
        starts = sorted(set(starts))
        for a, b in zip(starts, starts[1:]):
            if b - a <= 33340000:
                continue
            item = {'display': display, 'start_s': a / 1e9, 'end_s': b / 1e9, 'gap_ms': (b-a)/1e6}
            for name, data in intervals.items():
                if name == 'displayed-surfaces-interval':
                    continue
                item[name] = {'overlap_ms': union_length(data, a, b)/1e6,
                              'starts_in_gap': sum(a <= x < b for x,y in data)}
            gaps.append(item)
    return {'pid': pid, 'submission_threads': dict(threads),
            'gaps': sorted(gaps, key=lambda x: -x['gap_ms']),
            'submission_threads_per_second': {str(k): dict(v) for k,v in sorted(thread_seconds.items())},
            'limitations': 'Overlap is correlation. GPU intervals exclude unattributed work; submission duration is not CPU busy time. Menus cannot be identified from timing alone.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('events', type=Path); p.add_argument('toc', type=Path)
    p.add_argument('--pid', type=int, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); result = analyze(a.events, a.toc, a.pid)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
