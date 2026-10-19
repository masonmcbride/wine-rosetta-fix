#!/usr/bin/env python3
"""Attach COFF function names only at exact byte-verified entry addresses.

No nearest-symbol or inferred-end guesses. Off-entry samples stay unresolved.
"""
import argparse,collections,json,struct
from pathlib import Path

def entries(data):
    nt=struct.unpack_from('<I',data,60)[0];pos,count=struct.unpack_from('<II',data,nt+12);optional=struct.unpack_from('<H',data,nt+20)[0];opt=nt+24
    if data[nt:nt+4]!=b'PE\0\0' or struct.unpack_from('<H',data,nt+4)[0]!=0x14c:raise ValueError('Expected i386 PE')
    base=struct.unpack_from('<I',data,opt+28)[0];nsec=struct.unpack_from('<H',data,nt+6)[0];sections=[struct.unpack_from('<I',data,opt+optional+i*40+12)[0] for i in range(nsec)]
    strings=pos+count*18
    if strings+4>len(data):raise ValueError('Missing COFF string table')
    length=struct.unpack_from('<I',data,strings)[0]
    if strings+length>len(data):raise ValueError('Truncated COFF string table')
    found=collections.defaultdict(list);i=0
    while i<count:
        off=pos+i*18;raw=data[off:off+8];value,section,kind,storage,aux=struct.unpack_from('<IhHBB',data,off+8)
        if raw[:4]==b'\0'*4:
            index=struct.unpack_from('<I',raw,4)[0]
            if not 4<=index<length:raise ValueError('Invalid COFF name offset')
            name=data[strings+index:strings+length].split(b'\0',1)[0].decode('utf-8','replace')
        else:name=raw.split(b'\0',1)[0].decode('utf-8','replace')
        if kind&0x30==0x20 and 1<=section<=nsec:found[base+sections[section-1]+value].append(name)
        if i+aux>=count:raise ValueError('Truncated COFF auxiliary records')
        i+=1+aux
    return found

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('attribution',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=json.loads(a.attribution.read_text());image=Path(r['image'])
    import hashlib
    data=image.read_bytes()
    if hashlib.sha256(data).hexdigest()!=r['sha256']:raise SystemExit('Attribution image changed')
    names=entries(data);counts=collections.Counter()
    for row in r['addresses']:
        if row['status'].startswith('verified_'):
            matches=names.get(int(row['static_address'],16),[])
            if matches:row['coff_function_entry_symbols']=matches;counts[tuple(matches)]+=row['samples']
    r['coff_exact_entry_sample_count']=sum(counts.values());r['coff_exact_entries']=[{'symbols':list(k),'samples':v} for k,v in counts.most_common()];r['limits'].append('COFF names attached only at exact function entries; no source lines or containing-function bounds inferred')
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'samples_at_verified_function_entries':sum(counts.values()),'top_entries':r['coff_exact_entries'][:12]},indent=2))
