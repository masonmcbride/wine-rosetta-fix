#!/usr/bin/env python3
"""Audit saved CPU leaf labels without guessing function or assembly mappings."""
import argparse,collections,json,re
from pathlib import Path
import xml.etree.ElementTree as E


def audit(path,pid,start,end):
    root=E.parse(path).getroot();ids={e.attrib['id']:e for e in root.iter() if 'id' in e.attrib}
    def resolve(e):
        while 'ref' in e.attrib:e=ids[e.attrib['ref']]
        return e
    def pids(e):
        e=resolve(e)
        if e.tag=='pid':return {int(e.text)}
        return set().union(*(pids(c) for c in e))
    counts=collections.Counter();pcs=collections.Counter()
    for row in root.iter('row'):
        time=row.find('sample-time')
        if time is None or pid not in pids(row.find('thread')):continue
        if not start<=int(resolve(time).text)<end:continue
        counts['samples']+=1;bt=list(row)[5]
        if bt.tag=='sentinel':counts['missing_user_backtrace']+=1;continue
        bt=resolve(bt);m=re.search(r'PC:(0x[0-9a-fA-F]+)',bt.attrib.get('fmt',''))
        if m:counts['raw_pc_labels']+=1;pcs[m[1]]+=1
        leaf=bt.find('text-address')
        if leaf is not None and not re.fullmatch(r'0x[0-9a-fA-F]+',resolve(leaf).attrib.get('fmt','')):counts['symbol_named_leaf']+=1
    counts.setdefault('symbol_named_leaf',0)
    return {'pid':pid,'range_ns':[start,end],'counts':dict(counts),'top_raw_pcs':pcs.most_common(12),'verified_function_assembly_mappings':0,'interpretation':'Symbol labels, when present, still need artifact, architecture, PC type and runtime mapping verification. Raw PCs remain unresolved; no nearest-symbol guesses.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--pid',type=int,required=True)
    p.add_argument('--start',type=float,default=1);p.add_argument('--end',type=float,default=15);a=p.parse_args()
    result=audit(a.input,a.pid,round(a.start*1e9),round(a.end*1e9));a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
