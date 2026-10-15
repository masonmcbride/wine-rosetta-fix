#!/usr/bin/env python3
"""Build experimental Mach sampler and standalone validators, never Wine."""
import hashlib,json,pathlib,subprocess
H=pathlib.Path(__file__).resolve().parent;rows=[]
(H/'tools').mkdir(exist_ok=True)
for arch in ['arm64','x86_64']:
 commands=[['clang','-O2','-g','-Wall','-Wextra','-Werror','-arch',arch,'-dynamiclib',str(H/'mach_sampler.c'),'-o',str(H/f'tools/mach-sampler-{arch}.dylib')]]
 for work in ['shares','mix']:
  commands.append(['clang','-O2','-g','-Wall','-Wextra','-Werror','-arch',arch,'-fno-omit-frame-pointer','-fno-optimize-sibling-calls',str(H/f'calibrate_{work}.c'),'-o',str(H/f'tools/calibrate-{work}-{arch}')])
 for command in commands:
  subprocess.run(command,check=True);p=pathlib.Path(command[-1]);rows.append(dict(command=command,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(H/'mach-build.json').write_text(json.dumps(dict(compiler=subprocess.run(['clang','--version'],capture_output=True,text=True,check=True).stdout,builds=rows,source_hashes={f:hashlib.sha256((H/f).read_bytes()).hexdigest() for f in ['mach_sampler.c','calibrate_shares.c','calibrate_mix.c']}),indent=2)+'\n')
