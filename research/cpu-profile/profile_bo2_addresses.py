#!/usr/bin/env python3
"""Prepare/launch opt-in, manually triggered 3-second address recovery.

Never terminates a game or bypasses the original launcher's active-bottle guard.
No recording starts until the trigger subcommand is run. Raw output is private.
"""
import argparse,datetime,hashlib,json,os,subprocess
from pathlib import Path
from wine_profile_launch import wrapper_command
h=Path(__file__).resolve().parent;root=h.parents[2]
private=root/'bo2-local/profiling/address-recovery'
lib=h/'tools/mach-sampler-images.dylib'
p=argparse.ArgumentParser(description=__doc__)
s=p.add_subparsers(dest='action',required=True);s.add_parser('plan');launch=s.add_parser('launch');launch.add_argument('--synced',action='store_true',help='Use separate clock-marker sampler for synchronized capture')
t=s.add_parser('trigger');t.add_argument('session',type=Path)
a=p.parse_args()
if a.action=='plan':
 print('Launch uses the original bo2/run-bo2.sh and preserves its debug-register options.')
 print('Requires a game restart; the launcher refuses an already-active bottle.')
 print('Preloads only the research library; waits up to 10 minutes for a manual trigger.')
 print('Trigger requests 3 seconds at 5 ms cadence; each Wine host has a separate output.')
 print('Validated on a PE32 fixture; gameplay fidelity, perturbation and module lifetime remain unvalidated.')
 raise SystemExit(0)
if a.action=='trigger':
 session=a.session.resolve()
 if session.parent!=private.resolve() or not (session/'launch.json').is_file():raise SystemExit('Not a prepared local session')
 path=session/'capture.trigger'
 with path.open('x') as f:f.write('capture requested\n')
 print('Capture requested; poll jitter/startup may affect actual start. Check per-process outputs and stats.')
 raise SystemExit(0)
if a.synced:lib=h/'tools/mach-sampler-synced.dylib'
if os.environ.get('DYLD_INSERT_LIBRARIES'):raise SystemExit('An existing preload is configured; review it before combining profilers')
build=json.loads((h/'tools'/('synced-sampler-build.json' if a.synced else 'image-sampler-build.json')).read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for f in [h/'mach_sampler.c',h/'sample_image_resolver.h',h/'tools'/('mach_sampler_synced.c' if a.synced else 'mach_sampler_images.c'),lib]:
 if build['sha256'].get(f.name)!=sha(f):raise SystemExit('Stale image-sampler build')
session=private/datetime.datetime.now(datetime.timezone.utc).strftime('zombies-%Y%m%dT%H%M%SZ');session.mkdir(parents=True)
env=os.environ.copy()
for k in list(env):
 if k.startswith('MACH_SAMPLE_'):del env[k]
env.update(DYLD_INSERT_LIBRARIES=str(lib),MACH_SAMPLE_OUTPUT=str(session/'samples'),MACH_SAMPLE_TRIGGER=str(session/'capture.trigger'),MACH_SAMPLE_SECONDS='3',MACH_SAMPLE_DELAY='0',MACH_SAMPLE_INTERVAL_US='5000')
launcher=root/'wine-rosetta-fix/bo2/run-bo2.sh'
meta={'purpose':'Experimental gameplay original-PC mapping, not validated function-cost profiling','session':str(session),'image_sampler_build':build,'before_sha256':{str(f):sha(f) for f in [launcher,root/'bo2-local/engine/lib/wine/x86_64-unix/ntdll.so']},'launch_strategy':'set preload after protected-shell startup and source unchanged wrapper','synchronized_markers':a.synced,'trigger_required':True,'seconds':3,'interval_us':5000,'status':'launch requested; success/game readiness not established'}
with (session/'launcher.private.log').open('w') as log:child=subprocess.Popen(wrapper_command(launcher,lib),env=env,stdout=log,stderr=log,start_new_session=True)
meta['launcher_pid']=child.pid;(session/'launch.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Session:',session);print('Launcher PID:',child.pid);print('After gameplay is ready, run:');print('python3',Path(__file__).name,'trigger',session)
