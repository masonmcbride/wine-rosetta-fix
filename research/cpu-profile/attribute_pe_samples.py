#!/usr/bin/env python3
"""Verify PE32 sample PCs against an explicit file, byte sequence, and DWARF.

Never infer an instruction boundary or function from the nearest symbol. Counts
are snapshots, not instruction cost. Byte comparisons are dump-time identity,
not proof of module lifetime throughout the sampling window.
"""
import argparse,collections,csv,hashlib,json,re,struct,subprocess
from pathlib import Path


def pe_sections(data):
    if data[:2]!=b'MZ':raise ValueError('Not a PE image')
    nt=struct.unpack_from('<I',data,60)[0]
    if data[nt:nt+4]!=b'PE\0\0' or struct.unpack_from('<H',data,nt+4)[0]!=0x14c:raise ValueError('Expected i386 PE')
    count=struct.unpack_from('<H',data,nt+6)[0];size=struct.unpack_from('<H',data,nt+20)[0];opt=nt+24
    if struct.unpack_from('<H',data,opt)[0]!=0x10b:raise ValueError('Expected PE32')
    preferred=struct.unpack_from('<I',data,opt+28)[0];sections=[]
    for i in range(count):
        off=opt+size+i*40;vs,va,rawsize,raw=struct.unpack_from('<IIII',data,off+8);flags=struct.unpack_from('<I',data,off+36)[0]
        if flags&0x20000000:sections.append((va,min(vs,rawsize),raw))
    return preferred,sections



def relocated_jump(data,rva,code,delta):
    """Verify only PE32 FF /4 absolute-indirect thunks with explicit HIGHLOW.

    Never normalize arbitrary differing bytes. Return expected loaded bytes only
    when the image's base-relocation table declares this exact 32-bit operand.
    """
    if len(code)!=6 or code[:2]!=b'\xff\x25':return None
    nt=struct.unpack_from('<I',data,60)[0];opt=nt+24
    if struct.unpack_from('<I',data,opt+92)[0]<=5:return None
    directory,size=struct.unpack_from('<II',data,opt+96+5*8)
    count=struct.unpack_from('<H',data,nt+6)[0];optional=struct.unpack_from('<H',data,nt+20)[0]
    def file_offset(address,length):
        for i in range(count):
            off=opt+optional+i*40;va,rawsize,raw=struct.unpack_from('<III',data,off+12)
            if va<=address and address+length<=va+rawsize and raw+address-va+length<=len(data):return raw+address-va
        return None
    if not directory or not size:return None
    start=file_offset(directory,size)
    if start is None:return None
    end=start+size;cursor=start;declared=[]
    while cursor<end:
        if cursor+8>end:return None
        page,block=struct.unpack_from('<II',data,cursor)
        if block<8 or block%2 or cursor+block>end:return None
        for off in range(cursor+8,cursor+block,2):
            entry=struct.unpack_from('<H',data,off)[0];kind=entry>>12;at=page+(entry&0xfff)
            if kind and at<rva+6 and at+4>rva:declared.append((kind,at))
        cursor+=block
    if declared!=[(3,rva+2)]:return None
    value=(struct.unpack_from('<I',code,2)[0]+delta)&0xffffffff
    return code[:2]+struct.pack('<I',value)


def attribute(samples,image):
    data=image.read_bytes();preferred,sections=pe_sections(data)
    dump=subprocess.run(['i686-w64-mingw32-objdump','-d','-w',str(image)],check=True,capture_output=True,text=True).stdout
    instructions={}
    for line in dump.splitlines():
        m=re.match(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*(\S.*)?$',line)
        if m and m[3]:instructions[int(m[1],16)]=(bytes.fromhex(m[2]),m[3])
    results={};status=collections.Counter();total=0
    with samples.open() as f:
        for row in csv.DictReader(f):
            total+=1;pc=int(row['pc'],16);base=int(row['base'],16);key=(pc,base,row['module'],row.get('instruction_bytes',''))
            if key in results:results[key]['samples']+=1;status[results[key]['status']]+=1;continue
            r={'runtime_pc':hex(pc),'runtime_base':hex(base),'samples':1,'status':'unresolved_module'}
            if row.get('kind')=='PE32' and row['module']!='UNKNOWN' and Path(row['module']).resolve()==image.resolve():
                address=preferred+pc-base;r['static_address']=hex(address);rva=pc-base
                section=next(((va,n,raw) for va,n,raw in sections if va<=rva<va+n),None)
                ins=instructions.get(address)
                if not section:r['status']='not_file_backed_executable_section'
                elif not ins:r['status']='not_verified_instruction_boundary'
                else:
                    code,asm=ins;va,n,raw=section;offset=raw+rva-va;memory=bytes.fromhex(row.get('instruction_bytes',''))
                    expected=code;relocated=False
                    if memory[:len(code)]!=code:
                        adjusted=relocated_jump(data,rva,code,base-preferred)
                        if adjusted is not None:expected=adjusted;relocated=True
                    if rva-va+len(code)>n or data[offset:offset+len(code)]!=code or memory[:len(code)]!=expected:r['status']='instruction_bytes_unverified'
                    else:
                        symbol=subprocess.run(['i686-w64-mingw32-addr2line','-f','-C','-e',str(image),hex(address)],check=True,capture_output=True,text=True).stdout.splitlines()
                        function=symbol[0] if symbol else '??';location=symbol[1] if len(symbol)>1 else '??'
                        r.update(status='verified_function_instruction' if function!='??' and not location.startswith('??') else 'verified_instruction_function_unresolved',bytes=expected.hex(),file_bytes=code.hex(),base_relocation_verified=relocated,assembly=asm,assembly_address_space='static file operands; runtime HIGHLOW operand is in bytes',function=function,source=location,file_offset=hex(offset))
            results[key]=r;status[r['status']]+=1
    return {'image':str(image),'sha256':hashlib.sha256(data).hexdigest(),'architecture':'i386','preferred_image_base':hex(preferred),'total_samples':total,'status_counts':dict(status),'addresses':list(results.values()),'limits':['No nearest-symbol guesses','Counts are not function or instruction CPU time','Runtime bytes and module lookup occur after the capture window','No gameplay attribution implied by fixture validation']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('samples',type=Path);p.add_argument('--image',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=attribute(a.samples,a.image);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
