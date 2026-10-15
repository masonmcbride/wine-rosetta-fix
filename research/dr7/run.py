#!/usr/bin/env python3
"""Reproduce isolated predicate experiment; no Wine/game runtime is launched."""
import csv
import hashlib
import json
import pathlib
import platform
import statistics
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)

def run(*args):
    return subprocess.check_output(args, text=True)

metadata = {'host': platform.platform(), 'compiler': run('clang', '--version'),
            'flags': '-O2 -Wall -Wextra -Werror -arch ARCH (no LTO)',
            'seed': '0x6a09e667f3bcc909', 'warmup_calls': 1000000,
            'timed_calls': 20000000, 'pairs': 15,
            'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [ROOT/'predicate.c', ROOT/'harness.c']}}
rows = []
with tempfile.TemporaryDirectory(prefix='wine-dr7-') as tmp:
    for arch in ['x86_64', 'arm64']:
        exe = str(pathlib.Path(tmp)/arch)
        flags = ['clang', '-O2', '-Wall', '-Wextra', '-Werror', '-arch', arch]
        subprocess.run(flags + [str(ROOT/'predicate.c'), str(ROOT/'harness.c'), '-o', exe], check=True)
        (OUT/f'{arch}-correctness.txt').write_text(run(exe))
        subprocess.run(flags + ['-S', str(ROOT/'predicate.c'), '-o', str(OUT/f'{arch}.s')], check=True)
        # Alternating AB/BA order limits monotonic thermal/order bias.
        for mode in range(4):
            for pair in range(15):
                order = ['baseline', 'candidate'] if pair % 2 == 0 else ['candidate', 'baseline']
                for variant in order:
                    fields = run(exe, variant, str(mode)).strip().split(',')
                    rows.append([arch, mode, pair, variant, float(fields[2]), int(fields[3])])
with (OUT/'timings.csv').open('w') as f:
    w = csv.writer(f)
    w.writerow(['arch', 'mode', 'pair', 'variant', 'ns_per_call', 'checksum'])
    w.writerows(rows)
summary = []
for arch in ['x86_64', 'arm64']:
    for mode in range(4):
        group = [r for r in rows if r[:2] == [arch, mode]]
        b = [r[4] for r in group if r[3] == 'baseline']
        c = [r[4] for r in group if r[3] == 'candidate']
        ratios = [next(r[4] for r in group if r[2:4] == [p, 'baseline']) /
                  next(r[4] for r in group if r[2:4] == [p, 'candidate']) for p in range(15)]
        assert len({r[5] for r in group}) == 1
        summary.append({'arch': arch, 'mode': mode, 'baseline_median_ns': statistics.median(b),
                        'candidate_median_ns': statistics.median(c),
                        'paired_ratio_median': statistics.median(ratios),
                        'baseline_range_ns': [min(b), max(b)], 'candidate_range_ns': [min(c), max(c)]})
(OUT/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
(OUT/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
