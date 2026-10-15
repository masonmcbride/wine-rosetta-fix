#!/usr/bin/env python3
"""Inspect target presentation requests and drawable waits in saved trace exports."""
import argparse,json,re
import xml.etree.ElementTree as E
from pathlib import Path
from analyze_stalls import union_length

parser=argparse.ArgumentParser(description=__doc__)
for name in ('events','toc','stalls','output'): parser.add_argument(name)
parser.add_argument('--pid',type=int,required=True)
args=parser.parse_args()
events,toc,stalls,output=args.events,args.toc,args.stalls,args.output
r=E.parse(events).getroot(); ids={x.attrib['id']:x for x in r.iter() if 'id' in x.attrib}
tables=E.parse(toc).getroot().findall('./run/data/table'); gaps=json.loads(Path(stalls).read_text())['gaps']
def resolve(x):
    while 'ref' in x.attrib: x=ids[x.attrib['ref']]
    return x

def pids(x):
    x=resolve(x)
    if x.tag=='pid':return {int(x.text)}
    return set().union(*(pids(c) for c in x))

def val(x):return int(resolve(x).text)

out={}
for node in r:
    name=tables[int(re.search(r'table\[(\d+)\]',node.attrib['xpath'])[1])-1].attrib['schema']
    rows=[x for x in node.findall('row') if args.pid in pids(x)]
    starts=sorted(val(x.find('start-time')) for x in rows)
    intervals=[(val(x.find('start-time')),val(x.find('start-time'))+val(x.find('duration'))) for x in rows if x.find('duration') is not None]
    out[name]={'rows':len(rows),'largest_start_gaps_ms':sorted([(b-a)/1e6 for a,b in zip(starts,starts[1:])],reverse=True)[:10],
               'longest_interval_ms':max((b-a for a,b in intervals),default=0)/1e6,
               'display_gap_overlap':[]}
    for g in gaps:
        a,b=round(g['start_s']*1e9),round(g['end_s']*1e9)
        out[name]['display_gap_overlap'].append({'start_s':g['start_s'],'gap_ms':g['gap_ms'],
               'starts':sum(a<=s<b for s in starts),'interval_union_ms':union_length(intervals,a,b)/1e6})
Path(output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:{'rows':v['rows'],'longest_interval_ms':v['longest_interval_ms'],'largest_start_gaps_ms':v['largest_start_gaps_ms'][:3],'largest_display_gap':v['display_gap_overlap'][:2]} for k,v in out.items()},indent=2))
