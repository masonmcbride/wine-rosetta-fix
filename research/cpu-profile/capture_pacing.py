#!/usr/bin/env python3
"""Bounded delayed capture; default plan is read-only. Never terminates the game."""
import argparse,ctypes,datetime,hashlib,json,os,subprocess,time,uuid
from pathlib import Path
H=Path(__file__).resolve().parent
PRIVATE=H.parents[2]/'bo2-local/profiling'

def command(pid,mode,output,notification):
    template=PRIVATE/'synchronized'/('display-control.tracetemplate' if mode=='display' else 'pacing.tracetemplate')
    return ['xcrun','xctrace','record','--template',str(template),'--attach',str(pid),'--time-limit','5s','--output',str(output),'--notify-tracing-started',notification]

class ReadyNotification:
    def __init__(self,name):
        self.lib=ctypes.CDLL('/usr/lib/system/libsystem_notify.dylib');self.token=ctypes.c_int()
        if self.lib.notify_register_check(name.encode(),ctypes.byref(self.token)):raise RuntimeError('Cannot register tracing-ready notification')
        self.check() # Initial check is set; clear it before starting recorder.
    def check(self):
        changed=ctypes.c_int()
        if self.lib.notify_check(self.token,ctypes.byref(changed)):raise RuntimeError('Cannot check tracing-ready notification')
        return bool(changed.value)
    def close(self):self.lib.notify_cancel(self.token)

def validate_session(session):
    if session.resolve().parent!=(PRIVATE/'address-recovery').resolve():raise ValueError('Expected private address-recovery session')
    meta=json.loads((session/'launch.json').read_text())
    if not meta.get('synchronized_markers'):raise ValueError('Relaunch with --synced; older library has no clock markers')
    if (session/'capture.trigger').exists():raise ValueError('One-shot sampler already triggered; do not reuse it')
    if time.time()-(session/'launch.json').stat().st_mtime>540:raise ValueError('Trigger may expire soon; prepare a fresh session')
    return meta

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','record']);p.add_argument('--pid',type=int,required=True);p.add_argument('--mode',choices=['display','states','combined'],default='combined');p.add_argument('--session',type=Path);p.add_argument('--delay',type=float,default=15);a=p.parse_args()
    if a.pid<=0 or not 0<=a.delay<=60:p.error('Positive PID and delay in 0..60 seconds required')
    if a.mode=='combined':
        if not a.session:p.error('Combined mode requires a fresh --synced launch session')
        validate_session(a.session)
    name='com.mason.wine-profile.ready.'+uuid.uuid4().hex
    output=PRIVATE/'synchronized'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')/('capture-'+a.mode+'.trace')
    cmd=command(a.pid,a.mode,output,name)
    if a.action=='plan':print(json.dumps({'command':cmd,'delay_seconds':a.delay,'limits':'Five-second trace around a three-second CPU pilot. Overhead and complete frame/state coverage require validation. Combined trigger waits for recorder notification.'},indent=2));raise SystemExit()
    output.parent.mkdir(parents=True,exist_ok=False);env=os.environ.copy();env['DEVELOPER_DIR']='/Applications/Xcode.app/Contents/Developer'
    template=Path(cmd[cmd.index('--template')+1])
    metadata={'template_sha256':hashlib.sha256(template.read_bytes()).hexdigest(),'pid':a.pid,'mode':a.mode,'command':cmd,'delay_seconds':a.delay,'status':'waiting','session':str(a.session) if a.session else None,'trace_seconds':5}
    def save():(output.parent/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    save();print('Return to gameplay; recorder starts after',a.delay,'seconds.',flush=True);time.sleep(a.delay)
    ready=ReadyNotification(name)
    try:
        with (output.parent/'recorder.log').open('w') as log:
            child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+45
                while not ready.check():
                    if child.poll() is not None:raise RuntimeError('Recorder exited before readiness; inspect recorder.log')
                    if time.monotonic()>deadline:raise RuntimeError('No recorder-ready notification; sampler not triggered')
                    time.sleep(.05)
                metadata['ready_monotonic']=time.monotonic();metadata['status']='recorder ready'
                if a.mode=='combined':
                    validate_session(a.session)
                    with (a.session/'capture.trigger').open('x') as f:f.write('synchronized capture requested\n')
                    metadata['trigger_monotonic']=time.monotonic()
                save();print('Recorder ready; capture requested.',flush=True)
                metadata['recorder_exit_code']=child.wait(timeout=90)
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
        if not output.is_dir():raise RuntimeError('Recorder produced no trace bundle; inspect recorder.log')
        metadata['status']='recording ended; export and clock/frame coverage validation required';save()
        print('Saved:',output,flush=True)
    except Exception as e:
        metadata['status']='failed';metadata['error']=str(e);save();raise
    finally:ready.close()
