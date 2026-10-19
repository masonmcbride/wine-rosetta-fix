#!/usr/bin/env python3
"""Offline byte attribution for Wine engine modules only.

Symbol labels are candidates, not proof of containing function boundaries.
No proprietary executable or system-framework file is disassembled.
"""
import sys,csv,json,collections,hashlib,pathlib,subprocess,re,struct
here=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(here))
from attribute_pe_samples import attribute
import argparse
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('sample',type=pathlib.Path);parser.add_argument('--output',type=pathlib.Path,required=True);args=parser.parse_args()
sample=args.sample
with sample.open() as stream:rows=list(csv.DictReader(stream))
out=args.output;out.mkdir(parents=True,exist_ok=True)
reports=[]
for name in sorted({r['module'] for r in rows if r['kind']=='PE32' and '/engine/' in r['module']}):
 image=pathlib.Path(name);v=attribute(sample,image);(out/(image.name+'.json')).write_text(json.dumps(v,indent=2)+'\n');reports.append({'image':image.name,'sha256':v['sha256'],'status_counts':v['status_counts']})
results=[]
for name in sorted({r['module'] for r in rows if r['kind']=='MachO64' and '/engine/' in r['module']}):
 image=pathlib.Path(name);data=image.read_bytes()
 if struct.unpack_from('<II',data) != (0xfeedfacf,0x1000007):raise ValueError('Expected x86_64 Mach-O')
 n=struct.unpack_from('<I',data,16)[0];pos=32;segments=[]
 for i in range(n):
  cmd,size=struct.unpack_from('<II',data,pos)
  if cmd==0x19:
   va,vs,fo,fs=struct.unpack_from('<QQQQ',data,pos+24);prot=struct.unpack_from('<I',data,pos+60)[0]
   if prot&4:segments.append((va,vs,fo,fs))
  pos+=size
 if not any(s[0]==0 for s in segments):raise ValueError('Only zero-based executable Mach-O images supported')
 dump=subprocess.run(['/usr/bin/objdump','-d',name],capture_output=True,text=True,check=True).stdout;ins={};function=None
 for line in dump.splitlines():
  m=re.match(r'^([0-9a-f]+) <(.+)>:',line)
  if m:function=(int(m[1],16),m[2]);continue
  m=re.match(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*(\S.*)$',line)
  if m:ins[int(m[1],16)]=(bytes.fromhex(m[2]),m[3],function)
 counts=collections.Counter((r['pc'],r['base'],r['instruction_bytes']) for r in rows if r['module']==name)
 for (pc,base,memory),count in counts.items():
  a=int(pc,16)-int(base,16);v={'module':image.name,'sha256':hashlib.sha256(data).hexdigest(),'pc':pc,'base':base,'static_address':hex(a),'samples':count,'status':'unresolved_instruction_boundary'}
  if a in ins:
   code,asm,fn=ins[a];seg=next((s for s in segments if s[0]<=a and a+len(code)<=s[0]+min(s[1],s[3])),None)
   if seg:
    offset=seg[2]+a-seg[0];v['status']='instruction_bytes_mismatch'
    if data[offset:offset+len(code)]==code and bytes.fromhex(memory).startswith(code):
     v.update(status='verified_instruction_symbol_range',file_offset=hex(offset),bytes=code.hex(),assembly=asm,symbol=fn[1] if fn else None,symbol_offset=hex(a-fn[0]) if fn else None)
  results.append(v)
(out/'wine-mach-instructions.json').write_text(json.dumps(results,indent=2)+'\n')
stats=json.loads(pathlib.Path(str(sample)+'.stats.json').read_text());summary={'samples':len(rows),'pe_reports':reports,'mach_status':dict(collections.Counter({s:sum(x['samples'] for x in results if x['status']==s) for s in {x['status'] for x in results}})),'mach_symbols':collections.Counter(),'threads':sorted(stats['threads'],key=lambda t:t['cpu_us'],reverse=True)[:8]}
for x in results:summary['mach_symbols'][x.get('symbol',x['status'])]+=x['samples']
summary['mach_symbols']=summary['mach_symbols'].most_common();summary['sample_sha256']=hashlib.sha256(sample.read_bytes()).hexdigest();summary['limits']=['Only engine paths disassembled; game executable, bottle graphics DLL and Apple framework instructions unresolved here', 'Symbol ranges are unverified containing-function candidates, especially stripped winemetal; Ghidra boundary verification is separate', 'Dump-time bytes and current file hashes do not prove module lifetime during capture', 'Counts are endpoint snapshots, not instruction costs, call counts, blocked durations or inclusive stacks', 'No source/build provenance established; no optimization selected'];summary['observed_thread_cpu_us']=sum(t['cpu_us'] for t in stats['threads']);(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
