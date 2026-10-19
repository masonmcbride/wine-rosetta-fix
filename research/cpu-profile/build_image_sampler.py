#!/usr/bin/env python3
"""Generate an identity-aware experimental sampler without altering validated core."""
import hashlib,json,subprocess
from pathlib import Path
h=Path(__file__).resolve().parent;(h/'tools').mkdir(exist_ok=True)
s=(h/'mach_sampler.c').read_text()
start=s.index(' for(unsigned i=0;i<used;i++){\n  Dl_info d={0};')
end=s.index('\n fclose(f);char path[4096];',start)
s=s[:start]+' for(unsigned i=0;i<used;i++)write_identity_sample(f,&samples[i]);'+s[end:]
s=s.replace('static void dump(double wall){','#include "sample_image_resolver.h"\nstatic void dump(double wall){')
s=s.replace('pc,base,module,tid,time,user_us,system_us\\n','pc,base,module,tid,time,user_us,system_us,kind,cpu_type,instruction_bytes\\n')
s=s.replace('static const char *output;','static const char *output;\nstatic char pid_output[4096];')
s=s.replace('output=getenv("MACH_SAMPLE_OUTPUT");if(!output)return;','output=getenv("MACH_SAMPLE_OUTPUT");if(!output)return;\n if(snprintf(pid_output,sizeof(pid_output),"%s.%d.csv",output,getpid())>=(int)sizeof(pid_output))return;\n output=pid_output;')
s=s.replace('wait_seconds(delay_seconds);double start=now();', 'const char *trigger=getenv("MACH_SAMPLE_TRIGGER"); if(trigger){double deadline=now()+600;while(access(trigger,F_OK)&&!atomic_load(&stopping)&&now()<deadline)wait_seconds(0.2);if(atomic_load(&stopping)||access(trigger,F_OK)){mach_port_deallocate(mach_task_self(),self);return NULL;}}\n wait_seconds(delay_seconds);double start=now();')
generated=h/'tools/mach_sampler_images.c';generated.write_text(s)
command=['clang','-arch','x86_64','-O2','-g','-Wall','-Wextra','-Werror','-dynamiclib','-I',str(h),str(generated),'-o',str(h/'tools/mach-sampler-images.dylib')]
subprocess.run(command,check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(h/'tools/image-sampler-build.json').write_text(json.dumps({'command':command,'sha256':{p.name:sha(p) for p in [h/'mach_sampler.c',h/'sample_image_resolver.h',generated,h/'tools/mach-sampler-images.dylib']}},indent=2)+'\n')
