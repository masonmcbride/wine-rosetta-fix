#!/usr/bin/env python3
"""Add bounded signpost/clock anchors to a separate generated sampler variant."""
import hashlib,json,subprocess
from pathlib import Path
h=Path(__file__).resolve().parent;tools=h/'tools'
source=tools/'mach_sampler_images.c';manifest=json.loads((tools/'image-sampler-build.json').read_text())
if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['sha256'][source.name]:raise SystemExit('Stale generated source; rebuild image sampler first')
s=source.read_text();s=s.replace('#include <time.h>','#include <time.h>\n#include <os/signpost.h>')
s=s.replace('static double window_user,window_system;', '''static double window_user,window_system;
static double sync_start,sync_end,marker_before,marker_after,end_marker_before,end_marker_after;
static int start_marker_enabled,end_marker_enabled;
static os_log_t sync_log;
static void dump_sync(void){
 char path[4096];snprintf(path,sizeof(path),"%s.sync.json",output);
 FILE *f=fopen(path,"w");if(!f)return;
 fprintf(f,"{\\"pid\\":%d,\\"clock\\":\\"CLOCK_MONOTONIC\\",\\"sample_start\\":%.9f,\\"sample_end\\":%.9f,\\"start_marker_before\\":%.9f,\\"start_marker_after\\":%.9f,\\"end_marker_before\\":%.9f,\\"end_marker_after\\":%.9f,\\"start_marker_enabled\\":%d,\\"end_marker_enabled\\":%d}\\n",getpid(),sync_start,sync_end,marker_before,marker_after,end_marker_before,end_marker_after,start_marker_enabled,end_marker_enabled);
 fclose(f);
}''')
old='wait_seconds(delay_seconds);double start=now();'
assert s.count(old)==1
s=s.replace(old,'''wait_seconds(delay_seconds);
 sync_log=os_log_create("com.mason.wine-profile",OS_LOG_CATEGORY_POINTS_OF_INTEREST);
 double start=now();sync_start=start;marker_before=now();start_marker_enabled=os_signpost_enabled(sync_log);
 os_signpost_event_emit(sync_log,OS_SIGNPOST_ID_EXCLUSIVE,"WineSampleStart","pid=%d",getpid());marker_after=now();''')
s=s.replace('double wall=now()-start;getrusage', '''sync_end=now();end_marker_before=now();end_marker_enabled=os_signpost_enabled(sync_log);
 os_signpost_event_emit(sync_log,OS_SIGNPOST_ID_EXCLUSIVE,"WineSampleEnd","pid=%d",getpid());end_marker_after=now();
 double wall=sync_end-start;getrusage''')
s=s.replace('dump(wall);return NULL;','dump(wall);dump_sync();return NULL;')
generated=tools/'mach_sampler_synced.c';generated.write_text(s);lib=tools/'mach-sampler-synced.dylib'
command=['clang','-arch','x86_64','-O2','-g','-Wall','-Wextra','-Werror','-dynamiclib','-I',str(h),str(generated),'-o',str(lib)];subprocess.run(command,check=True)
files=[h/'mach_sampler.c',h/'sample_image_resolver.h',generated,lib]
(tools/'synced-sampler-build.json').write_text(json.dumps({'command':command,'base_build':manifest,'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},indent=2)+'\n');print(lib)
