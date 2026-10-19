# Synchronized pacing pilot

Prepared and fixture-tested 2026-10-17, America/Los_Angeles. No new gameplay
recording, game restart or engine patch was performed during this preparation.

## What is ready

A locally generated Instruments template retains **Display, Thread State Trace,
and Points of Interest**. It omits the full Metal GPU/resource/application,
Time Profiler, syscall and VM instruments from Game Performance. Dependencies
still collect some underlying events; a smaller instrument list is not proof
of low overhead. The template derives from installed Xcode using a private
keyed-archive layout and must be revalidated after Xcode changes. Generated
Apple template bytes stay under ignored private `bo2-local/`.

A separate `mach-sampler-synced.dylib` adds two PID-specific signposts and
CLOCK_MONOTONIC call brackets. The original sampler and previously calibrated
image library remain separate. Sampler instructions/identity checks are the
same experimental mechanism, with the same Rosetta and module-lifetime limits.
The Wine launcher and debug-register options are preserved.

`capture_pacing.py` waits the requested delay, starts a **five-second** attached
trace, waits for Instruments' actual ready notification, then triggers the
**three-second** one-shot sampler. The extra trace time covers trigger polling
and the end marker. It refuses used/near-expired trigger sessions. It does not
restart or terminate the game. Five seconds bounds recording, not Instruments'
startup/finalization time or memory footprint. All raw outputs stay private.

## End-to-end fixture result

Disposable MIT `pacing_fixture.m` presents cleared Metal drawables in a small
background window. This validates collection, not Wine/game performance.

Private sample session: `address-recovery/pacing-fixture-20261018T030458Z`.
Private trace session: `synchronized/20261018T030458Z`.

- Both PID 60240 signposts exported; 42/42 CPU snapshots aligned inside anchors.
- Start/end marker call brackets: about 6/3 microseconds. Anchor interval
  difference: about 24.25 microseconds over three seconds. Affine interpolation
  is used inside the anchors; these brackets do **not** bound all alignment error.
- 307 display events explicitly attributed to the fixture PID, over ~5.108 s.
  Desktop/global swaps without target process attribution are not its frames.
- 16,581 target thread-state intervals, including Running, Blocked, Runnable,
  Preempted, Interrupted and Idle. The analyzer retains uncovered time per thread.
- 179 complete target display intervals inside the CPU anchors. 143 have no CPU
  snapshot; sparse sampling is explicit and is not interpreted as idle time.
- Zero sampler failures/overflow. Collector CPU was 72,428 microseconds; this
  excludes suspension disturbance and Instruments cost.
- Trace ~90 MB; scheduler XML ~5.4 MB. This low-work fixture does not predict
  gameplay volume. Stop at a bounded pilot before extending any recording.

The fixture's timer stopped but Cocoa did not initially exit within the wait;
that is recorded as a timeout in its original validation metadata. The fixture
was subsequently absent when cleanup checked its PID. The source now exits
through NSApp termination; the validation runner also bounds cleanup of only
its own child. A one-second follow-up GUI test of the corrected source exited with status 0
and reported `PASS frames=58`. Original validation hashes identify the tested build,
which differs from the corrected fixture. This does not invalidate the exported
frame/marker/state checks, but is not a clean fixture-lifecycle pass.

## Controls before gameplay conclusions

Three modes are available: `display` (display/markers), `states`
(display/states/markers with CPU sampler idle), and `combined` (same plus CPU
sampling). Compare repeated display → states → combined → display windows in
normal gameplay, without changing settings; preserve map/scene/focus notes.
A loaded-but-idle sampler is not a fully uninstrumented control. An additional
ordinary-launch run is required to bound preload overhead. Without independent
frame telemetry, even display-only Instruments overhead remains unresolved.
Do not subtract timings from different scenes or infer overhead from CPU use.
No gameplay overhead measurement or recurring cause is established by this work.

## Next gameplay session

Build commands (workspace root), if inputs changed:

```sh
python3 wine-rosetta-fix/research/cpu-profile/build_image_sampler.py
python3 wine-rosetta-fix/research/cpu-profile/build_synced_sampler.py
python3 wine-rosetta-fix/research/cpu-profile/build_pacing_template.py --output bo2-local/profiling/synchronized/pacing.tracetemplate
python3 wine-rosetta-fix/research/cpu-profile/build_pacing_template.py --display-only --output bo2-local/profiling/synchronized/display-control.tracetemplate
```

After the user requests launch, use `profile_bo2_addresses.py launch --synced`.
This still refuses an already-active bottle. The game needs one restart to load
this separate library; the previous running game cannot acquire it retroactively.
Identify the actual game worker PID and fresh session from that launch; do not
reuse the old PID or capture trigger. On readiness, execute:

```sh
python3 wine-rosetta-fix/research/cpu-profile/capture_pacing.py record \
  --pid GAME_WORKER_PID --session FRESH_SESSION --mode combined --delay 15
```

`plan` in place of `record` prints the command without starting Instruments.
For controls, use `--mode display` or `--mode states` and omit `--session`.
The delay is before recorder startup; the actual start depends on readiness.
No alt-tab is needed after sending the request.

Export the trace TOC with `xctrace export --toc`, then use
`export_pacing_capture.py TRACE --output EXPORT_DIR`. It exports only signposts,
process-attributed displayed surfaces and thread states. Run:

```sh
python3 wine-rosetta-fix/research/cpu-profile/analyze_synced_pacing.py \
  GAME_SAMPLES_CSV EXPORT_DIR TOC_XML ANALYSIS_DIR
```

The report includes every complete covered display interval, state durations,
uncovered duration per thread and original-PC snapshots. It requires both
same-PID markers and exactly one target display stream; missing evidence fails
closed. Aligning data does not establish call counts, exact function CPU cost,
wait ownership or causation. Continue the exact-byte/function verification from
[gameplay assembly attribution](gameplay-assembly-attribution.md) on each new
capture; never reuse another process's slides. Compare recurring slow/smooth
intervals before choosing a patch.
