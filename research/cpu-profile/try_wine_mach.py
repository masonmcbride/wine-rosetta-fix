#!/usr/bin/env python3
"""Per-thread CPU-accounted Mach snapshots of only the MIT Wine event guest."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--diagnostic-only',action='store_true')
args=parser.parse_args()
HERE=pathlib.Path(__file__).resolve().parent;ENGINE=HERE.parents[2]/'bo2-local/engine'
OUT=HERE/'results'/('wine-mach-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'));OUT.mkdir(parents=True)
files=[HERE/'mach_sampler.c',HERE/'events.c',HERE/'events.exe',HERE/'tools/mach-sampler-x86_64.dylib',ENGINE/'lib/wine/x86_64-unix/ntdll.so']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
build=json.loads((HERE/'build.json').read_text())
assert sha(HERE/'events.c')==build['source_sha256'] and sha(HERE/'events.exe')==build['executable_sha256']
meta=dict(hashes={str(p):sha(p) for p in files},runs=[],cpu_share_validation='see standalone Mach validation; flat endpoint attribution limits apply')
sampler_build=json.loads((HERE/'mach-build.json').read_text())
assert sampler_build['source_hashes']['mach_sampler.c']==sha(files[0])
assert next(r['sha256'] for r in sampler_build['builds'] if r['command'][-1]==str(files[3]))==sha(files[3])
meta['sampler_build']=sampler_build
(OUT/'mach_sampler.c').write_bytes(files[0].read_bytes())
env=os.environ.copy()
for k in list(env):
 if k.startswith('WINE') or k.startswith('MACH_SAMPLE_') or k=='DYLD_INSERT_LIBRARIES':del env[k]
settings=dict(WINEPREFIX=str(HERE/'prefix'),WINESERVER=str(ENGINE/'bin/wineserver'),WINEDEBUG='-all',WINEMSYNC='1',WINEESYNC='1',WINEFSYNC='0',WINE_ROSETTA_EXEC_BREAKPOINTS='0',WINE_ROSETTA_WOW64_BREAKPOINTS='0',WINE_ROSETTA_CALL_WORKAROUND='0',DYLD_FALLBACK_LIBRARY_PATH=str(ENGINE/'lib')+':/usr/lib',WINEDLLOVERRIDES='mscoree,mshtml=')
env.update(settings);meta['environment']=settings
try:
 for label in (['profile-diagnostic'] if args.diagnostic_only else ['warmup','control1','profile1','profile2','control2']):
    runenv=env.copy();seconds=2 if label=='warmup' else 15
    if label.startswith('profile'):
      runenv.update(DYLD_INSERT_LIBRARIES=str(files[3]),MACH_SAMPLE_OUTPUT=str(OUT/(label+'.csv')),MACH_SAMPLE_DELAY='3',MACH_SAMPLE_SECONDS='10',MACH_SAMPLE_INTERVAL_US='5000',MACH_SAMPLE_PARENT_PID=str(os.getpid()))
    cmd=[str(ENGINE/'bin/wine64'),str(HERE/'events.exe'),str(seconds)]
    start=time.monotonic()
    with (OUT/(label+'.stdout')).open('w') as out,(OUT/(label+'.stderr')).open('w') as err:
      p=subprocess.Popen(cmd,env=runenv,stdout=out,stderr=err)
      try:rc=p.wait(timeout=90)
      finally:
       if p.poll() is None:p.terminate();p.wait(timeout=5)
    row=dict(label=label,host_pid=p.pid,exit=rc,seconds=seconds,wall_seconds=time.monotonic()-start);meta['runs'].append(row);print(row,flush=True)
    if rc or 'PASS ' not in (OUT/(label+'.stdout')).read_text():raise RuntimeError('guest failed')
    if label.startswith('profile') and not (OUT/(label+'.csv')).is_file():raise RuntimeError('sampler did not produce output')
    if label.startswith('profile'):
      if len((OUT/(label+'.csv')).read_text().splitlines())<=1:raise RuntimeError('sampler output is empty')
      row['window_stats']=json.loads((OUT/(label+'.csv.stats.json')).read_text())
finally:
 meta['hashes_after']={str(p):sha(p) for p in files};(OUT/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print(OUT,flush=True)
