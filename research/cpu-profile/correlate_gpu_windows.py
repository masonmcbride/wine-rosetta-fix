#!/usr/bin/env python3
"""Stream target GPU intervals and union clipped overlap in named windows."""
import argparse,json
from pathlib import Path
import xml.etree.ElementTree as E
from extract_thread_states import References
from analyze_stalls import union_length


def analyze(path,windows,pid):
    refs=References();intervals={k:[] for k in windows};rows=target=0;stack=[]
    for event,e in E.iterparse(path,events=('start','end')):
        if event=='start':stack.append(e);continue
        if e.tag=='row':
            fields={}
            for c in e: fields.setdefault(c.tag,refs.decode(c))
            rows+=1
            process=fields.get('process')
            if process and process.get('pid')==pid:
                a=fields['start-time'];b=a+fields['duration'];target+=1
                for name,(start,end) in windows.items():
                    if b>start and a<end:intervals[name].append((max(a,start),min(b,end)))
            stack[-2].remove(e);e.clear()
        stack.pop()
    return {'all_rows':rows,'target_rows':target,'windows':{name:{'window_ms':(b-a)/1e6,'gpu_interval_count':len(intervals[name]),'recorded_gpu_union_ms':union_length(intervals[name],a,b)/1e6} for name,(a,b) in windows.items()},'limits':'Recorded target GPU interval coverage, not hardware utilization or a wait dependency graph.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['input','windows','output']:p.add_argument(name,type=Path)
    p.add_argument('--pid',type=int,required=True);a=p.parse_args()
    result=analyze(a.input,json.loads(a.windows.read_text()),a.pid)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
