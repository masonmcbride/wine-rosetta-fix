#!/usr/bin/env python3
"""Import exact DXMT artifacts into disposable Ghidra projects and check bytes.

Uses Ghidra's Java entry point to avoid the shell launcher's global JDK setting
write. All Ghidra settings, caches, projects and logs stay beneath --out.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from attribute_pe_samples import pe_sections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ghidra', type=Path, required=True)
    parser.add_argument('--java', type=Path, required=True, help='Supported JDK java executable')
    parser.add_argument('--variants', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    ghidra = args.ghidra.resolve()
    manifest = json.loads(args.manifest.read_text())
    vmargs = [line.split('=', 1)[1] for line in (ghidra / 'support/launch.properties').read_text().splitlines()
              if line.startswith('VMARGS=') or line.startswith('VMARGS_MACOS=')]
    options = [f'-Dapplication.settingsdir={out / "settings"}',
               f'-Dapplication.cachedir={out / "cache"}',
               f'-Djava.util.prefs.userRoot={out / "prefs"}']
    summary = {'scope': 'Independent static entry-window decode, not gameplay function-cost attribution',
               'variants': {}}
    for variant in ['release', 'llvm']:
        row = manifest['variants'][variant]
        image = (args.variants / variant / 'd3d11.dll').resolve()
        receipt = out / (variant + '-entry.json')
        command = [str(args.java), *vmargs, *options, '-Xmx2G', '-XX:ParallelGCThreads=2',
                   '-XX:CICompilerCount=2', '-Djava.awt.headless=true', '-cp',
                   str(ghidra / 'Ghidra/Framework/Utility/lib/Utility.jar'), 'ghidra.Ghidra',
                   'ghidra.app.util.headless.AnalyzeHeadless', str(out), 'entry-' + variant,
                   '-import', str(image), '-readOnly', '-noanalysis', '-scriptPath',
                   str(Path(__file__).with_name('ghidra').resolve()), '-postScript',
                   'AuditDxmtEntry.java', row['binary_sha256'], row['static_address'],
                   '128', str(receipt), '-max-cpu', '2', '-log', str(out / (variant + '-application.log')),
                   '-scriptlog', str(out / (variant + '-script.log'))]
        # Do not allow a stale script result to masquerade as this run's success.
        receipt.unlink(missing_ok=True)
        env = os.environ.copy()
        env.pop('JAVA_TOOL_OPTIONS', None)
        env.pop('JDK_JAVA_OPTIONS', None)
        with (out / (variant + '-headless.log')).open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=150)
        result = json.loads(receipt.read_text())
        data = image.read_bytes()
        if hashlib.sha256(data).hexdigest() != result['sha256'] or result['sha256'] != row['binary_sha256']:
            raise RuntimeError('Artifact identity mismatch')
        preferred, sections = pe_sections(data)
        count = 0
        calls = []
        for instruction in result['instructions']:
            address = int(instruction['address'], 16)
            code = bytes.fromhex(instruction['bytes'])
            rva = address - preferred
            section = next(((va, n, raw) for va, n, raw in sections if va <= rva and rva + len(code) <= va + n), None)
            if section is None:
                raise RuntimeError('Instruction is not file-backed executable code')
            va, n, raw = section
            offset = raw + rva - va
            if data[offset:offset + len(code)] != code:
                raise RuntimeError('Ghidra bytes differ from file')
            if code[0] == 0xe8 and len(code) == 5:
                target = (address + 5 + struct.unpack('<i', code[1:])[0]) & 0xffffffff
                if [int(x, 16) for x in instruction['call_targets']] != [target]:
                    raise RuntimeError('Ghidra relative call target mismatch')
                calls.append({'address': hex(address), 'target': hex(target)})
            count += 1
        if count == 0:
            raise RuntimeError('No verified instructions')
        summary['variants'][variant] = {'sha256': result['sha256'], 'verified_instructions': count,
                                       'relative_calls': calls, 'command': command,
                                       'raw_receipt': str(receipt)}
        print(variant, count, 'instructions verified', flush=True)
    (out / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
