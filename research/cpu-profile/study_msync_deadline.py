#!/usr/bin/env python3
"""Prepare an unapplied, source-extracted msync deadline experiment; no engine writes."""
import difflib,hashlib,json,subprocess
from pathlib import Path
h=Path(__file__).resolve().parent;root=h.parents[2];source=root/'bo2-local/source/winecx/dlls/ntdll/unix/msync.c'
out=root/'bo2-local/profiling/msync-deadline';out.mkdir(parents=True,exist_ok=True)
s=source.read_text();start=s.index('    NtQuerySystemTime( &now );',s.index('NTSTATUS msync_wait_objs('));end=s.index('\n    for (i = 0;',start);baseline=s[start:end]
variant=baseline.replace('    NtQuerySystemTime( &now );\n','',1).replace('        else\n            end = now.QuadPart - timeout->QuadPart;', '        else\n        {\n            NtQuerySystemTime( &now );\n            end = now.QuadPart - timeout->QuadPart;\n        }')
assert variant!=baseline and variant.count('NtQuerySystemTime')==1
patched=s[:start]+variant+s[end:];patch=''.join(difflib.unified_diff(s.splitlines(True),patched.splitlines(True),fromfile='a/dlls/ntdll/unix/msync.c',tofile='b/dlls/ntdll/unix/msync.c'))
(out/'candidate.patch').write_text(patch);(out/'baseline-prefix.c').write_text(baseline);(out/'candidate-prefix.c').write_text(variant)
header=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <limits.h>
typedef union {int64_t QuadPart;} LARGE_INTEGER;
#define TIMEOUT_INFINITE INT64_MAX
static unsigned calls;static int fixed_clock;
__attribute__((noinline)) static void NtQuerySystemTime(LARGE_INTEGER *now){
 if(fixed_clock){calls++;now->QuadPart=1000000;return;}
 struct timespec t;clock_gettime(CLOCK_REALTIME,&t);now->QuadPart=(int64_t)t.tv_sec*10000000+t.tv_nsec/100;
}
'''
functions=''
for name,body in [('baseline',baseline),('candidate',variant)]:
 functions+='__attribute__((noinline)) static uint64_t '+name+'(const LARGE_INTEGER *timeout){LARGE_INTEGER now;uint64_t end=0;'+body+'\nreturn timeout?end:0;}\n'
main=r'''
static double ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (t.tv_sec*1e9+t.tv_nsec);}
int main(void){
 LARGE_INTEGER values[]={{TIMEOUT_INFINITE},{1},{999999},{1000000},{1000001},{INT64_MAX-1},{0},{-1},{-10000},{-1000000000}};
 fixed_clock=1;unsigned cases=0;
 for(unsigned i=0;i<=sizeof(values)/sizeof(values[0]);i++){
  LARGE_INTEGER *t=i==sizeof(values)/sizeof(values[0])?NULL:&values[i];calls=0;uint64_t b=baseline(t);unsigned bc=calls;calls=0;uint64_t c=candidate(t);unsigned cc=calls;
  unsigned expected=t&&t->QuadPart!=TIMEOUT_INFINITE&&t->QuadPart<=0;
  if(b!=c||bc!=1||cc!=expected){fprintf(stderr,"FAIL case %u\n",i);return 1;}cases++;
 }
 fprintf(stderr,"PASS %u deadline cases; query counts as expected\n",cases);fixed_clock=0;
 volatile uint64_t sink=0;unsigned n=300000;
 for(unsigned round=0;round<8;round++)for(unsigned mode=0;mode<4;mode++)for(unsigned j=0;j<2;j++){
  unsigned candidate_first=round%2;unsigned which=j^candidate_first;
  uint64_t (*fn)(const LARGE_INTEGER *)=which?candidate:baseline;
  LARGE_INTEGER value=mode==0?(LARGE_INTEGER){TIMEOUT_INFINITE}:mode==1?(LARGE_INTEGER){2000000}: (LARGE_INTEGER){-10000};
  const LARGE_INTEGER *input=mode==3?NULL:&value;
  double begin=ns();for(unsigned k=0;k<n;k++){sink^=fn(input);__asm__ volatile("" : "+m"(sink));}double elapsed=ns()-begin;
  printf("%u,%u,%s,%.6f\n",round,mode,which?"candidate":"baseline",elapsed/n);
 }
 fprintf(stderr,"sink=%llu\n",(unsigned long long)sink);return 0;
}
'''
fixture=out/'deadline-study.c';fixture.write_text(header+functions+main);binary=out/'deadline-study'
command=['clang','-arch','x86_64','-O2','-g','-Wall','-Wextra','-Werror',str(fixture),'-o',str(binary)]
subprocess.run(command,check=True);r=subprocess.run([str(binary)],capture_output=True,text=True,check=True);(out/'measurements.csv').write_text('round,mode,variant,ns_per_call\n'+r.stdout);(out/'correctness.txt').write_text(r.stderr)
assembly=subprocess.run(['/usr/bin/objdump','-d',str(binary)],capture_output=True,text=True,check=True).stdout;(out/'fixture.asm').write_text(assembly)
installed=root/'bo2-local/engine/lib/wine/x86_64-unix/ntdll.so';listing=subprocess.run(['/usr/bin/objdump','-d','--start-address=0x1d000','--stop-address=0x1d0a1',str(installed)],capture_output=True,text=True,check=True).stdout;(out/'installed-prefix.asm').write_text(listing)
manifest={'scope':'Source-extracted deadline prefix only; not full Wine synchronization or gameplay validation','source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'engine_sha256':hashlib.sha256(installed.read_bytes()).hexdigest(),'compile':command,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [fixture,binary,out/'candidate.patch']},'correctness':r.stderr,'applied':False}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
