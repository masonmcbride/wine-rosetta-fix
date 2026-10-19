#!/usr/bin/env python3
"""Join target display intervals, scheduler states and clock-aligned CPU snapshots.

Outputs all covered frames. No exact function CPU time or causal classification.
"""
import argparse,bisect,collections,csv,json
from pathlib import Path
from align_pacing_samples import align
from extract_thread_states import extract
from analyze_recurring_pacing import frame_streams,integrals
from summarize_metal import summarize

def analyze(sample,exports,toc,output):
    output.mkdir(parents=True,exist_ok=True)
    alignment=align(sample,Path(str(sample)+'.sync.json'),exports/'os-signpost.xml',output/'aligned.csv');pid=alignment['pid']
    display=summarize(exports/'displayed-surfaces-interval.xml',toc,pid)
    displays=display['tables'].get('displayed-surfaces-interval',{}).get('per_display',{})
    if len(displays)!=1:raise ValueError('Require exactly one target-attributed display stream; do not mix multiple displays or use global swaps')
    states=extract(exports/'thread-state.xml',output/'states.csv',pid)
    if not states['target_rows']:raise ValueError('No target scheduler coverage')
    starts=frame_streams(exports/'displayed-surfaces-interval.xml',toc,pid)['displayed-surfaces-interval']
    a,b=alignment['trace_start_marker_ns'],alignment['trace_end_marker_ns'];starts=[t for t in starts if a<=t<=b]
    if len(starts)<2:raise ValueError('No complete target display intervals within CPU anchors')
    data,_=integrals(output/'states.csv',starts);snapshots=collections.defaultdict(collections.Counter)
    with (output/'aligned.csv').open() as f:
        for r in csv.DictReader(f):
            i=bisect.bisect_right(starts,int(r['trace_time_ns']))-1
            if 0<=i<len(starts)-1:snapshots[i][(r['tid'],r['module'],r['pc'])]+=1
    frames=[]
    for i,(a,b) in enumerate(zip(starts,starts[1:])):
        threads={}
        for tid,d in data.items():
            values={s:int(v[i+1]-v[i]) for s,v in d['prefix'].items()};covered=sum(values.values())
            if covered>b-a:raise ValueError('Scheduler coverage exceeds frame interval')
            threads[tid]={'state_ns':values,'uncovered_ns':b-a-covered}
        frames.append({'start_ns':a,'end_ns':b,'gap_ms':(b-a)/1e6,'threads':threads,'snapshots':[dict(tid=t,module=m,pc=p,count=n) for (t,m,p),n in snapshots[i].items()]})
    result={'pid':pid,'alignment':alignment,'display':display,'scheduler':states,'complete_frame_intervals':len(frames),'frames_without_cpu_snapshot':sum(not f['snapshots'] for f in frames),'frames':frames,'limits':['Display intervals differ from game CPU frame/present-request intervals','Snapshots are locations, not call counts or exact function time; verify bytes separately','Scheduler states distinguish recorded execution from blocking; uncovered time remains explicit','Three-second pilot cannot establish recurring gameplay cause or collector overhead']}
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return {k:v for k,v in result.items() if k not in ['frames','display','scheduler','alignment']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['sample','exports','toc','output']:p.add_argument(name,type=Path)
    a=p.parse_args();print(json.dumps(analyze(a.sample,a.exports,a.toc,a.output),indent=2))
