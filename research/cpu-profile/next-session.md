# Next-session handoff

**Current entry point (2026-10-19):**
[compiler/runtime experiment](compileiq-interview.md). A coherent DWARF DXMT
build and focused runtime/graphics probes now pass. Next is broader graphics,
ABI and actual gameplay-pacing validation; preserve the installed baseline.

**Earlier entry point (2026-10-17):**
[synchronized pacing capture](synchronized-pacing-capture.md). The reduced
collector passed frame/state/clock coverage checks on our disposable Metal
fixture. Gameplay controls and disturbance remain unmeasured. Earlier sections
below retain historical milestones; the sampler has since captured gameplay.

## Objective and baseline

Improve Zombies first, then investigate Overwatch 2 and Borderlands 2 with
measurements from those actual games. Preserve the existing debug-register
implementation and proprietary binaries. No optimization candidate is justified
yet. Do not repeat the resolution-change routine as the next step.

## Established

- Live read-only Ghidra identifies the working ntdll snapshot; SHA-256 is
  `c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591`.
- The Mach sampler passed limited independent CPU-share validation. It has not
  been injected into Zombies and is not a proven general game profiler.
- Existing Origins traces show DXMT encoding-thread submissions and useful
  Metal events. The 26-second stall cluster coincides with a workload phase
  change, sparse presentation requests, and little attributed GPU activity.
- The lower-resolution recording includes possible menu time; do not use it to
  claim a causal resolution response. Long gaps are not proven normal gameplay.
- Existing CPU samples only report Running states and mostly raw translated
  PCs. They cannot reveal why a blocked rendering thread was waiting.

## Next work

1. Prepare a bounded Instruments scheduling/wait-state capture for the Zombies
   host process. Validate blocked-thread and presentation correlation in a short
   capture before collecting a longer run. Keep raw output private.
2. During ordinary user gameplay, collect at most two minutes initially and
   record focus/menu/lifecycle interruptions. No fixed camera or resolution
   changes are needed. Measure collection disturbance before making performance
   claims; CPU/GPU activity alone is not an overhead control.
3. Identify the thread and wait chain at persistent gameplay stalls. Distinguish
   missing game work, DXMT queue/frame-latency waits and lifecycle transitions.
4. Establish matching installed backend source/version before modifying it.
   Upstream DXMT source is an investigation reference, not proved build provenance.
5. If a specific avoidable cost is found, build one candidate separately, retain
   the working engine, and test correctness and repeatable pacing. Otherwise
   report the precise remaining evidence gap. Do not invent a kernel rewrite.

## Local artifacts

Raw gameplay traces and exports are under the private workspace
`bo2-local/profiling/origins-first/`. The existing launch wrapper is
`bo2/run-bo2.sh`; it preserves the validated Rosetta options. The research
sampler's synthetic runner uses separate zeroed breakpoint options and must not
replace the game launcher. Samply remains removed. Xcode Instruments is installed;
commands explicitly select `/Applications/Xcode.app/Contents/Developer` through
`DEVELOPER_DIR`. Do not change system developer settings as a profiling step.

## Scheduling capture follow-up

The short combined trace has now been captured and analyzed; do not repeat
steps 1–2 above with the same preset. Read
[zombies-scheduling-findings.md](zombies-scheduling-findings.md). The concrete
next target is identifying the wait/dependency shared by Backend and the busy
unnamed wine thread near 11.20 s, alongside DXMT encoding starvation. No lock
owner or inefficient function is established. The current private data is under
`bo2-local/profiling/origins-scheduling/`. It contains actual blocked/runnable
intervals, but has incomplete presentation coverage and substantial collection
cost. Over 99.9% of scheduler intervals are from Zombies itself; unrelated
system-process coverage was not the dominant exported volume.

## Mandatory acceptance criteria and whole-run follow-up

Read [recurring-pacing-findings.md](recurring-pacing-findings.md) and
[assembly-attribution-contract.md](assembly-attribution-contract.md). Whole-run
comparisons do not support generalizing the isolated Backend block. The stronger
recurring association is higher DXMT encoder blocking during slow request
intervals while game threads remain busy; display-stage behavior differs.
All 68.937 recorded Running thread-seconds in the covered interval remain
unresolved at function level. Trusted gameplay function-to-assembly attribution
is mandatory before selecting a patch; raw Rosetta PCs or thread names do not
satisfy it. Verify original PCs, runtime mappings, artifact bytes and source
provenance, or use validated source-aware telemetry in a separate component.
Do not treat the synthetic assembly mapping proof as gameplay attribution.

