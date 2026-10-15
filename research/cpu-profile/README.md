# Wine and Zombies profiling research

The goal is smoother Zombies, Overwatch 2 and Borderlands 2 gameplay. Zombies
is the current workload. No performance patch has been selected or applied;
the working debug-register implementation remains unchanged.

## Start here

- [Current findings and next investigation](zombies-stall-findings.md): DXMT
  submits Metal work; the largest recorded display gaps have sparse present
  requests and sparse target GPU work, alongside a workload phase change.
  This is not yet a diagnosed inefficient function.
- [First gameplay captures](zombies-origins-first.md): methods, settings,
  observations, and the menu-time confound in the resolution comparison.
- [Validated experimental CPU sampler](mach-profiling-findings.md): original-x86
  Mach snapshots with independent per-thread CPU accounting and explicit limits.
- [Rejected approaches](rejected-approaches.md): concise record of dead ends.
- [Next-session handoff](next-session.md): what to do without repeating setup.

Raw gameplay traces, account state, binaries and bottles are private and are
not part of this repository. The synthetic validation evidence retained under
`results/` is selected explicitly; new generated results are ignored by default.
Historical paths and hashes in that evidence describe the measured machine,
not portable installation locations or guaranteed source provenance.

## Useful tools

`analyze_stalls.py`, `analyze_presentation.py`, `analyze_saved_cpu.py` and
`summarize_metal.py` analyze local Instruments exports. They do not record games,
classify menus, or prove causation. CPU sample counts are not exact CPU timings.
The saved-CPU helper's windows are specific to the first Origins capture.

`mach_sampler.c`, `build_mach.py`, `validate_mach.py`, and `analyze_mach.py`
implement an experimental in-process sampler. Its validation supports coarse
CPU attribution on tested patterns, not universal function-level accuracy.
`events.c`, `build.py`, and `try_wine_mach.py` provide a source-available Win32
synchronization calibration workload; it is not evidence of gameplay hotness.
The runner expects the workspace's separate `bo2-local/engine` and uses its own
ignored research prefix. Do not inject the sampler into a game by default.

Build calibration tools on macOS with Apple clang; the Win32 guest additionally
requires `x86_64-w64-mingw32-gcc`:

```sh
python3 build_mach.py
python3 validate_mach.py --rates 5000
python3 build.py
# Only when intentionally running the synthetic guest with the local engine:
python3 try_wine_mach.py
```

Offline checks, from this directory:

```sh
python3 -m unittest test_mach_analysis test_metal_analysis test_stalls
```

Superseded profiler scripts, generated manifests and full exploratory results
are preserved locally in an ignored archive. A complete pre-cleanup research
snapshot is also retained outside this repository under the private workspace
`bo2-local/research-archive/`. They are not active tools or publication evidence.
