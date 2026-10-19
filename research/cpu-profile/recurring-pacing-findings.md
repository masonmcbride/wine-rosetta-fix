# Whole-covered-run pacing and function attribution audit

2026-10-15, America/Los_Angeles. Supersedes treating the single 11.2-second stall
as a general diagnosis. Existing data only; no new gameplay capture or engine
change. The user's mandatory assembly requirement is formalized in
[assembly-attribution-contract.md](assembly-attribution-contract.md).

## Covered interval and method

Analyze seconds 1–15 to exclude recorder startup and stay inside both scheduler
and presentation coverage. Preserve the distinction between display-surface
swaps and application present requests. There are 1,744 complete display
intervals and 2,322 complete present-request intervals. Do not interpret either
as an independently validated in-game FPS counter or physical scanout count.
Display records cycle through three surface IDs; their existence does not
establish multiple independent game windows.

`analyze_recurring_pacing.py` constructs exact per-thread cumulative state-duration
integrals at every interval boundary, avoiding time-bin rounding. It preserves
unobserved coverage rather than calling it blocked or running, and rejects
backward/overlapping scheduler intervals. It compares the fastest and slowest
quartiles independently for each event stream; quantile ties can change group
sizes. These are descriptive, temporally dependent groups, not randomized trials.
`compare_pacing_gpu.py` unions target GPU intervals and measures exact overlap
with those same windows. Recorded GPU overlap is not hardware utilization.

## Pacing is uneven across the run

| Stream | Median | 95th percentile | 99th percentile |
|---|---:|---:|---:|
| Display swap interval | 8.315 ms | 21.966 ms | 29.453 ms |
| Present-request interval | 5.696 ms | 9.576 ms | 13.303 ms |

Display 95th-percentile intervals range from ~16.65 to 25.98 ms across the
14 individual seconds. The single larger stall therefore does not account for
all measured irregularity. Present requests have ~5.1–5.8 ms median intervals
in many early seconds, rising to ~7.4–8.0 ms in seconds 9–11 before falling
again. Present-request counts also decline from roughly 170–180 per second
in several early windows to 123–134 per second in seconds 9–11. These describe
this instrumented run, not a diagnosis of the user's reported 190-to-90 FPS swings.

## Recurring thread-level association

Each entry below is the median fraction of its own frame interval, not a fraction
of whole-process CPU. Thread times overlap across cores and must not be added
as wall-clock frame latency.

| Present-request groups | Fastest quarter (581 intervals) | Slowest quarter (581 intervals) |
|---|---:|---:|
| DXMT encoder Running | 70.6% | 39.7% |
| DXMT encoder Blocked | 28.1% | 59.4% |
| Backend Running | 74.9% | 77.1% |
| Backend Blocked | 1.5% | 1.2% |
| Busy unnamed wine thread Running | 66.9% | 71.5% |
| Busy unnamed wine thread Blocked | 7.0% | 3.9% |
| Recorded target GPU overlap fraction | 64.7% | 44.3% |

DXMT encoder blocking is higher in slow groups in **12 of 12 eligible individual
seconds**, requiring at least five fast and five slow observations and excluding
intervals over 30 ms. This check reduces dependence on the one long stall and
on a single slow phase. It does not prove causation or independence. Conditioning
on frame duration and pipeline phase can itself influence these proportions.

This is consistent with uneven work supply or dependencies before GPU execution,
while game CPU threads remain active. It does **not** show that the encoder's
waits are unnecessary, whether the producer is computing useful work or spinning,
or whether a game dependency, queue policy, synchronization, pacing, or recorder
perturbation caused it. Backend's large block in the earlier isolated stall does
not recur as a higher median blocking fraction in slow request intervals.

Display groups show a much weaker encoder difference: median blocked fractions
45.3% fast versus 48.7% slow; GPU overlap fractions are 47.0% versus 51.5%.
The request-stage association therefore cannot simply be generalized to every
variation in displayed cadence. Display/presentation timing remains a distinct
investigation, not a diagnosed display bug.

## Function attribution: explicitly unresolved

Seconds 1–15 contain **68.937 recorded Running thread-seconds** across concurrent
threads. Under the required verified function/assembly gate, all 68.937 seconds
remain unresolved at function level. This is scheduler accounting, not an
independent uninstrumented CPU measurement. Blocked time remains a separate
state and has not been charged to a CPU function.

The saved CPU export contains 68,013 samples in this interval: 67,734 carry raw
PC labels and 279 lack a user backtrace. No sample leaf has an exported symbol
name. Counts are not calibrated per-function CPU weights. The image-load table
has zero rows. Saved symbol-store UUIDs match six current Wine images, including
ntdll and winemetal, but do not by themselves establish runtime bases or whether
a sampled address is original-x86 or translated code. No verified gameplay
sample-to-function-to-assembly mapping is claimed. **The mandatory gameplay
function attribution requirement remains unmet**, and blocks optimization selection.

A separately scoped positive mapping was verified on the retained synthetic
Wine sampler capture: original PC -> runtime module base -> `_msync_wait_objs`
-> exact instruction bytes in hash-matched ntdll -> read-only Ghidra disassembly.
See `assembly-mapping-proof.json`. That proves the mapping workflow works with
appropriate PC/mapping evidence; it does not fill the gameplay evidence gap.

## Ranked interpretation and next action

1. Recurring present-request slowdown coincides with more encoder waiting,
   less encoder execution and lower recorded GPU coverage while game threads
   stay busy. Identify the producer/queue dependency and producer CPU functions.
2. Display cadence has additional variability with a weak version of that same
   association. Examine presentation scheduling separately rather than assuming
   a single cause explains both streams.
3. Collection disturbance remains unmeasured and can affect both observations.
   Avoid the expensive combined preset for confirmation; no performance claim
   is transferable to ordinary play without a lightweight control.
4. Individual long Backend blocks are useful local observations, not a general
   explanation. No specific lock, Wine function, shader or instruction is proved
   needlessly slow. Do not implement a speculative kernel rewrite.

The next attribution work must obtain verifiable original PCs/runtime mappings
or source-aware function and wait/dependency telemetry in an isolated matching
Wine/DXMT component, validated before gameplay use. Preserve the working engine,
debug-register implementation and proprietary binaries. Keep unresolved time
explicit until that step succeeds. No further broad gameplay trace is needed
to restate the current association.

## Evidence and validation

Private results: `recurring-pacing.json`, its per-interval CSV,
`within-second-recurrence.json`, `recurring-gpu.json` and
`function-attribution-audit.json` and the reproducible PID-filtered
`cpu-leaf-audit.json` (from `audit_function_attribution.py`) under `bo2-local/profiling/origins-scheduling/`.
The within-second check's source is retained there as `check_recurrence.py`.
Sixteen offline tests pass, including exact state integrals across missing-data
gaps, overlap rejection, GPU union/prefix queries, process filtering, missing
references and point-event handling. These validate analysis mechanics, not
causal interpretation, profiler overhead, call-stack fidelity or repeatability.
