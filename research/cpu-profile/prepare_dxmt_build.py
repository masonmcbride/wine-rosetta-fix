#!/usr/bin/env python3
"""Prepare a native PE32 DXMT build reusing the installed bridge at its DLL ABI.

No installed DLL is modified. Upstream i386 shader-compiler forwarding is retained.
"""
import difflib,hashlib,json,re,struct,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[2]
SOURCE=ROOT/'bo2-local/source/dxmt-v0.80';OUT=ROOT/'bo2-local/dxmt-build';OUT.mkdir(parents=True,exist_ok=True)
IMAGE=ROOT/'bo2-local/engine/lib/wine/i386-windows/winemetal.dll'
def exports(data):
    nt=struct.unpack_from('<I',data,60)[0];opt=nt+24
    if data[nt:nt+4]!=b'PE\0\0' or struct.unpack_from('<H',data,nt+4)[0]!=0x14c:raise ValueError('Expected PE32 i386 bridge')
    count=struct.unpack_from('<H',data,nt+6)[0];size=struct.unpack_from('<H',data,nt+20)[0];sections=[struct.unpack_from('<IIII',data,opt+size+i*40+8) for i in range(count)]
    def off(rva,length=1):
        for vs,va,rawsize,raw in sections:
            if va<=rva and rva+length<=va+rawsize and raw+rva-va+length<=len(data):return raw+rva-va
        raise ValueError('Unmapped export RVA')
    rva,n=struct.unpack_from('<II',data,opt+96);p=off(rva,40);base,numfunc,names,functions,namesptr,ordinals=struct.unpack_from('<IIIIII',data,p+16);result=[]
    for i in range(names):
        nameoff=off(struct.unpack_from('<I',data,off(namesptr,4*names)+i*4)[0]);end=data.index(b'\0',nameoff);name=data[nameoff:end].decode('ascii');ordinal=base+struct.unpack_from('<H',data,off(ordinals,2*names)+i*2)[0]
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9@]*',name):raise ValueError('Unsupported export name')
        result.append((name,ordinal))
    return result

def original(path):return subprocess.check_output(['git','-C',str(SOURCE),'show','HEAD:'+path],text=True)
def apply_boundary(path,updated):
    base=original(path);p=SOURCE/path
    if p.read_text() not in [base,updated]:raise RuntimeError('Research file already modified: '+path)
    p.write_text(updated);return ''.join(difflib.unified_diff(base.splitlines(True),updated.splitlines(True),fromfile='a/'+path,tofile='b/'+path))

if __name__=='__main__':
    data=IMAGE.read_bytes();names=exports(data);definition=OUT/'winemetal.def';library=OUT/'libwinemetal.a'
    definition.write_text('LIBRARY winemetal.dll\nEXPORTS\n'+''.join(f'  {n} @{o}\n' for n,o in names))
    subprocess.run(['i686-w64-mingw32-dlltool','-m','i386','-d',str(definition),'-l',str(library)],check=True)
    opt=original('meson.options');option="\noption('external_winemetal_import', type : 'string', value : '')\n"
    wrapper="""# Optional boundary: retain the installed Wine/Metal bridge and shader translator.
external_bridge = get_option('external_winemetal_import')
if external_bridge != ''
  if cpu_family != 'x86' or wine_builtin_dll
    error('External bridge mode requires native i386 PE DLLs')
  endif
  winemetal_dep = declare_dependency(
    link_args : [external_bridge],
    include_directories : [include_directories('.')],
  )
else
"""
    patch=apply_boundary('meson.options',opt+option)+apply_boundary('src/winemetal/meson.build',wrapper+original('src/winemetal/meson.build')+'\nendif\n')
    (OUT/'external-bridge.patch').write_text(patch)
    receipt={'bridge_sha256':hashlib.sha256(data).hexdigest(),'exports':len(names),'import_archive':str(library),'upstream_commit':subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip(),'boundary':'Generated import library only; preserve original bridge DLL and Unix Metal/shader translator','engine_modified':False}
    (OUT/'boundary.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
