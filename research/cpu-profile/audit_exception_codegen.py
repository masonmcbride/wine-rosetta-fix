#!/usr/bin/env python3
"""Reproduce PE32 exception codegen; no game, engine or source checkout writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def run(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--runtime-compiler', default='i686-w64-mingw32-g++')
    parser.add_argument('--nm', default='i686-w64-mingw32-nm')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fixture = Path(__file__).with_name('exception_codegen_fixture.cpp')
    report = {'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'compiler': run([args.clang, '--version']).splitlines()[0],
              'target': 'i686-w64-windows-gnu', 'variants': {},
              'scope': 'Static codegen only; no runtime correctness or performance claim'}
    for mode in ('sjlj', 'dwarf'):
        output = args.out / (mode + '.s')
        command = [args.clang, '--target=' + report['target'], '-O2', '-S',
                   '-fexceptions', '-f' + mode + '-exceptions', str(fixture), '-o', str(output)]
        run(command)
        assembly = output.read_text()
        calls = re.findall(r'^\s*call\w*\s+([^\s#]+)', assembly, re.M)
        report['variants'][mode] = {
            'command': command, 'assembly_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'static_call_sites': calls,
            'sjlj_registration': any('Unwind_SjLj_Register' in call for call in calls),
            'sjlj_unregistration': any('Unwind_SjLj_Unregister' in call for call in calls),
            'exception_cleanup_present': any(re.search(r'Unwind_(?:SjLj_)?Resume', call) for call in calls),
        }
    sjlj, dwarf = (report['variants'][mode] for mode in ('sjlj', 'dwarf'))
    if not (sjlj['sjlj_registration'] and sjlj['sjlj_unregistration']
            and not dwarf['sjlj_registration'] and not dwarf['sjlj_unregistration']
            and sjlj['exception_cleanup_present'] and dwarf['exception_cleanup_present']):
        raise RuntimeError('Expected code-generation contrast not reproduced')
    archive = run([args.runtime_compiler, '-print-file-name=libgcc_eh.a']).strip()
    symbols = run([args.nm, archive])
    definitions = sorted(set(re.findall(r'^\s*[0-9a-fA-F]+\s+T\s+(\S+)', symbols, re.M)))
    report['installed_runtime'] = {
        'archive': archive,
        'sha256': hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
        'unwind_definitions': [s for s in definitions if 'Unwind' in s or 'personality' in s],
        'note': 'Archive symbols are a compatibility screen, not a full C++ ABI/link test',
    }
    # This tests link compatibility only. Never execute the generated binaries.
    support = args.out / 'link_support.cpp'
    support.write_text("struct Guard { Guard(); ~Guard(); };\n"
                       "Guard::Guard() {}\nGuard::~Guard() {}\n"
                       "void encode_work() {}\nextern void encode_chunk();\n"
                       "int main() { encode_chunk(); }\n")
    for mode in ('sjlj', 'dwarf'):
        obj = args.out / (mode + '.o')
        run([args.clang, '--target=' + report['target'], '-O2', '-c',
             '-fexceptions', '-f' + mode + '-exceptions', str(fixture), '-o', str(obj)])
        command = [args.runtime_compiler, '-static', str(support), str(obj),
                   '-o', str(args.out / (mode + '.exe'))]
        linked = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (args.out / (mode + '-link.log')).write_text(linked.stdout)
        report['variants'][mode]['link_screen'] = {
            'command': command, 'exit_code': linked.returncode,
            'diagnostic': linked.stdout,
            'scope': 'Empty support functions; no execution or exception-correctness validation',
        }
    result = args.out / 'receipt.json'
    result.write_text(json.dumps(report, indent=2) + '\n')
    print(result)


if __name__ == '__main__':
    main()
