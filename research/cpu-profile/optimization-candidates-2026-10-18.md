# Concrete optimization audit: 2026-10-18

The most promising new investigation is **32-bit graphics exception/TLS overhead**.
A second, smaller candidate removes an unnecessary clock read in Wine msync.
Neither is a demonstrated gameplay speedup or selected production optimization.
No Wine/game/backend binaries were replaced; no new gameplay was recorded.

## Installed graphics build is now identified

The installed i386 d3d11.dll and dxgi.dll differ from the official DXMT v0.80
release in exactly 16 bytes, at DOS-header offsets `0x40..0x4f`. The official
`Wine builtin DLL` marker is replaced by DOS-stub bytes. Every other byte,
including code, data, symbols and relocations, is identical. Thus the earlier
whole-file hash mismatch does not indicate different compiled graphics code.

[Identity receipt](dxmt-release-identity.json) records both full hashes and the
archive SHA-256, verified against the official release asset's published digest.
[Official release](https://github.com/3Shain/dxmt/releases/tag/v0.80) corresponds
to source tag commit `589adb780354b461645b29999cefaf533594ee99`, fetched into a
separate private research checkout. This establishes release linkage; it is not
a reproduced build or proof that arbitrary later source matches the binary.

## Lead 1: exception bookkeeping adds TLS and locking to graphics execution

For the saved Origins game worker PID 50302, 138/157 d3d11 samples match exact
instruction bytes. Nineteen remain rejected; they were not normalized or guessed.
COFF function symbols identify **36 samples exactly at function entries**, including:

| Exact function entry | Samples |
|---|---:|
| pthread_spin_unlock | 6 |
| pthread_setspecific | 5 |
| pthread_spin_lock | 3 |
| _Unwind_SjLj_Register | 3 |
| dxmt::d3d11_device_mutex::lock | 3 |
| _Unwind_SjLj_Unregister | 2 |

These are endpoint locations, not call counts, function costs or percentages of
frame time. `resolve_coff_entries.py` does not attach preceding/nearest names to
off-entry addresses. Other samples remain instruction-only until actual bounds
are established. Flat samples do not establish callers.

The installed binary independently shows the following call path:

- `_Unwind_SjLj_Register`, static `0x6a5ed100`.
- `0x6a5ed130`: call `pthread_getspecific`, target `0x6a5ff5c0`.
- `0x6a5ed147`: call `pthread_setspecific`, target `0x6a5ff650`.
- The pthread TLS implementations call spin lock/unlock and imported Windows TLS
  functions. Those are real instructions in the installed module, not inferred
  from a source-only model.

An isolated i386 C++ RAII fixture built with Clang `-fsjlj-exceptions` emits
registration/unregistration calls on the normal path. The same fixture with
`-fdwarf-exceptions` retains exception cleanup but omits those normal-path calls.
See [fixture](exception_codegen_fixture.cpp); assemblies are private under
`bo2-local/profiling/dxmt-build-audit/`, beside installed runtime disassembly.

**Concrete experiment:** rebuild the matching DXMT i386 source with a coherent
DWARF exception toolchain/runtime/dependency set, compare normal-path code and
exception correctness, then A/B against the preserved release backend. Do not
simply disable exceptions or mix an incompatible libgcc/libstdc++ unwinder with
changed compiler flags. Source uses exceptions; removing them is not equivalent.
The fixture proves a code-generation difference, not feasibility of the complete
link, ABI compatibility, or a measured speedup. A complete alternative DXMT build
has not been attempted; required matching dependencies/toolchain are not prepared.

This lead is preferable to blindly removing waits because it identifies actual
runtime work present in graphics execution. Its contribution to uneven frames
still requires recurring, synchronized evidence and collection-overhead checks.

## Candidate 2: skip a clock query when the timeout does not need conversion

`msync_wait_objs` unconditionally calls `NtQuerySystemTime` before examining its
timeout. The installed ntdll confirms the call at static `0x1d056`, bytes
`e855ff0200`, before the null/infinite/absolute branches. The same function occurs
in the saved gameplay samples, but six snapshots do not establish it as hot.

[Unapplied candidate patch](msync-deadline-candidate.patch) moves the query into
the branch that converts relative deadlines (including zero). Null, infinite
and absolute waits avoid it. Object acquisition, atomics, APC priority, timeout
zero behavior, blocking and wakeups are unchanged in the patch. No query is
removed from relative timeout conversion. Relative time is still captured before
object lookup; this is not a change to when a contended wait starts its deadline.

`study_msync_deadline.py` extracts the actual source prefix and generates both
versions without writing the Wine checkout. Eleven fixed-clock boundary cases
match deadlines and expected clock-call counts. Eight alternating-order pairs,
300,000 calls per variant/mode, compiled x86_64 `-O2` and executed under Rosetta:

| Mode | Baseline median ns | Candidate median ns | Median paired saving ns |
|---|---:|---:|---:|
| Infinite | 19.69 | 1.12 | 18.57 |
| Absolute | 19.74 | 1.35 | 18.40 |
| Null | 19.88 | 1.34 | 18.49 |
| Relative | 20.59 | 20.58 | 0.12 |

All eight pairs favor the candidate in each avoided-query case; relative results
are effectively unchanged. This is an isolated deadline-prefix experiment with
a clock_gettime-based query stand-in, not full Wine API timing or a concurrent
synchronization test. It omits Wine's full clock initialization/fallback behavior.
The compiler output retains the baseline call and restricts the candidate call
to its conversion branch. Raw source, hashes, patch, assembly and measurements
are private under `bo2-local/profiling/msync-deadline/`.

Patch applicability passed against WineCX commit
`4ca4a0b0d1899b3a362f69844b225475a2b8905e`. Only `git apply --check` was used.
The full patched engine has not been compiled or tested. Signed-overflow corner
cases already present in the original subtraction were not addressed. A full
Wine timeout/APC/wait-any/wait-all matrix remains necessary before deployment.

This is a small cleanup candidate, not the leading stutter hypothesis. For scale,
100,000 avoided reads per second at 18 ns saves only ~1.8 ms of aggregate CPU per
second; actual gameplay call rates and timeout distributions remain unknown.

## Rejected shortcuts

The sampled `_thread_set_tsd_base` syscall is required Wine/native thread-state
switching until an ABI-safe alternative is established. Snapshot concentration
at that PC does not prove its isolated cost. FXSAVE removal also lacks the needed
register-preservation proof. Neither is proposed as a patch.

In matching release source, `EncodingThread` waits for producer publication on
`ready_for_encode`; `WaitForFinishThread` waits for Metal completion; present
latency and chunk capacity add distinct backpressure. Encoder blocking can mean
lack of producer work rather than an inefficient lock. Removing waits or adding
spin loops without naming the dependency is rejected.

## Completed diagnostic repair and verification

The previously unfinished PE check is now narrowly implemented and tested:
FF25 indirect-jump operands are accepted only when an explicit PE32 HIGHLOW
relocation at the exact operand and exact load delta explain the runtime bytes.
All 41 formerly rejected Wine thunk samples pass that check. The original report
is retained; follow-up results live in the private `attribution-relocations/`
directory. Wine instruction coverage rises from 460 to **501**; adding 138
verified graphics instructions yields **639/2,313**. Function costs remain
unresolved; entry-symbol coverage is a subset, not additional samples.

33 offline tests pass, including rejecting wrong relocation kinds, unlisted
operands and non-function COFF symbols. The deadline experiment has its separate
11-case check. These checks do not substitute for gameplay regression testing.

Next: prepare the coherent graphics build experiment and test compatibility;
use the synchronized pilot to measure recurrence and distinguish CPU runtime
bookkeeping from blocking. Preserve the working baseline until a candidate passes
both correctness and repeated gameplay pacing comparisons.
