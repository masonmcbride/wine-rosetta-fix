# Usable coarse Wine CPU attribution through in-process Mach snapshots

2026-10-15 America/Los_Angeles. This replaces the process-signal sampler for
CPU attribution. The old signal sampler remains rejected. No Wine rebuild,
engine patch, game launch or proprietary executable change was required.

## What changed

A direct probe demonstrated that an x86-64 process running under Rosetta can
suspend a known worker and read its original x86 RIP using
`thread_get_state(..., x86_THREAD_STATE64, ...)`. Five probe snapshots resolved
to the expected `hot_worker`. Failure of hardware debug-register access does
not imply that these general-register snapshots fail.

`mach_sampler.c` uses that path inside a preloaded research library:

1. A collector enumerates the process's threads, excluding itself, and records
   THREAD_BASIC_INFO user/system CPU and thread IDs.
2. It skips threads not reported Running or already suspended. For candidates,
   it suspends, reads the architecture-specific registers and resumes immediately.
   It performs no symbol lookup, allocation or file output while a target is
   suspended. Each thread-list right and list allocation is released.
3. Original PCs and cumulative CPU counters enter a bounded preallocated buffer.
   Per-poll thread order and sleep duration are varied with a fixed reproducible
   PRNG to reduce deterministic cadence/order effects. The sleep is 0.8–1.2 times
   the requested interval; actual polling also includes capture overhead.
4. Outside capture, `atos` resolves module/base/PC tuples. The analyzer weights
   each snapshot with that thread's CPU delta since its preceding valid snapshot.
   It retains unknown attribution, unassigned tails and separate user/system totals.

This is a flat endpoint-snapshot estimator, not a call-stack unwinder. No
SIGPROF delivery or process CPU timer is involved. It uses original machine
addresses and independent CPU counters rather than treating each sampled
thread as an equal unit of work.

## Validation: independent threads and functions on one thread

The unequal-worker benchmark measures each worker's CPU through its own Mach
thread query, independently of the collector. The within-thread benchmark
alternates ~20 ms hot and ~5 ms cool phases and measures their actual CPU time.
The latter test is essential: merely matching per-thread totals cannot validate
how costs are split among functions within that thread.

Rosetta rate sweep: `results/mach-validation-20261015T083014.327961Z`.
Two repetitions per workload/rate, reverse order in repetition 2:

| Test | Requested cadence | Reference cool share | Estimated cool share (mean of two runs) |
|---|---:|---:|---:|
| Unequal workers | 5 ms | 17.68% | 17.45% |
| Unequal workers | 10 ms | 17.66% | 17.46% |
| Unequal workers | 17 ms | 17.63% | 17.29% |
| Two functions on one thread | 5 ms | 20.48% | 19.99% |
| Two functions on one thread | 10 ms | 20.49% | 21.26% |
| Two functions on one thread | 17 ms | 20.48% | 22.74% |

The coarser within-thread case is noisy: one 17 ms run was 25.55% versus
20.47% reference. Do not infer universal sub-percentage-point accuracy.
The 5 ms rate was used for Wine.

After adding observer/window CPU diagnostics, the **same build used for Wine**
was validated again at 5 ms:
`results/mach-validation-20261015T083527.239470Z`.

| Test | Reference mean | Estimated mean |
|---|---:|---:|
| Unequal workers | 17.69% | 17.60% |
| Two functions on one thread | 20.48% | 20.32% |

All snapshots in those calibration runs resolved; zero sampler errors.
Native ARM64 checks use the corresponding native register flavor. Its 10 ms
unequal-worker test was 17.34% versus 17.69%, but its single within-thread
10 ms run was 26.31% versus 20.46%. A denser two-run 5 ms check gave a mean
20.51% versus 20.44%. Both the noisy and improved results are retained:
`mach-validation-20261015T083151.275394Z` and
`mach-validation-20261015T083443.669306Z`.

The mixed-phase reference includes its clock/API loop overhead; it is not an
instruction-level oracle. Sampling is correlated, repetitions are few and no
confidence interval or CPU-frequency isolation is claimed. These results support
coarse attribution on the tested patterns, not exact timing of every function.

## Wine capture results

Workload: existing MIT Win32 event round trips, including independent worker
acknowledgement validation. Same working engine and dedicated research prefix,
with all Rosetta breakpoint/workaround options zero. A parent-PID gate activates
the library only in the directly launched guest host process. Inherited helpers
may load the library but do not activate the collector. Wineserver CPU is not
captured; no system-wide scan or profiling request was made.

The collector waits three seconds and captures ten seconds inside each
15-second guest. Two equal-duration controls bracket two sampled runs.
Results: `results/wine-mach-20261015T083307.994792Z`.

