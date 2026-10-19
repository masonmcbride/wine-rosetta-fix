#!/usr/bin/env python3
"""Derive a narrow local template from installed Xcode; do not redistribute it."""
import argparse,copy,hashlib,json,plistlib
from pathlib import Path
PACKAGES=Path('/Applications/Xcode.app/Contents/Applications/Instruments.app/Contents/Packages')
BASE=PACKAGES/'GPU.instrdst/Contents/Templates/Game Performance.tracetemplate'
TYPES={'display':'com.apple.xray.instrument-type.metal-display','states':'com.apple.xray.instrument-type.kdebug.ctxswitches','markers':'com.apple.xray.instrument-type.poi'}

def narrow(archive,keep):
    x=copy.deepcopy(archive);o=x['$objects'];top=x['$top'];count=o[top['$0'].data];pairs=[]
    for i in range(count):
        label=o[top[f'${2*i+1}'].data];name=label['NS.string']
        if name in keep:pairs.append((top[f'${2*i+1}'],top[f'${2*i+2}']))
    if {o[a.data]['NS.string'] for a,b in pairs}!=keep:raise ValueError('Installed template lacks required instruments')
    for k in list(top):
        if k.startswith('$') and k[1:].isdigit():del top[k]
    o.append(len(pairs));top['$0']=plistlib.UID(len(o)-1)
    for i,(a,b) in enumerate(pairs):top[f'${2*i+1}']=a;top[f'${2*i+2}']=b
    stub=o[top['stubInfoByUUID'].data];pairs=[(a,b) for a,b in zip(stub['NS.keys'],stub['NS.objects']) if o[a.data] in keep]
    stub['NS.keys']=[a for a,b in pairs];stub['NS.objects']=[b for a,b in pairs]
    return x

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--display-only',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    keep={TYPES['display'],TYPES['markers']}
    if not a.display_only:keep.add(TYPES['states'])
    original=BASE.read_bytes();result=plistlib.dumps(narrow(plistlib.loads(original),keep),fmt=plistlib.FMT_BINARY)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(result)
    a.output.with_suffix('.json').write_text(json.dumps({'base':str(BASE),'base_sha256':hashlib.sha256(original).hexdigest(),'sha256':hashlib.sha256(result).hexdigest(),'instruments':sorted(keep),'validation':'Requires a real recording and export; reduced instrument count is not an overhead measurement'},indent=2)+'\n')
    print(a.output)
