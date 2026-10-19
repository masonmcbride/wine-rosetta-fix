# Origins scheduler and presentation correlation

2026-10-15, America/Los_Angeles. Analysis of the saved 20-second telemetry check;
no new gameplay, recording, engine patch or proprietary binary change was needed.

## Result

The actionable investigation target is **the game Backend/producer-to-DXMT
synchronization path**, not an identified Metal kernel or ntdll function. During
the largest later present-request gap, a busy game thread and Backend become
blocked together, DXMT encoding activity declines, and recorded target GPU work
is sparse. This is a correlated execution pattern, not a proved wait-for graph,
lock owner, avoidable cost, or general diagnosis of Zombies performance.

Do not equate the host's `Main Thread` being blocked with a game-loop failure:
it is also mostly blocked in ordinary comparison windows.

## Data and coverage

User confirmed Origins loaded and was asked to play normally. Saved settings
were 1512×945, windowed, VSync off and cap 200. Recorded with Metal System Trace
plus Thread State Trace attached to PID 6211. Raw data remains private under
`bo2-local/profiling/origins-scheduling/`.

The recording spans 20.588 seconds, but extracted display swaps span only
0.323–15.803 seconds and present requests 0.313–16.046 seconds. The cause of
this incomplete presentation coverage is unestablished. Comparisons below use
covered time only; missing events are not treated as a four-second gameplay stall.
The backdated-signpost warning and unmeasured collection disturbance remain
material limitations. Exact user focus/menu behavior was not independently logged.

There are four display gaps over 33.34 ms. Three begin within the first second
(134.45, 41.67 and 36.80 ms), and may be affected by recorder startup. The later
gap is 35.811 ms at 11.193865–11.229677 seconds. A nearby present-request gap
is 32.349 ms at 11.180677–11.213026 seconds. These are different pipeline stages;
do not expect their boundaries or durations to match exactly.

## Equal-window comparison

All columns below span exactly 32.349 ms. Scheduler durations are clipped to
each window for each individual thread, not summed into wall-clock latency.

| Recorded quantity | Immediately before request gap | Request gap | Immediately after |
|---|---:|---:|---:|
| Backend Running | 26.378 ms | 16.195 ms | 23.571 ms |
| Backend Blocked | 0.622 ms | 14.056 ms | 3.224 ms |
| DXMT encode Running | 17.747 ms | 9.383 ms | 14.794 ms |
| DXMT encode Blocked | 14.295 ms | 22.771 ms | 17.195 ms |
| Recorded target GPU interval union | 19.836 ms | 2.823 ms | 13.448 ms |

The longest individual Backend block intersecting the request gap extends from
11.199067 to 11.216024 seconds (~13.959 ms). Another busy thread, labeled only
`wine 0x2a466`, is blocked from 11.202698 to 11.216232 (~13.533 ms; 10.328 ms
lies inside the request gap). Their near-simultaneous wakeups make a shared
synchronization/dependency a useful hypothesis, but do not prove a shared lock.

DXMT's finish thread has a block from 11.186073 to 11.213781 (~27.708 ms).
The encode thread's longest single block inside the request gap is only
2.594 ms: its 22.771 ms aggregate is many waits, not one continuous 23 ms wait.
A completion thread sleeping can be ordinary operation, so none of these waits
alone proves a bug or excess synchronization.

Within the later **display** gap, recorded drawable waits union to 4.572 ms
and compiler intervals to 0.208 ms; neither spans its 35.811 ms duration.
Target GPU interval union there is 10.245 ms. Union coverage is not hardware
utilization, and unattributed/device work and explicit GPU dependencies are
not ruled out. The table supports sparse recorded execution during the request
pause; it does not establish that the entire device was idle.

## Where recorded CPU execution occurs

For seconds 1–15, recorded Running intervals include:

| Thread label | Recorded Running duration over 14 s |
|---|---:|
| Backend | 10.675 s |
| wine 0x2a466 (role unestablished) | 9.522 s |
| DXMT encode | 6.973 s |
| Each of five JQ Workers | 5.159–5.194 s |

These name useful threads to investigate, not function-level hot paths. They
are instrumented scheduler durations, not independently measured uninstrumented
CPU cost. Multiple threads execute concurrently; do not sum them as frame time.
Preemption is also substantial on the busy game threads, but this run cannot
separate ordinary workload competition from tracing disturbance.

## Why collection was expensive: corrected explanation

The complete scheduler export contains 7,816,485 intervals, of which 7,812,077
belong to Zombies (~99.94%). Therefore the earlier explanation emphasizing
unrelated system processes was overstated: the dominant exported volume comes
from detailed modeling of the game's own frequent state changes. These are
model intervals, not one-to-one hardware context switches. Their count does not
prove wasted application work. Full Metal collection adds other event streams;
Instruments' diagnostic sample measured ~15 GB footprint during finalization.
Do not repeat or extend that combined preset unchanged.

## Analysis implementation and checks

`extract_thread_states.py` streams XML, resolves references with a packed numeric
array and small metadata map, filters PID, and writes a private target CSV. It
processed the whole export, not just the earlier 100,000-row pilot. Numeric
reference storage is ~55.6 MB, plus 8,288 object references and parser overhead.
`correlate_thread_states.py` clips intervals to explicit windows. Across all
7,812,077 target intervals there were zero backward per-thread starts and zero
overlapping intervals; per-thread sums in each analyzed window do not exceed
that window. `correlate_gpu_windows.py` streams GPU rows and unions clipped
intervals, preserving the primary duration when a row has multiple duration fields.

A point-event counting bug in `analyze_stalls.py` was also fixed: present requests
lack a duration and must still count as starts inside a display gap. They add
zero interval duration. The corrected later display gap has five request starts;
the earlier request gap is a separate measured interval. No conclusions should
be based on the initial zero counts from that corner case.

Twelve offline tests pass, including PID/reference handling, missing-reference
rejection, overlap coverage rejection, clipping, point presentation events, and
primary GPU duration selection. These verify analysis mechanics, not event
completeness, lock causation, recorder overhead, or gameplay repeatability.

Private outputs include `game-states.csv`, `game-states.csv.json`,
`scheduler-windows.json`, `focused-wait-intervals.json`, `gpu-windows.json`,
`frame-summary.json`, `frame-gaps.json` and `present-request-gaps.json`.
No account state or raw game trace is added to Git.

## Next step

Investigate **what the Backend and wine 0x2a466 threads wait on near 11.20 s**,
and why DXMT's encoder lacks work in that interval. Start with available saved
wait/wakeup metadata and establish backend build/source identity. If the saved
trace cannot name the dependency, use narrow source-aware wait/queue telemetry
in an isolated matching open-source component, with explicit disturbance checks.
Do not infer ownership from similar wakeup times or patch an arbitrary ntdll wait.
No further resolution tests, broad two-minute trace, kernel rewrite or performance
patch is supported by this result. Existing Wine and game binaries remain the baseline.
