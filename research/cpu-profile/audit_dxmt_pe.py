#!/usr/bin/env python3
"""Compare named exports, dependencies and unwind symbols in DXMT PE32 DLLs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def inspect(path, tools):
    symbols = subprocess.check_output([str(tools / 'llvm-nm'), str(path)], text=True,
                                      stderr=subprocess.DEVNULL)
    text = subprocess.check_output([str(tools / 'llvm-readobj'), '--coff-exports',
                                    '--coff-imports', str(path)], text=True)
    exports = []
    for block in re.findall(r'Export \{(.*?)\n\}', text, re.S):
        name = re.search(r'^  Name: (.*)$', block, re.M)
        ordinal = re.search(r'^  Ordinal: (.*)$', block, re.M)
        exports.append({'name': name.group(1) if name else '',
                        'ordinal': int(ordinal.group(1)) if ordinal else None})
    imports = []
    for block in re.findall(r'Import \{(.*?)\n\}', text, re.S):
        name = re.search(r'^  Name: (.*)$', block, re.M)
        imports.append(name.group(1) if name else '')
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size, 'exports': exports, 'imports': imports,
            'unwind_symbols': sorted(set(re.findall(
                r'^.*\s(\S*(?:Unwind_|gxx_personality)\S*)$', symbols, re.M)))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools', type=Path, required=True, help='LLVM bin directory')
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--gcc', type=Path, required=True)
    parser.add_argument('--llvm', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = {'scope': 'Static PE32 audit; matching names do not establish ABI compatibility',
              'variants': {}}
    for variant in ['release', 'gcc', 'llvm']:
        report['variants'][variant] = {}
        for dll in ['d3d11', 'dxgi', 'd3d10core']:
            report['variants'][variant][dll] = inspect(getattr(args, variant) / (dll + '.dll'), args.tools)
    # Refuse to silently compare against Wine's builtin graphics DLLs.
    identity = json.loads(Path(__file__).with_name('dxmt-release-identity.json').read_text())
    for item in identity['files']:
        dll = Path(item['file']).stem
        if report['variants']['release'][dll]['sha256'] not in [item['installed_sha256'], item['release_sha256']]:
            raise RuntimeError('Baseline does not match verified DXMT release: ' + dll)
    for variant in ['gcc', 'llvm']:
        for dll in ['d3d11', 'dxgi', 'd3d10core']:
            release = {e['name'] for e in report['variants']['release'][dll]['exports']}
            candidate = {e['name'] for e in report['variants'][variant][dll]['exports']}
            report['variants'][variant][dll].update(
                missing_release_export_names=sorted(release - candidate),
                additional_export_names=sorted(candidate - release))
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(args.out)


if __name__ == '__main__':
    main()
