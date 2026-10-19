#!/usr/bin/env python3
"""Run only our source-built 32-bit fixture in a separate research prefix."""
import datetime,hashlib,json,os,subprocess,select
from pathlib import Path
h=Path(__file__).resolve().parent;root=h.parents[2];engine=root/'bo2-local/engine'
out=root/'bo2-local/profiling/address-recovery'/datetime.datetime.now(datetime.timezone.utc).strftime('pe32-%Y%m%dT%H%M%SZ');out.mkdir(parents=True)
exe=h/'tools/calibrate-pe32.exe';lib=h/'tools/mach-sampler-images.dylib'
env=os.environ.copy()
for k in list(env):
 if k.startswith(('WINE','MACH_SAMPLE_')) or k=='DYLD_INSERT_LIBRARIES':del env[k]
env.update(WINEPREFIX=str(h/'prefix'),WINESERVER=str(engine/'bin/wineserver'),WINELOADER=str(engine/'bin/wine64'),WINEDEBUG='-all',WINEMSYNC='1',WINEESYNC='1',WINEFSYNC='0',WINE_ROSETTA_EXEC_BREAKPOINTS='0',WINE_ROSETTA_WOW64_BREAKPOINTS='0',WINE_ROSETTA_CALL_WORKAROUND='0',WINEDLLOVERRIDES='mscoree,mshtml=',DYLD_FALLBACK_LIBRARY_PATH=str(engine/'lib')+':/usr/lib')
# Warm this dedicated research prefix without the profiler.
r=subprocess.run([str(engine/'bin/wine64'),str(exe)],env=env,capture_output=True,text=True,timeout=60)
(out/'control.stdout').write_text(r.stdout);(out/'control.stderr').write_text(r.stderr)
if r.returncode or 'PASS ' not in r.stdout:raise RuntimeError('control failed')
env.update(DYLD_INSERT_LIBRARIES=str(lib),MACH_SAMPLE_OUTPUT=str(out/'samples.csv'),MACH_SAMPLE_DELAY='0',MACH_SAMPLE_TRIGGER=str(out/'capture.trigger'),MACH_SAMPLE_SECONDS='3',MACH_SAMPLE_INTERVAL_US='5000')
files=[h/'calibrate_pe32.c',h/'mach_sampler.c',exe,lib,engine/'lib/wine/x86_64-unix/ntdll.so']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={str(p):sha(p) for p in files}
build=json.loads((h/'tools/image-sampler-build.json').read_text())
assert build['sha256'][lib.name]==sha(lib)
assert build['sha256']['sample_image_resolver.h']==sha(h/'sample_image_resolver.h')
(out/'image-sampler-build.json').write_text(json.dumps(build,indent=2)+'\n')
(out/'calibrate_pe32.c').write_bytes((h/'calibrate_pe32.c').read_bytes())
(out/'sample_image_resolver.h').write_bytes((h/'sample_image_resolver.h').read_bytes())
(out/'mach_sampler_images.c').write_bytes((h/'tools/mach_sampler_images.c').read_bytes())
p=subprocess.Popen([str(engine/'bin/wine64'),str(exe)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 if not select.select([p.stdout],[],[],30)[0]:raise RuntimeError('fixture readiness timeout')
 ready=p.stdout.readline()
 if not ready.startswith('READY bits=32'):raise RuntimeError('fixture not ready')
 (out/'capture.trigger').touch()
 stdout,stderr=p.communicate(timeout=40)
 r=subprocess.CompletedProcess(p.args,p.returncode,ready+stdout,stderr)
finally:
 if p.poll() is None:p.terminate();p.wait(timeout=5)
(out/'profile.stdout').write_text(r.stdout);(out/'profile.stderr').write_text(r.stderr)
meta={'purpose':'Validate original PE32 PCs only, no game process','exit':r.returncode,'before':before,'after':{str(p):sha(p) for p in files}}
(out/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n');print(out);print(r.stdout)
if r.returncode or 'PASS ' not in r.stdout or not list(out.glob('samples.csv.*.csv')):raise RuntimeError('profile failed')
