#!/usr/bin/env python3
"""Capture read-only source/binary evidence and generate an unapplied patch."""
import difflib
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
OUT = ROOT/'results'
OUT.mkdir(exist_ok=True)
relative = 'dlls/ntdll/unix/signal_x86_64.c'
source = WORKSPACE/'wine'/relative
text = source.read_text()
start = text.index('static BOOL rosetta_exec_breakpoints(')
end = text.index('\n\n\nstruct xcontext;', start)
old = text[start:end]
(OUT/'source-function.txt').write_text(old+'\n')
assert 'for (i = 0; i < 4; i++)' in old
new = old.replace('    unsigned int i;\n', '''#ifndef WINE_RESEARCH_BRANCHLESS_DR7
    unsigned int i;
#endif
''').replace('    for (i = 0; i < 4; i++)', '''#ifdef WINE_RESEARCH_BRANCHLESS_DR7
    const ULONG_PTR d = data->dr7;
    return (!!(d & 3) & !(d & 0x000f0000)) |
           (!!(d & 12) & !(d & 0x00f00000)) |
           (!!(d & 48) & !(d & 0x0f000000)) |
           (!!(d & 192) & !(d & 0xf0000000));
#else
    for (i = 0; i < 4; i++)''').replace('            return TRUE;\n#endif', '            return TRUE;\n#endif\n#endif')
updated = text[:start]+new+text[end:]
(ROOT/'candidate.patch').write_text(''.join(difflib.unified_diff(
    text.splitlines(True), updated.splitlines(True), fromfile='a/'+relative,
    tofile='b/'+relative)))

binary = WORKSPACE/'bo2-local/engine/lib/wine/x86_64-unix/ntdll.so'
asm = subprocess.check_output(['otool', '-tvV', str(binary)], text=True)
# Capture one symbol's complete instruction listing; no disassembler writes.
lines = asm.splitlines()
first = lines.index('_trap_handler:')
last = next((i for i in range(first+1, len(lines)) if lines[i].endswith(':')), len(lines))
(OUT/'winecx-trap-handler.asm').write_text('\n'.join(lines[first:last])+'\n')
paths = [source, binary, *sorted((WORKSPACE/'wine-rosetta-fix/patches').glob('*.patch')),
         *sorted((WORKSPACE/'wine-rosetta-fix/bo2/patches').glob('*.patch'))]
(OUT/'artifact-hashes.json').write_text(json.dumps({str(p.relative_to(WORKSPACE)):
    hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, indent=2)+'\n')

# 64-bit SMT-LIB contract. Solve with: z3 equivalence.smt2
def bv(n): return f'(_ bv{n} 64)'
zero = bv(0)
slots = []
for i in range(4):
    enabled = f'(distinct (bvand (bvlshr d {bv(2*i)}) {bv(3)}) {zero})'
    execution = f'(= (bvand (bvlshr d {bv(16+4*i)}) {bv(15)}) {zero})'
    slots.append(f'(and {enabled} {execution})')
baseline = 'false'
for slot in reversed(slots): baseline = f'(ite {slot} true {baseline})'
terms = [f'(and (distinct (bvand d {bv(3 << (2*i))}) {zero}) '
         f'(= (bvand d {bv(15 << (16+4*i))}) {zero}))' for i in range(4)]
(ROOT/'equivalence.smt2').write_text('(set-logic QF_BV)\n(declare-const d (_ BitVec 64))\n'
    + f'(assert (distinct {baseline} (or {" ".join(terms)})))\n(check-sat)\n')