## PE32 address-recovery breakthrough

Read [pe32-address-recovery.md](pe32-address-recovery.md). Original PCs in a
32-bit Windows fixture now map to module, function, source and exact assembly
bytes: 505/505 samples in the triggered calibration, zero Mach errors/overflow.
The old parent-PID gate missed the WOW64 worker; per-PID outputs fix selection.
The new sampler is generated separately and does not change the validated core
or working engine. A game restart is required to preload it; no restart or game
injection has occurred. `profile_bo2_addresses.py plan` describes the prepared
three-second manually triggered pilot. Gameplay disturbance, module lifetime
and stripped-function coverage still need validation. Do not automatically
launch, trigger, or mistake fixture validation for gameplay attribution.

## Gameplay pilot launch correction (2026-10-16)

The first delayed trigger yielded no samples because the protected shell stripped
the preload variable. The launch path is fixed and native-child tested, but the
currently launched game does not gain that fix retroactively. Relaunch through
`profile_bo2_addresses.py launch` after the user closes the current game, then
use a new delayed trigger. Preserve the failed session as failed; no gameplay
function-to-assembly attribution has succeeded yet.

## 2026-10-17: successful gameplay address attribution

The corrected launcher produced 2,313 game-worker samples. Offline checks verified
460 sampled instructions in Wine modules; Ghidra independently confirmed the
main syscall-dispatcher function and selected bytes. Function CPU cost, blocking
and frame-gap causation remain unresolved. See
[gameplay assembly attribution](gameplay-assembly-attribution.md) for exact
coverage, assembly examples, limitations and the next experiment. No optimization
was selected or applied.

## 2026-10-18: concrete compiler/runtime audit

Read [optimization candidates](optimization-candidates-2026-10-18.md). Installed
DXMT code matches official v0.80 outside its 16-byte builtin marker. Exact graphics
entry symbols expose SjLj exception/TLS bookkeeping as a compiler/runtime lead.
An isolated, unapplied msync deadline patch skips unnecessary clock reads and
passes prefix checks; no engine or gameplay speedup has been established.

## 2026-10-19: compiler interview evidence and local build feasibility

Read [compiler interview narrative](compileiq-interview.md). The new
`audit_exception_codegen.py` reproduces PE32 SjLj/DWARF assembly differences,
records runtime symbols, and performs link screens without executing programs.
SjLj links with installed MinGW; DWARF fails on missing unwinder/personality
symbols. A coherent alternative toolchain remains necessary.

A disposable source copy successfully built all three graphics DLLs with GCC
SjLj and the prepared external bridge boundary. See `dxmt-build-feasibility.json`
and its companion patch. Outputs/logs are in
`/private/tmp/wine-compileiq-audit/`; no installed engine or game was modified.
This is build feasibility, not DWARF feasibility, runtime compatibility or a
performance result. Interview framing must preserve those distinctions.

## 2026-10-19 follow-up: coherent DWARF build and measured graphics path

The earlier same-day toolchain gap above is resolved for a complete local build.
Official LLVM-MinGW 20251216 (verified archive digest) built all three graphics
DLLs with DWARF and the existing external bridge boundary. The installed engine
and game bottle remain untouched.

`run_exception_study.py` passed cleanup, rethrow, type-matching and constructor
failure probes on main and secondary threads for both runtime configurations.
Eight alternating-order timing pairs measured 64.98 ns/guarded iteration for
SjLj versus 2.89 ns for DWARF; this is a deliberately tiny mechanism fixture
with different runtime/link stacks, not a gameplay benchmark.

`run_graphics_smoke.py` passed all 18 final graphics runs across release, GCC
and DWARF builds. Each verified a 4 KiB GPU copy, vertex state, and loaded D3D11
and DXGI paths. Six order-balanced rounds of the IAGetVertexBuffers CPU getter
measured medians of 36.88, 36.16 and 10.53 ns/call respectively. Its contribution
to real gameplay is unknown, and complete compiler/runtime configurations differ.

Independent read-only Ghidra imports checked 36 release and 22 alternative
entry instructions against file bytes and relative-call targets. The existing
fixed-target ntdll MCP session was not changed. Receipts and reproduction tools
are linked from `compileiq-interview.md`; raw artifacts remain in
`/private/tmp/wine-compileiq-audit/`.

Next: broader graphics and exception/ABI coverage, then controlled actual-game
pacing comparisons with disturbance checks. Do not install these research DLLs
into the working game bottle based on a getter microbenchmark.
