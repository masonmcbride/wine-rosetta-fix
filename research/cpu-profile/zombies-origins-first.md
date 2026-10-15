# First Zombies / Origins Metal capture

2026-10-15. The user clarified that the intended workloads are Zombies,
Overwatch 2 and Borderlands 2. Use those workloads for optimization selection;
the earlier synthetic CPU tests validate instrumentation only. The user
authorized running the existing Zombies setup and profiling it while leaving
proprietary binaries and the working Wine debug-register implementation intact.

## Capture

Launched the existing `bo2/run-bo2.sh` without changing its settings. The user
loaded Origins and confirmed readiness at 1512×945. Attached Xcode Instruments
Metal System Trace to the game host PID 4347 for 30 seconds. An earlier
15-second capture during loading served only as a telemetry smoke test.
No research sampling library was injected into the game.

Raw traces, exports, loaded-library mappings, selected settings and executable
hashes remain private under `bo2-local/profiling/origins-first/`. Do not publish
that directory or account/game data. The trace is not a gameplay replay;
standing at spawn was requested, but exact camera position, enemy activity,
focus, thermal state and background activity were not independently verified.

Saved configuration lists windowed 1512×945, VSync off, a 200 FPS cap and
`r_aaSamples=1`. These are saved values, not independent live verification.
Loaded mappings include winemetal.so, MoltenVK and Metal.framework. Both
translation libraries being present does not establish which implementation
rendered each frame. Actual game-attributed Metal GPU and presentation events
were successfully recorded.

## Observations

| Quantity | Origins spawn capture |
|---|---:|
| Target-attributed display swap timestamps | 3,530 |
| Span between first and last swap | 30.1065 s |
| Display updates per second over that span | 117.22 |
| Median interval | 8.32 ms |
| 95th percentile interval | 23.32 ms |
| 99th percentile interval | 31.68 ms |
| Longest interval | 300.00 ms |
| Intervals greater than 33.34 ms | 8 |
| Target-attributed command-buffer submission rows | 10,043 |
| Target-attributed GPU interval rows | 215,604 |
| Union of target-attributed GPU intervals | 13.4131 s |
| Recorded compiler activity intervals | 65 |
| Union of recorded compiler activity | 5.397 ms |
| Longest recorded compiler interval | 0.506 ms |

Display swap intervals describe the recorded display surface stream; they are
not CPU frame times, simulation rate or input-to-photon latency. Submission
counts are not frame counts. GPU interval union is recorded attributed work,
not a hardware utilization percentage. The recorded compiler activity is brief;
this does not include every possible translation/cache operation and does not
prove that a particular compiler event blocked a frame.

The trace establishes usable Metal telemetry and pacing irregularities on the
actual requested workload. It does **not** yet establish a CPU/GPU bottleneck,
profiler overhead, repeatability, the cause of the 300 ms gap, or a justified
Wine optimization. Both traces finalized successfully with a warning about
backdated signpost intervals; retain that warning when assessing event timing.

## Reproduction and validation

Use `xctrace record --template 'Metal System Trace' --attach PID --time-limit 30s`
with an explicit new output path and
`DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer`. Export the TOC and
the `displayed-surfaces-interval`, `metal-gpu-intervals`,
`metal-application-command-buffer-submissions` and
`graphics-compiler-activity-intervals` tables. `summarize_metal.py` resolves XML
references, maps table indices through the matching TOC, filters by target PID
including nested process labels, and unions overlapping intervals. Other
desktop processes are excluded from the reported target figures.

Two offline tests cover reference/process filtering, overlapping GPU intervals,
display gaps, and rejection of missing references. Together with the three
existing CPU analyzer tests, all five passed. Before/after SHA-256 checks matched
for the launcher, Wine loader, ntdll, both selected t6zm executable paths, and
32-bit D3D11/DXGI libraries. Wine source remained clean. ntdll remains
`c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591`.
Ordinary gameplay can write runtime state; no binary or engine patch was made.

## Next experiment

Repeat the same warmed spawn view at 1512×945, then at a lower resolution,
keeping other settings and scene conditions comparable. Compare display pacing
and GPU execution coverage across repeated captures. A resolution response can
help distinguish graphics pressure from CPU/presentation limitations; it is not
conclusive by itself. Measure collection disturbance with an independent frame
source before treating these traces as an uninstrumented performance baseline.
Inspect CPU or presentation behavior around persistent long gaps before selecting
any patch. No optimization is selected from this first capture.

## Lower-resolution follow-up: scene confounded

A second 30-second Metal System Trace attached to the same host at saved
1024×640, windowed, VSync off and cap 200. It finalized successfully with the
same backdated-signpost warning. The user's latest correction was that there
was probably some menu time. Treat this as a mixed scene, **not a controlled
resolution comparison**. Do not infer a CPU bottleneck from its lower update
rate or a resolution benefit from its improved tail.

| Quantity | 1512×945 first capture | 1024×640 mixed capture |
|---|---:|---:|
| Display updates/sec over observed span | 117.22 | 93.69 |
| 95th percentile display interval | 23.32 ms | 16.67 ms |
| 99th percentile display interval | 31.68 ms | 16.67 ms |
| Longest display interval | 300.00 ms | 100.00 ms |
| Gaps greater than 33.34 ms | 8 | 1 |
| Union of attributed GPU intervals | 13.413 s | 13.106 s |
| Union of recorded compiler intervals | 5.397 ms | 5.150 ms |

Private evidence uses `origins-spawn-1024x640.trace`, `lower-toc.xml`,
`lower-events.xml`, `lower-summary.json` and `lower-manifest.json` in the same
private capture directory. The filename reflects the intended scene, not proof
that every recorded moment was spawn gameplay. All selected input hashes
matched the earlier capture and remained unchanged afterward.

Next capture should start after explicit confirmation that the game is fully
in spawn with menus closed. Keep focus and camera view stable, and record menu
interruptions if they occur. Repeat both resolutions under those conditions
before selecting an optimization target.
