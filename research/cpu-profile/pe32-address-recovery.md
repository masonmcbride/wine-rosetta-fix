# Original PE32 PC to function to assembly: validated recovery path

2026-10-15, America/Los_Angeles. This closes the **32-bit fixture** recovery
problem. It does not claim gameplay attribution, causal timing, or an optimization.
Zombies was not restarted, injected, recorded or modified during this work.

## What worked

A source-built MIT PE32 CPU fixture ran under the existing Wine engine in the
separate research prefix. The identity-aware in-process sampler recovered:

| Calibration | Original PCs verified to function + source + instruction | Mach errors / overflow |
|---|---:|---:|
| Fixed-delay, correct per-process outputs | 504 / 504 worker samples | 0 / 0 |
| Manually triggered after READY | 505 / 505 worker samples | 0 / 0 |

Example: runtime PC `0x4014ee`, runtime image base `0x400000`, preferred PE base
`0x400000` -> static VA `0x4014ee` -> `hot_leaf`, `calibrate_pe32.c:8` -> bytes
`c1 e8 0d` -> `shr $0xd,%eax`. Runtime bytes read after the capture match the
file's executable section at offset `0xaee`. Other observed addresses resolve
to the same function's `lea`, `imul` and `sub` instructions. This validates
original-PC recovery and identity mapping; sample counts do not measure those
instructions' individual costs or Rosetta translation-block cost.

The prior Mach sampler algorithm is retained unchanged. `build_image_sampler.py`
generates a separate experimental library from that core, adds per-PID filenames,
post-window image/byte lookup, and a manual trigger. `sample_image_resolver.h`
recognizes file-backed executable PE32 regions and validates Mach-O text regions.
It rejects misleading `dladdr` labels, bounds PE searches, and emits unknowns.
No path lookup, disassembly, file hashing or symbol work occurs while a target
thread is suspended.

## Critical process-selection finding

The old parent-PID gate selected Wine's launch process and missed the actual
WOW64 worker. Increasing the sampling delay did not fix it. Per-process output
identified the worker and recovered the known function. Capturing helpers must
not be mistaken for capturing the game. Keep process IDs separate and identify
which process loads/runs the target before interpreting results.

An external observer was also tested only against our signed calibration child.
It successfully obtained its task port and loaded-image addresses outside the
sandbox, but original x86 `thread_get_state` requests returned error 4. All
suspended probe threads were resumed; the child exited successfully. That path
is rejected for original-PC recovery here. Source and logs stay in the private
address-recovery directory. No target code-signature or protection setting was
changed; only the new diagnostic observer was signed with a debugging entitlement.

## Evidence and reproduction

Private results are under `bo2-local/profiling/address-recovery/`:
`pe32-20261015T224039Z` (identity-aware fixed delay) and
`pe32-20261015T224531Z` (manual trigger). They retain source/build metadata,
raw per-process samples, stats, output, input hashes and
`verified-pe32-assembly.json`. The triggered run also preserves the fixture binary
privately. Earlier failed/diagnostic runs are explicitly not attribution evidence.

```sh
# From this directory, on the configured Apple Silicon research machine:
i686-w64-mingw32-gcc -O2 -g -Wall -Wextra -Werror calibrate_pe32.c -o tools/calibrate-pe32.exe
python3 build_image_sampler.py
python3 validate_pe32_pc.py
# Select the fixture worker's CSV from that new result directory:
python3 attribute_pe_samples.py WORKER.csv --image tools/calibrate-pe32.exe --output mapping.json
```

The last step uses an explicit file, preferred/runtime bases, executable section
bounds, exact disassembler instruction boundaries, matching file/runtime bytes,
and DWARF function/source lookup. It does not guess the nearest symbol. Missing
symbols, module identity or bytes stay unresolved. Tests include a relocated
runtime-base example, mismatched memory bytes and unknown module paths. All 19
offline tests pass; sampler variants compile with warnings treated as errors.
Working ntdll hash remains
`c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591`.

## Ready for a bounded gameplay pilot, with limits

`profile_bo2_addresses.py plan` describes an opt-in next run. `launch` uses the
unchanged original BO2 wrapper, which preserves the debug-register options and
refuses an already-active bottle. It preloads only the research library and
prints a private session path. **It requires restarting the game.** It does not
close an existing game automatically. `trigger SESSION` requests three seconds
at a nominal 5 ms cadence after gameplay is ready. No data is automatically sent
or pushed. The trigger expires after ten minutes in each waiting collector.

Gameplay suspension disturbance, arbitrary thread churn, captured module
lifetimes, and the heavy game's lock interactions remain unvalidated. Image
lookup and runtime instruction-byte reads occur at dump time, not every sample;
unloading/reusing a module during capture can invalidate retrospective identity.
That limitation must be addressed or shown inapplicable before a gameplay PC
is promoted through the mandatory attribution gate. The 64 KB PE base search is
bounded to 64 MB behind a PC and only recognizes PE32; failures remain unknown.
Stripped DLLs may yield a verified image/instruction but no verified function or
source. The current Ghidra project remains the hash-matched ntdll; other Wine/DXMT
images require separate verified analysis, not pretending ntdll contains them.

The useful next experiment is a short original-PC gameplay pilot, validate the
correct worker and unknown fraction, then map Wine/DXMT addresses with matching
image identities. Do not infer an optimization from calibration success or use
instruction hit frequency as a cycle-cost distribution.

## First gameplay launch: preload did not reach Wine (2026-10-16)

The delayed trigger produced zero sample files. A local reproduction confirmed
that protected `/bin/bash` strips inherited `DYLD_INSERT_LIBRARIES`. The original
launcher was therefore started without its intended preload; this run is not
profiling evidence. No capture success or gameplay attribution is claimed.

`wine_profile_launch.wrapper_command` now sets the preload inside the shell
after interpreter startup and sources the unchanged original wrapper with its
normal `$0` and arguments. A native-child integration test verifies real library
loading through a wrapper, including paths with spaces, and checks that the
wrapper file is unchanged. All 20 offline tests pass. The game needs a relaunch
for this fix to take effect; no game was automatically stopped or relaunched.
The failed session and reason are retained privately.

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
