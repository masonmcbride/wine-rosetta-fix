#!/usr/bin/env python3
"""Validate independent CPU shares and within-thread mixes against direct snapshots."""
import argparse,datetime,hashlib,json,os,pathlib,re,resource,subprocess,time
from analyze_mach import analyze
parser=argparse.ArgumentParser();parser.add_argument('--arch',choices=['arm64','x86_64'],default='x86_64');parser.add_argument('--quick',action='store_true');parser.add_argument('--rates',nargs='+',type=int);parser.add_argument('--workloads',nargs='+',choices=['shares','mix']);args=parser.parse_args()
if args.rates and any(r<1000 or r>50000 for r in args.rates):parser.error('rates must be 1000..50000')
H=pathlib.Path(__file__).resolve().parent;OUT=H/'results'/('mach-validation-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));OUT.mkdir(parents=True)
lib=H/f'tools/mach-sampler-{args.arch}.dylib';rows=[]
plan=[('shares',None,0)]
for rep in range(1 if args.quick else 2):
 cases=[(work,rate) for work in (args.workloads or ['shares','mix']) for rate in (args.rates or ([10000] if args.quick else [5000,10000,17000]))]
 if rep:cases.reverse()
 plan.extend((work,rate,rep+1) for work,rate in cases)
plan.append(('shares',None,1))
meta=dict(arch=args.arch,source_sha256=hashlib.sha256((H/'mach_sampler.c').read_bytes()).hexdigest(),library_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),runs=rows)
(OUT/'mach_sampler.c').write_bytes((H/'mach_sampler.c').read_bytes())
for work in ['shares','mix']:(OUT/f'calibrate_{work}.c').write_bytes((H/f'calibrate_{work}.c').read_bytes())
try:
 for work,rate,rep in plan:
  label=f'{work}-{rate or "control"}-r{rep}';target=H/f'tools/calibrate-{work}-{args.arch}';env=os.environ.copy()
  for k in list(env):
   if k.startswith('MACH_SAMPLE_') or k=='DYLD_INSERT_LIBRARIES':del env[k]
  if rate:env.update(DYLD_INSERT_LIBRARIES=str(lib),MACH_SAMPLE_OUTPUT=str(OUT/(label+'.csv')),MACH_SAMPLE_INTERVAL_US=str(rate),MACH_SAMPLE_PARENT_PID=str(os.getpid()))
  before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic();p=subprocess.run([str(target)],env=env,capture_output=True,text=True,timeout=15);after=resource.getrusage(resource.RUSAGE_CHILDREN)
  (OUT/(label+'.stdout')).write_text(p.stdout);(OUT/(label+'.stderr')).write_text(p.stderr)
  match=re.search(r'PASS hot_cpu=([\d.]+) cool_cpu=([\d.]+)',p.stdout)
  if p.returncode or not match:raise RuntimeError('guest failed '+label)
  hot,cool=map(float,match.groups());r=dict(label=label,workload=work,interval_us=rate,expected_cool_share=cool/(hot+cool),target_cpu_seconds=hot+cool,process_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,wall_seconds=time.monotonic()-start,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
  if rate:
   a=analyze(OUT/(label+'.csv'),args.arch);w=dict(a['weighted_cpu_us']);hotw=sum(n for s,n in w.items() if s.startswith('hot_leaf '));coolw=sum(n for s,n in w.items() if s.startswith('cool_leaf '))
   raw=dict(a['raw_counts']);hotn=sum(n for s,n in raw.items() if s.startswith('hot_leaf '));cooln=sum(n for s,n in raw.items() if s.startswith('cool_leaf '))
   r.update(samples=a['samples'],weighted_cool_share=coolw/(hotw+coolw) if hotw+coolw else None,raw_cool_share=cooln/(hotn+cooln) if hotn+cooln else None,attributed_cpu_us=a['attributed_cpu_us'],observed_thread_cpu_us=a['observed_thread_cpu_us'],unresolved_cpu_us=a['unresolved_attributed_cpu_us'],failures=a['stats']['failures'])
   r['error']=r['weighted_cool_share']-r['expected_cool_share'] if r['weighted_cool_share'] is not None else None
  rows.append(r);(OUT/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print(r,flush=True)
finally:
 (OUT/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print(OUT,flush=True)
