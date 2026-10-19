#!/usr/bin/env python3
"""Build/run a bounded PE32 exception study in its own disposable Wine prefix.

Same Clang compiles work.cpp for both exception models. The link/runtime stacks
necessarily differ. Timings compare these configurations, not exception flags
in isolation, and cannot be generalized to graphics/gameplay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, log, env=None, timeout=90):
    start = time.monotonic()
    result = subprocess.run([str(a) for a in args], env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=timeout)
    log.write_text(result.stdout)
    return {'command': [str(a) for a in args], 'exit_code': result.returncode,
            'wall_seconds': time.monotonic() - start, 'log': str(log)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--llvm', type=Path, required=True, help='LLVM-MinGW root')
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--gcc', default='i686-w64-mingw32-g++')
    parser.add_argument('--pairs', type=int, default=8)
    parser.add_argument('--iterations', type=int, default=3000000)
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    if not 2 <= args.pairs <= 20 or not 10000 <= args.iterations <= 100000000:
        parser.error('Use 2..20 pairs and 10000..100000000 iterations')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    engine, llvm = args.engine.resolve(), args.llvm.resolve()
    clang = llvm / 'bin/i686-w64-mingw32-clang++'
    source = Path(__file__).with_name('exception-runtime')
    report = {'scope': 'Synthetic PE32 runtime configurations; no graphics or gameplay claim',
              'compiler': subprocess.check_output([str(clang), '--version'], text=True),
              'sources': {p.name: sha(p) for p in sorted(source.glob('*.cpp'))},
              'builds': {}, 'runs': [], 'pairs': args.pairs, 'iterations': args.iterations}
    receipt = out / 'receipt.json'
    def save():
        receipt.write_text(json.dumps(report, indent=2) + '\n')
    for mode, linker in [('sjlj', args.gcc), ('dwarf', clang)]:
        obj = out / (mode + '-work.o')
        asm = out / (mode + '-work.s')
        exe = out / (mode + '.exe')
        compile_args = [clang, '-std=c++20', '-O2', '-fexceptions',
                        '-f' + mode + '-exceptions', source / 'work.cpp']
        commands = [compile_args + ['-c', '-o', obj],
                    compile_args + ['-S', '-o', asm],
                    [linker, '-std=c++20', '-O2', '-static', source / 'main.cpp', obj, '-o', exe]]
        build = {'steps': [], 'runtime': 'GCC libstdc++/libgcc' if mode == 'sjlj' else 'LLVM libc++/libunwind'}
        report['builds'][mode] = build
        for i, cmd in enumerate(commands):
            step = command(cmd, out / f'{mode}-build-{i}.log')
            build['steps'].append(step)
            save()
            if step['exit_code']:
                raise RuntimeError('Build failed: ' + step['log'])
        build.update(executable_sha256=sha(exe), assembly_sha256=sha(asm))
    save()
    if args.build_only:
        print(receipt)
        return
    prefix = out / 'prefix'
    marker = out / 'prefix-owner.txt'
    if prefix.exists() and not marker.exists():
        raise RuntimeError('Refusing to reuse an unowned Wine prefix')
    marker.write_text('Owned by run_exception_study.py; disposable experiment prefix\n')
    env = os.environ.copy()
    # Avoid inheriting game-specific profiling or DLL overrides.
    for key in ['DYLD_INSERT_LIBRARIES', 'WINEDLLOVERRIDES', 'WINEARCH', 'WINE_SERVER_DIR']:
        env.pop(key, None)
    env.update(WINEPREFIX=str(prefix), WINESERVER=str(engine / 'bin/wineserver'),
               WINELOADER=str(engine / 'bin/wine64'),
               DYLD_FALLBACK_LIBRARY_PATH=str(engine / 'lib') + ':/usr/lib',
               WINEDEBUG='-all', WINEMSYNC='0', WINEESYNC='0', WINEFSYNC='0',
               WINEDLLOVERRIDES='winemenubuilder.exe=d',
               WINE_ROSETTA_EXEC_BREAKPOINTS='0', WINE_ROSETTA_WOW64_BREAKPOINTS='0',
               WINE_ROSETTA_CALL_WORKAROUND='0')
    report['runtime_environment'] = {k: v for k, v in env.items()
                                     if k.startswith('WINE') or k == 'DYLD_FALLBACK_LIBRARY_PATH'}
    report['engine_loader_sha256'] = sha(engine / 'bin/wine64')
    # First run initializes only this prefix; exclude it from timing summaries.
    warm = command([engine / 'bin/wine64', out / 'sjlj.exe', '10000'],
                   out / 'prefix-init.log', env=env, timeout=90)
    report['prefix_initialization'] = warm
    save()
    if warm['exit_code']:
        raise RuntimeError('Prefix initialization failed: ' + warm['log'])
    for pair in range(args.pairs):
        order = ['sjlj', 'dwarf'] if pair % 2 == 0 else ['dwarf', 'sjlj']
        for mode in order:
            log = out / f'pair-{pair:02d}-{mode}.log'
            run = command([engine / 'bin/wine64', out / (mode + '.exe'), str(args.iterations)],
                          log, env=env, timeout=30)
            run.update(pair=pair, mode=mode)
            report['runs'].append(run)
            save()
            if run['exit_code']:
                raise RuntimeError('Runtime failed: ' + str(log))
            lines = [line for line in log.read_text().splitlines() if line.startswith('{')]
            if len(lines) != 1:
                raise RuntimeError('Expected one JSON result: ' + str(log))
            measurement = json.loads(lines[0])
            if not measurement.get('correctness') or measurement['iterations'] != args.iterations:
                raise RuntimeError('Correctness/iteration check failed: ' + str(log))
            if measurement['ticks'] <= 0 or measurement['frequency'] <= 0:
                raise RuntimeError('Invalid timing: ' + str(log))
            run['measurement'] = measurement
            run['ns_per_iteration'] = measurement['ticks'] * 1e9 / measurement['frequency'] / args.iterations
            save()
    report['summary'] = {mode: {'median_ns_per_iteration': statistics.median(
        r['ns_per_iteration'] for r in report['runs'] if r['mode'] == mode)}
        for mode in ['sjlj', 'dwarf']}
    deltas = []
    for pair in range(args.pairs):
        runs = {r['mode']: r for r in report['runs'] if r['pair'] == pair}
        if runs['sjlj']['measurement']['checksum'] != runs['dwarf']['measurement']['checksum']:
            raise RuntimeError('Mismatched workload checksums')
        deltas.append(runs['sjlj']['ns_per_iteration'] - runs['dwarf']['ns_per_iteration'])
    report['paired_sjlj_minus_dwarf_ns'] = deltas
    report['median_paired_difference_ns'] = statistics.median(deltas)
    save()
    print(json.dumps(report['summary'], indent=2))
    print(receipt)


if __name__ == '__main__':
    main()