| Quantity | Profile 1 | Profile 2 |
|---|---:|---:|
| Wall capture seconds | 10.0025 | 10.0016 |
| Process user CPU seconds | 3.9710 | 3.9219 |
| Process system CPU seconds | 6.8965 | 6.8921 |
| Collector CPU seconds | 0.0618 | 0.0616 |
| Observed noncollector thread CPU seconds | 10.7995 | 10.7451 |
| Assigned CPU seconds | 10.7954 | 10.7371 |
| Unassigned observed tail | 0.0041 s | 0.0080 s |
| Unresolved assigned CPU weight | 0.0301 s (0.279%) | 0.0426 s (0.397%) |
| Snapshots | 1,657 | 1,647 |
| Mach errors / buffer overflow | 0 / 0 | 0 / 0 |

Observed noncollector thread accounting plus collector CPU is close to the
independent process CPU total; the small residual includes boundaries and time
before thread discovery. Sampling skips sleeping threads instead of counting
idle stacks as CPU. Unknown addresses remain in totals rather than being
silently dropped; these include a few Windows PE addresses not named by atos.

Throughput (round trips/sec):

| Control 1 | Profile 1 | Profile 2 | Control 2 |
|---:|---:|---:|---:|
| 129,815 | 130,697 | 126,696 | 131,174 |

The sampled/control mean ratio is 0.9862: 1.38% lower observed throughput.
This is not a causal overhead estimate: one sampled run exceeds one control,
ordering is fixed and background activity is uncontrolled. Collector CPU is
measured separately and must not be conflated with total perturbation from
pausing threads. Full-run CPU/throughput data are in `throughput.json`.

## What the profile supports

The directly measured process CPU split is approximately **63–64% system CPU**
for this synchronization workload. Repeated snapshots resolve to lock wait/wake
syscall endpoints, Wine's syscall dispatcher, `msync_wait_objs`, event/wait and
in-process synchronization helpers. The same broad path appears in both runs.
This is useful evidence that the event-roundtrip workload is dominated by the
kernel-facing synchronization path, rather than by the isolated DR7 predicate.
It is not evidence about gameplay or another application.

The largest weighted endpoint bins are `__ulock_wait2`, `__ulock_wake` and
`__wine_syscall_dispatcher`. **Do not label the wait bin as exact wait-function
CPU time.** Kernel CPU is recorded separately, but a saved userspace PC can
sit at a syscall boundary. Weighting the preceding CPU interval onto that PC
can also blur phase changes. Kernel-stack tracing or controlled operation-level
experiments would be needed to divide costs within this path. No kernel call
graph or individual engine optimization was proved here.

Ghidra's read-only connection was reverified live. It reports the same ntdll
SHA-256 as the profiled engine and locates `_msync_wait_objs` at `0x1d000`.
The sampled `+378` site corresponds to `0x1d17a` in that artifact. Program
identity is retained in the capture directory's `ghidra-identity.json`.
This connects measured original PCs to static analysis without pretending
Ghidra measured CPU hotness or proving adjacent-source build provenance.

## Tools, checks and practical limits

* `build_mach.py`: builds only the profiler and standalone calibration guests;
  records flags, compiler identity and hashes.
* `validate_mach.py`: runs the two complementary workloads, with raw source/output,
  snapshots, CPU references, hashes and diagnostics retained.
* `try_wine_mach.py`: runs only the MIT guest with equal-duration controls;
  verifies source/build identity and retains before/after artifact hashes.
* `analyze_mach.py`: resolves PCs and conserves per-thread CPU weights; rejects
  backwards counters and attribution exceeding observed thread CPU.

Three offline tests verify independent thread baselines, preservation of
unknown/unassigned costs and rejection of backwards CPU counters. Additional
checks on the real captures verify user+system conservation, zero errors and
unchanged input hashes. Both architectures compile with warnings as errors.

This is a local research profiler, not a production attach tool. Suspending
threads can perturb timing and lock interactions. No symbolic work is done
while a target is suspended; thread exits and failed operations must remain
visible in diagnostics. Thread creation/exit between polls, workloads with
shorter phases, and arbitrary thread churn have not been fully validated.
Only the small tested processes were used. Use the denser 5 ms setting and
repeat/validate when workload behavior changes.

A representative open-source application is the next profiling workload before
claiming a general Wine bottleneck. No further profiler install or Wine rebuild
is needed to make that next measurement. Do not optimize the engine from a
synthetic event benchmark alone.

Wine source remains clean and the debug-register implementation is unchanged.
Before/after hashes matched for the Wine captures. Working ntdll and Ghidra's
snapshot still hash to:

`c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591`

No game, anti-cheat component, proprietary executable, existing game bottle or
engine file was modified. Samply was not reinstalled and the system developer
selection was not changed by this work.
