#!/usr/bin/env python3
"""Attach target GPU interval-union coverage to recurring pacing groups."""
import argparse,bisect,collections,csv,json,statistics
from pathlib import Path
import xml.etree.ElementTree as E
from extract_thread_states import References


def gpu_union(path,pid):
    refs=References();intervals=[];stack=[]
    for event,e in E.iterparse(path,events=('start','end')):
        if event=='start':stack.append(e);continue
        if e.tag=='row':
            fields={}
            for c in e:fields.setdefault(c.tag,refs.decode(c))
            p=fields.get('process')
            if p and p.get('pid')==pid:
                a=fields['start-time'];intervals.append((a,a+fields['duration']))
            stack[-2].remove(e);e.clear()
        stack.pop()
    merged=[]
    for a,b in sorted(intervals):
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
        else:merged.append((a,b))
    starts=[a for a,b in merged];prefix=[0]
    for a,b in merged:prefix.append(prefix[-1]+b-a)
    def integral(t):
        i=bisect.bisect_right(starts,t)-1
        return 0 if i<0 else prefix[i]+min(max(0,t-merged[i][0]),merged[i][1]-merged[i][0])
    return integral


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['gpu','intervals','summary','output']:p.add_argument(name,type=Path)
    p.add_argument('--pid',type=int,required=True);a=p.parse_args()
    integral=gpu_union(a.gpu,a.pid);summary=json.loads(a.summary.read_text());groups=collections.defaultdict(list);seen=set();details=[]
    with a.intervals.open() as f:
        for r in csv.DictReader(f):
            start,end=int(r['start_ns']),int(r['end_ns']);key=(r['stream'],start,end)
            if key in seen:continue
            seen.add(key);n=end-start;s=summary['streams'][r['stream']]
            low=round(s['quantiles_ms']['0.25']*1e6);high=round(s['quantiles_ms']['0.75']*1e6)
            category='fast' if n<=low else 'slow' if n>=high else 'middle'
            coverage=integral(end)-integral(start)
            if not 0<=coverage<=n:raise ValueError('Invalid GPU union')
            d={'stream':r['stream'],'start_ns':start,'end_ns':end,'group':category,'gpu_fraction':coverage/n,'gpu_union_ms':coverage/1e6}
            groups[r['stream'],category].append(d);details.append(d)
    out={'groups':{stream:{group:{'n':len(v),'median_gpu_fraction':statistics.median(r['gpu_fraction'] for r in v),'median_gpu_ms':statistics.median(r['gpu_union_ms'] for r in v)} for (s,group),v in groups.items() if s==stream} for stream in summary['streams']},'intervals':details,'limitation':'Target-attributed recorded GPU coverage is not device utilization or causal dependency.'}
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['groups'],indent=2))
