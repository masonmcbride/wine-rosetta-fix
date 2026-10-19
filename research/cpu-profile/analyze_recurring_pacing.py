#!/usr/bin/env python3
"""Compare complete covered presentation intervals using exact scheduler integrals.

Association only: slow/fast groups are descriptive and temporally dependent.
Running durations are not function attribution, and missing coverage is explicit.
"""
import argparse,bisect,collections,csv,json,re
from array import array
from pathlib import Path
import xml.etree.ElementTree as E


def frame_streams(events,toc,pid):
    root=E.parse(events).getroot();ids={e.attrib['id']:e for e in root.iter() if 'id' in e.attrib}
    tables=E.parse(toc).getroot().findall('./run/data/table')
    def resolve(e):
        while 'ref' in e.attrib:e=ids[e.attrib['ref']]
        return e
    def pids(e):
        e=resolve(e)
        if e.tag=='pid':return {int(e.text)}
        return set().union(*(pids(c) for c in e))
    streams={}
    for node in root.findall('node'):
        name=tables[int(re.search(r'table\[(\d+)\]',node.attrib['xpath'])[1])-1].attrib['schema']
        if name not in ('displayed-surfaces-interval','ca-client-present-request'):continue
        streams[name]=sorted(set(int(resolve(row.find('start-time')).text) for row in node.findall('row') if pid in pids(row)))
    return streams


def integrals(source,queries):
    states=['Running','Blocked','Runnable','Preempted','Interrupted','Idle','Terminated','Unknown']
    data={};last={};rows=0
    with source.open() as f:
        for r in csv.DictReader(f):
            a,b,tid=int(r['start_ns']),int(r['end_ns']),r['tid'];state=r['state'];rows+=1
            if b<a or (tid in last and a<last[tid]):raise ValueError('Unordered/overlapping thread intervals')
            last[tid]=b
            if state not in states:raise ValueError('Unknown state '+state)
            if tid not in data:data[tid]={'index':0,'totals':dict.fromkeys(states,0),'prefix':{s:array('q',[0])*len(queries) for s in states}}
            d=data[tid]
            while d['index']<len(queries) and queries[d['index']]<=b:
                q=queries[d['index']]
                for s in states:d['prefix'][s][d['index']]=d['totals'][s]+(max(0,q-a) if s==state else 0)
                d['index']+=1
            d['totals'][state]+=b-a
    for d in data.values():
        for s in states:
            for i in range(d['index'],len(queries)):d['prefix'][s][i]=d['totals'][s]
    return data,rows


def percentile(values,q):
    x=sorted(values)
    return x[round((len(x)-1)*q)] if x else None


def analyze(source,streams,labels,start,end,output):
    intervals={name:[(a,b) for a,b in zip(ts,ts[1:]) if a>=start and b<=end] for name,ts in streams.items()}
    queries=sorted({x for pairs in intervals.values() for pair in pairs for x in pair})
    if not queries:raise ValueError('No covered intervals')
    indices={q:i for i,q in enumerate(queries)};data,rows=integrals(source,queries)
    selected={t:name for t,name in labels.items() if any(x in name for x in ('Backend','dxmt-encode','dxmt-finish','wine 0x2a466','Main Thread'))}
    report={'scheduler_rows':rows,'range_ns':[start,end],'function_attribution':'Unresolved: scheduler intervals name threads, not functions.','streams':{}}
    with output.with_suffix('.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['stream','start_ns','end_ns','interval_ms','tid','thread','running_fraction','blocked_fraction','runnable_fraction','preempted_fraction','other_fraction','unobserved_fraction']);writer.writeheader()
        for name,pairs in intervals.items():
            lengths=[b-a for a,b in pairs];low=percentile(lengths,.25);high=percentile(lengths,.75)
            # Define disjoint groups even when quantiles tie.
            categories={'fast':[p for p in pairs if p[1]-p[0]<=low], 'slow':[p for p in pairs if p[1]-p[0]>=high and p[1]-p[0]>low]}
            summary={'interval_count':len(pairs),'quantiles_ms':{str(q):percentile(lengths,q)/1e6 for q in (.25,.5,.75,.95,.99)},'groups':{},'per_second':{}}
            measures={}
            for a,b in pairs:
                ia,ib=indices[a],indices[b];duration=b-a
                measures[a,b]={}
                for tid,label in selected.items():
                    d=data.get(tid);values={s:(p[ib]-p[ia]) for s,p in d['prefix'].items()} if d else {}
                    total=sum(values.values())
                    if total>duration:raise ValueError('Overcounted scheduler coverage')
                    row={'stream':name,'start_ns':a,'end_ns':b,'interval_ms':duration/1e6,'tid':tid,'thread':label}
                    for s in ('Running','Blocked','Runnable','Preempted'):row[s.lower()+'_fraction']=values.get(s,0)/duration
                    row['other_fraction']=sum(v for s,v in values.items() if s not in ('Running','Blocked','Runnable','Preempted'))/duration
                    row['unobserved_fraction']=(duration-total)/duration
                    writer.writerow(row);measures[a,b][tid]=row
            for group,picked in categories.items():
                summary['groups'][group]={'count':len(picked),'threads':{}}
                for tid,label in selected.items():
                    items=[measures[p][tid] for p in picked]
                    summary['groups'][group]['threads'][label]={key:percentile([r[key] for r in items],.5) for key in ('running_fraction','blocked_fraction','runnable_fraction','preempted_fraction','unobserved_fraction')}
            for second in range(start//10**9,end//10**9):
                durations=[b-a for a,b in pairs if second*10**9<=a<(second+1)*10**9]
                if durations:summary['per_second'][str(second)]={'count':len(durations),'p50_ms':percentile(durations,.5)/1e6,'p95_ms':percentile(durations,.95)/1e6}
            report['streams'][name]=summary
    output.write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['states','events','toc','labels','output']:p.add_argument(name,type=Path)
    p.add_argument('--pid',type=int,required=True);p.add_argument('--start',type=float,default=1);p.add_argument('--end',type=float,default=15);a=p.parse_args()
    r=analyze(a.states,frame_streams(a.events,a.toc,a.pid),json.loads(a.labels.read_text())['threads'],round(a.start*1e9),round(a.end*1e9),a.output)
    for name,s in r['streams'].items():print(name,s['interval_count'],s['quantiles_ms'],{g:v['count'] for g,v in s['groups'].items()})
