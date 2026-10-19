#!/usr/bin/env python3
"""Run the synchronized collector against our disposable Metal fixture only."""
import datetime,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
h=Path(__file__).resolve().parent;private=h.parents[2]/'bo2-local/profiling/address-recovery'
session=private/datetime.datetime.now(datetime.timezone.utc).strftime('pacing-fixture-%Y%m%dT%H%M%SZ');session.mkdir(parents=True)
lib=h/'tools/mach-sampler-synced.dylib';fixture=h/'tools/pacing-fixture'
meta={'purpose':'Disposable open-source Metal fixture, not gameplay','synchronized_markers':True,'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [lib,fixture,h/'pacing_fixture.m']}}
for p in [lib,fixture,h/'pacing_fixture.m',h/'tools/mach_sampler_synced.c']:shutil.copy2(p,session/p.name)
(session/'launch.json').write_text(json.dumps(meta,indent=2)+'\n')
env=os.environ.copy()
for k in list(env):
 if k.startswith('MACH_SAMPLE_'):del env[k]
env.update(DYLD_INSERT_LIBRARIES=str(lib),MACH_SAMPLE_OUTPUT=str(session/'samples'),MACH_SAMPLE_TRIGGER=str(session/'capture.trigger'),MACH_SAMPLE_SECONDS='3',MACH_SAMPLE_INTERVAL_US='5000')
with (session/'fixture.log').open('w') as log:
 child=subprocess.Popen([str(fixture)],env=env,stdout=log,stderr=subprocess.STDOUT)
 print('Fixture PID:',child.pid,'session:',session,flush=True)
 try:
  result=subprocess.run([sys.executable,str(h/'capture_pacing.py'),'record','--pid',str(child.pid),'--mode','combined','--session',str(session),'--delay','2'],timeout=160)
  meta['capture_exit_code']=result.returncode
 finally:
  # The fixture exits itself after 60 seconds. No existing process is terminated.
  try:meta['fixture_exit_code']=child.wait(timeout=70)
  except subprocess.TimeoutExpired:
   child.terminate();meta['fixture_exit_code']=child.wait(timeout=10);meta['fixture_cleanup']='terminated only our Popen child after fixture self-exit timeout'
  meta['sample_outputs']=[p.name for p in session.glob('samples.*')];(session/'validation.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Fixture validation outputs:',session)
