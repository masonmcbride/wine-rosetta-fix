#!/usr/bin/env python3
"""Stream an Instruments thread-state export to a target-only CSV.

Numeric XML references use a packed array; XML rows are discarded immediately.
Missing references fail closed. Output contains raw scheduler intervals, not
estimates of uninstrumented CPU cost or inferred lock identities.
"""
import argparse
from array import array
import collections
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET


class References:
    def __init__(self):
        self.numbers = array('q')
        self.objects = {}
        self.missing = -(2**63)

    def get(self, index):
        if index in self.objects:
            return self.objects[index]
        if index < len(self.numbers) and self.numbers[index] != self.missing:
            return self.numbers[index]
        raise ValueError(f'Missing XML reference {index}')

    def decode(self, element):
        if 'ref' in element.attrib:
            return self.get(int(element.attrib['ref']))
        children = [self.decode(c) for c in element]
        tag = element.tag
        if tag in ('start-time', 'duration', 'pid', 'tid'):
            result = int(element.text)
        elif tag == 'thread-state':
            result = element.attrib.get('fmt', element.text)
        elif tag == 'process':
            result = {'pid': next((v for c, v in zip(element, children) if c.tag == 'pid'), None)}
        elif tag == 'thread':
            result = {'tid': next((v for c, v in zip(element, children) if c.tag == 'tid'), None),
                      'pid': next((v['pid'] for c, v in zip(element, children) if c.tag == 'process'), None),
                      'label': element.attrib.get('fmt', 'unknown')}
        else:
            # Retain references from other types too: later rows may reuse them.
            result = None
        if 'id' in element.attrib:
            index = int(element.attrib['id'])
            if isinstance(result, int):
                if index >= len(self.numbers):
                    self.numbers.extend(array('q', [self.missing]) * (index + 131072 - len(self.numbers)))
                self.numbers[index] = result
            else:
                self.objects[index] = result
        return result


def extract(source, output, pid):
    refs = References()
    counts = collections.Counter()
    rows = selected = 0
    labels = {}
    minimum = maximum = None
    with output.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['start_ns', 'end_ns', 'tid', 'state'])
        stack = []
        for event, element in ET.iterparse(source, events=('start', 'end')):
            if event == 'start':
                stack.append(element)
                continue
            if element.tag == 'row':
                fields = [refs.decode(c) for c in element]
                rows += 1
                thread, process = fields[1], fields[4]
                if process and process.get('pid') == pid and thread and thread.get('pid') == pid:
                    start, state, duration = fields[0], fields[2], fields[3]
                    if start < 0 or duration < 0:
                        raise ValueError('Negative scheduler interval')
                    writer.writerow([start, start + duration, thread['tid'], state])
                    labels[str(thread['tid'])] = thread['label']
                    counts[state] += 1
                    selected += 1
                    minimum = start if minimum is None else min(minimum, start)
                    maximum = max(maximum or 0, start + duration)
                stack[-2].remove(element)
                element.clear()
                if rows % 250000 == 0:
                    print(f'Processed {rows} rows; target {selected}', flush=True)
            stack.pop()
    summary = dict(pid=pid, all_rows=rows, target_rows=selected, states=dict(counts),
                   threads=labels, minimum_ns=minimum, maximum_ns=maximum,
                   numeric_reference_bytes=len(refs.numbers)*refs.numbers.itemsize,
                   object_references=len(refs.objects))
    Path(str(output)+'.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pid', type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.input, args.output, args.pid), indent=2))
