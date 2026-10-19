#!/usr/bin/env python3
"""Clip saved per-thread scheduler intervals to explicit nanosecond windows."""
import argparse,collections,csv,json
from pathlib import Path


def correlate(source, windows):
    totals={name:collections.defaultdict(collections.Counter) for name in windows}
    previous={};overlaps=backwards=0;rows=0
    with source.open() as f:
        for r in csv.DictReader(f):
            start,end,tid=int(r['start_ns']),int(r['end_ns']),r['tid']
            if end < start: raise ValueError('Negative interval')
            if tid in previous:
                a,b=previous[tid]
                backwards += start<a
                overlaps += start<b
            previous[tid]=(start,end); rows+=1
            for name,(a,b) in windows.items():
                duration=min(b,end)-max(a,start)
                if duration>0:totals[name][tid][r['state']]+=duration
    for name,(a,b) in windows.items():
        for tid,states in totals[name].items():
            if sum(states.values())>b-a:
                raise ValueError(f'Thread {tid} coverage exceeds window {name}')
    return {'rows':rows,'backward_starts':backwards,'overlapping_thread_intervals':overlaps,
            'windows':{name:{'start_ns':a,'end_ns':b,'threads':{tid:dict(states) for tid,states in totals[name].items()}} for name,(a,b) in windows.items()}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv',type=Path);p.add_argument('windows',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args(); result=correlate(args.csv,json.loads(args.windows.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:v for k,v in result.items() if k!='windows'})
