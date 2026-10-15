#!/usr/bin/env python3
"""Resolve Mach snapshot PCs and attribute explicitly measured per-thread CPU deltas."""
import collections,csv,io,json,pathlib,subprocess,sys

def analyze(file,arch='x86_64'):
 stats=json.loads(pathlib.Path(str(file)+'.stats.json').read_text());rows=list(csv.DictReader(io.StringIO(file.read_text())))
 groups=collections.defaultdict(set);mapping={}
 for r in rows:groups[(r['module'],r['base'])].add(r['pc'])
 for (module,base),pcs in groups.items():
  pcs=sorted(pcs)
  for start in range(0,len(pcs),100):
   chunk=pcs[start:start+100]
   if module=='UNKNOWN':names=['UNKNOWN']*len(chunk)
   else:
    p=subprocess.run(['atos','-arch',arch,'-o',module,'-l',base]+chunk,capture_output=True,text=True,timeout=20)
    names=p.stdout.splitlines()
    if p.returncode or len(names)!=len(chunk):names=['UNRESOLVED']*len(chunk)
   for pc,name in zip(chunk,names):mapping[(module,base,pc)]=name
 initial={t['tid']:(t['first_user_us'],t['first_system_us']) for t in stats['threads']};previous=dict(initial)
 weighted=collections.Counter();user=collections.Counter();system=collections.Counter();counts=collections.Counter();by_thread={}
 unknown=0
 for r in rows:
  tid=int(r['tid']);u=int(r['user_us']);s=int(r['system_us']);pu,ps=previous[tid]
  if u<pu or s<ps:raise ValueError('CPU accounting went backwards')
  du,ds=u-pu,s-ps;previous[tid]=(u,s);name=mapping[(r['module'],r['base'],r['pc'])]
  counts[name]+=1;weighted[name]+=du+ds;user[name]+=du;system[name]+=ds
  if name.startswith('0x') or name in ['UNKNOWN','UNRESOLVED']:unknown+=du+ds
 for tid,(u,s) in previous.items():
  iu,isys=initial[tid];by_thread[str(tid)]=dict(user_us=u-iu,system_us=s-isys)
 total=sum(t['cpu_us'] for t in stats['threads']);assigned=sum(weighted.values())
 if assigned>total:raise ValueError('Attributed CPU exceeds observed thread accounting')
 result=dict(samples=len(rows),stats=stats,observed_thread_cpu_us=total,attributed_cpu_us=assigned,unattributed_cpu_us=total-assigned,
    unresolved_attributed_cpu_us=unknown,raw_counts=counts.most_common(),weighted_cpu_us=weighted.most_common(),user_cpu_us=user.most_common(),system_cpu_us=system.most_common(),per_thread=by_thread,
    interpretation='Endpoint snapshots weighted by preceding CPU deltas. Time between different functions can alias; kernel CPU is charged to a userspace context, not a kernel stack. No exact per-function-time claim.')
 file.with_suffix('.analysis.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=pathlib.Path(sys.argv[1]);r=analyze(p,sys.argv[2] if len(sys.argv)>2 else 'x86_64')
 summary={k:v for k,v in r.items() if k not in ['stats','per_thread','raw_counts','user_cpu_us','system_cpu_us']}
 summary['weighted_cpu_us']=r['weighted_cpu_us'][:15]
 print(json.dumps(summary,indent=2))
