#!/usr/bin/env python3
"""Load isolated DXMT DLLs and verify a 4 KiB offscreen D3D11 buffer copy.

Requires a prefix created by run_exception_study.py. Never copies DLLs to a Wine
installation or game bottle; native DLL selection applies only to this process.
"""
import argparse
import hashlib
import json
import os
import itertools
import statistics
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True, help='Owned exception-study directory')
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--variants', type=Path, required=True, help='Parent of release/gcc/llvm DLL directories')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=1, help='1 smoke pass, or 6 balanced timing rounds')
    parser.add_argument('--iterations', type=int, default=0, help='0 disables getter timing')
    args = parser.parse_args()
    if args.rounds not in (1, 6) or (args.iterations and not 10000 <= args.iterations <= 10000000):
        parser.error('Use 1 or 6 rounds; timing iterations must be 10000..10000000')
    study, engine = args.study.resolve(), args.engine.resolve()
    marker = study / 'prefix-owner.txt'
    if not marker.exists() or 'run_exception_study.py' not in marker.read_text():
        raise RuntimeError('Expected owned disposable study prefix')
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in ['DYLD_INSERT_LIBRARIES', 'WINEARCH', 'WINE_SERVER_DIR']:
        env.pop(key, None)
    env.update(WINEPREFIX=str(study / 'prefix'), WINESERVER=str(engine / 'bin/wineserver'),
               WINELOADER=str(engine / 'bin/wine64'),
               DYLD_FALLBACK_LIBRARY_PATH=str(engine / 'lib') + ':/usr/lib',
               WINEDEBUG='-all', WINEMSYNC='0', WINEESYNC='0', WINEFSYNC='0',
               MVK_CONFIG_LOG_LEVEL='1',
               WINEDLLOVERRIDES='d3d11=n;dxgi=n;d3d10core=n;winemetal=b;winemenubuilder.exe=d',
               WINE_ROSETTA_EXEC_BREAKPOINTS='0', WINE_ROSETTA_WOW64_BREAKPOINTS='0',
               WINE_ROSETTA_CALL_WORKAROUND='0')
    report = {'scope': 'Offscreen buffer-copy smoke only; no shader, presentation or gameplay validation',
              'probe_sha256': hashlib.sha256(args.probe.read_bytes()).hexdigest(),
              'probe_source_sha256': hashlib.sha256(Path(__file__).with_name('exception-runtime').joinpath('graphics_smoke.cpp').read_bytes()).hexdigest(),
              'runs': [], 'prefix': str(study / 'prefix')}
    receipt = out / 'receipt.json'
    orders = list(itertools.permutations(['release', 'gcc', 'llvm'])) if args.rounds == 6 else [('release', 'gcc', 'llvm')]
    schedule = [(round_no, variant) for round_no, order in enumerate(orders) for variant in order]
    for round_no, variant in schedule:
        directory = (args.variants / variant).resolve()
        windows_directory = 'Z:' + str(directory).replace('/', '\\')
        cmd = [str(engine / 'bin/wine64'), str(args.probe.resolve()), windows_directory]
        if args.iterations:
            cmd.append(str(args.iterations))
        run = {'variant': variant, 'round': round_no, 'command': cmd,
               'dlls': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.dll')}}
        try:
            result = subprocess.run(cmd, env=env, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=60)
            run.update(exit_code=result.returncode, output=result.stdout)
            rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            run['measurement'] = rows[-1] if rows else None
            run['passed'] = result.returncode == 0 and bool(rows) and rows[-1].get('passed') is True
            expected_path = 'loaded_d3d11=' + windows_directory + '\\d3d11.dll'
            if expected_path.lower() not in result.stdout.lower():
                run.update(passed=False, path_check_failed=True)
            expected_dxgi = 'loaded_dxgi=' + windows_directory + '\\dxgi.dll'
            if expected_dxgi.lower() not in result.stdout.lower():
                run.update(passed=False, dxgi_path_check_failed=True)
            if args.iterations:
                measurements = [row for row in rows if row.get('benchmark') == 'IAGetVertexBuffers']
                if len(measurements) != 1:
                    run['passed'] = False
                else:
                    measurement = measurements[0]
                    run['benchmark'] = measurement
                    if measurement['iterations'] != args.iterations or measurement['ticks'] <= 0 or measurement['frequency'] <= 0:
                        run['passed'] = False
                    else:
                        run['ns_per_call'] = measurement['ticks'] * 1e9 / measurement['frequency'] / args.iterations
        except subprocess.TimeoutExpired as error:
            run.update(passed=False, timeout=True, output=str(error.stdout))
            # This environment scopes shutdown to our disposable study prefix.
            subprocess.run([str(engine / 'bin/wineserver'), '-k'], env=env, timeout=10)
        (out / (str(round_no) + '-' + variant + '.log')).write_text(run.get('output', ''))
        report['runs'].append(run)
        receipt.write_text(json.dumps(report, indent=2) + '\n')
        print(round_no, variant, 'PASS' if run['passed'] else 'FAIL', flush=True)
    if args.iterations and all(run['passed'] for run in report['runs']):
        report['summary'] = {variant: {'median_ns_per_call': statistics.median(
            run['ns_per_call'] for run in report['runs'] if run['variant'] == variant)}
            for variant in ['release', 'gcc', 'llvm']}
        report['timing_scope'] = 'CPU getter microbenchmark; different complete build/runtime configurations, not isolated exception-mode causation'
        receipt.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report['summary'], indent=2))
    print(receipt)
    if not all(run['passed'] for run in report['runs']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
