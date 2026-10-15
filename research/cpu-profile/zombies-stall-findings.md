# Origins stall-window investigation

2026-10-15. Analyzed existing recordings only; no new game launch, recording,
engine change or proprietary binary edit. Evidence stays in the private
`bo2-local/profiling/origins-first/` directory.

## Findings

**DXMT actively submits Metal work.** In the 1512×945 recording, 9,589 of
10,043 command-buffer rows name `dxmt-encode-thr`; 452 name `Backend` and two
name `wined3d_cs`. In the lower-resolution recording all 11,559 rows name the
DXMT encoding thread. This is stronger evidence than merely loading both
winemetal and MoltenVK. It establishes DXMT activity, not exclusive ownership
of all surfaces or the identity of every other renderer.

DXMT is an open-source D3D10/11-to-Metal implementation. Current upstream
[command queue source](https://github.com/3Shain/dxmt/blob/main/src/dxmt/dxmt_command_queue.cpp)
names its encoding thread and contains encoding, commit and completion paths.
Its [swapchain source](https://github.com/3Shain/dxmt/blob/main/src/d3d11/d3d11_swapchain.cpp)
contains frame-latency synchronization and presentation logic. These are
investigation entry points, **not proven faulty functions**. Current upstream
is not established as the source corresponding to these installed binaries;
no backend upgrade or fork was installed.

**The largest recorded gaps are not sustained target-attributed GPU execution.**
Times below are relative to recording start. Overlap is the union of clipped
intervals, so overlapping events are not double counted.

| Display gap | Start (s) | Recorded target GPU work | Compiler overlap | Present requests starting inside gap | Drawable-wait overlap |
|---|---:|---:|---:|---:|---:|
| 300.00 ms | 26.1047 | 4.702 ms | 3.291 ms | 1 | 0 ms |
| 228.96 ms | 25.8757 | 0.168 ms | 0 ms | 1 | 0 ms |
| 91.65 ms | 26.4047 | 0.173 ms | 0 ms | See private presentation export | See private presentation export |

The largest gap between recorded present requests is 289.94 ms, followed by
222.97 ms. Both are close to the large display-gap durations. The longest
recorded drawable wait anywhere in the capture is 19.83 ms. Thus there is
positive evidence of sparse presentation requests during the largest gaps,
and no corresponding recorded drawable wait or sustained target GPU interval.
This supports investigating **frame production, scheduling, synchronization,
or lifecycle transitions before presentation**. It does not establish CPU
saturation, a Wine synchronization bug, or absence of unattributed GPU work.

**The first recording has a major behavior change around 26 seconds.**
DXMT submissions fall from 376 in second 24 and 332 in second 25 to 34 in
second 26, then roughly 56–62 per second. Meanwhile the `Backend` thread
produces 442 submissions during second 26. The 300 ms gap contains 444
submission starts across threads, so submission count must not be mistaken
for produced frames. This cluster may reflect a scene/focus/lifecycle change;
timing alone cannot identify it as a menu or loading screen. All eight display
gaps over 33.34 ms in this capture occur after 25.8 seconds. They do not justify
calling normal spawn gameplay generally CPU- or GPU-bound.

The lower-resolution capture has just one gap over 33.34 ms: 100 ms at
0.3874 s, with 9.675 ms of target GPU overlap and no recorded compilation.
It is close to trace startup, and the user reported possible menu time in this
capture. Neither the whole-run averages nor this startup gap establish a
resolution response. No automatic menu removal was attempted.

## Implementation and verification

`analyze_stalls.py` reads the matching TOC and XML exports, follows shared XML
IDs, filters target PID, groups display timestamps per display, and correlates
gaps against recorded GPU/compiler/submission intervals. It also records
submission thread counts by second. Private outputs are `spawn-stalls.json`
and `lower-stalls.json` (the latter predates the optional per-second output).
`analyze_presentation.py EVENTS TOC STALLS OUTPUT --pid 4347` correlates the
additional presentation/drawable export; output is `presentation-stalls.json`.
These are local experimental trace analyzers, not validated menu classifiers.

Seven offline tests pass across the CPU, Metal and stall helpers. New tests
check interval clipping, overlap union, empty inputs and boundary exclusion;
existing Metal tests cover process/reference filtering. Those tests do not
validate Instruments event completeness or diagnose causation. Both captures
retain the backdated-signpost warning, and no collection-overhead baseline or
repeatability estimate exists.

The live read-only Ghidra connection still reports `ntdll.so` with SHA-256
`c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591`, matching a
fresh hash of the working engine. That program is ntdll, not DXMT. No measured
ntdll instruction or function is implicated by these GPU/presentation tables,
so decompiling arbitrary ntdll functions would not select a justified patch.
Wine source remains unchanged.

## Concrete next technical step

Existing CPU samples around 25.8–26.6 seconds were also exported and inspected
(`spawn-cpu.xml`, `cpu-stall-windows.json`, reproduced by
`analyze_saved_cpu.py INPUT OUTPUT`). Before the transition, the DXMT encoding
thread has 595 running samples in a one-second window. It has no recorded
running samples inside either the 229 ms or 300 ms gap; Backend and an unnamed
Wine-host thread dominate those windows. Afterward, a Database thread appears
prominently (555 running samples in seconds 27–28). This is further evidence of
a workload phase change, not proof of which function blocked. Every sampled
state is Running: this trace does not provide blocked-thread wait histories,
and the translated stack labels largely remain raw PCs. Counts are descriptive
sampling observations, not exact CPU timings or a new function-cost ranking.

To resolve the remaining cause,
we need to distinguish game-thread inactivity, DXMT frame-latency/queue waits,
and a focus/lifecycle transition. If the existing evidence is insufficient,
the narrowly scoped next measurement is thread scheduling/wait-state telemetry
correlated with present requests during ordinary Zombies gameplay, with focus
and lifecycle events recorded. This replaces repeated resolution experiments.

Once a specific translation-layer or Wine path is implicated, first establish
matching source/build provenance, then implement one isolated candidate and
compare correctness and pacing. No kernel rewrite or performance patch is
supported by the current evidence. Working engine and debug-register behavior
remain the baseline.
