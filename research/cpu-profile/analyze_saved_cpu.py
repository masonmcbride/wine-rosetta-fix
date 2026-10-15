#!/usr/bin/env python3
"""Count saved Instruments CPU samples; counts are not exact CPU timings."""
import collections,json,sys
from pathlib import Path
import xml.etree.ElementTree as E
r=E.parse(sys.argv[1]).getroot(); ids={x.attrib['id']:x for x in r.iter() if 'id' in x.attrib}
def resolve(x):
    while 'ref' in x.attrib:x=ids[x.attrib['ref']]
    return x
windows={'before_transition':(24.8,25.8),'gap_229ms':(25.8757265,26.104684666),'gap_300ms':(26.104684666,26.404682708),'after_transition':(27,28)}
out={}
for name,(a,b) in windows.items():
    threads=collections.Counter();states=collections.Counter();pcs=collections.Counter()
    for row in r.iter('row'):
        time=int(resolve(row.find('sample-time')).text)/1e9
        if not a<=time<b:continue
        thread=resolve(row.find('thread'));threads[thread.attrib.get('fmt','unknown')]+=1
        states[resolve(row.find('thread-state')).attrib.get('fmt','unknown')]+=1
        bt=row.find('kperf-bt')
        if bt is not None:pcs[resolve(bt).attrib.get('fmt','unknown')]+=1
    out[name]={'start_s':a,'end_s':b,'sample_count':sum(threads.values()),'threads':dict(threads),'states':dict(states),'top_stack_labels':pcs.most_common(5)}
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
