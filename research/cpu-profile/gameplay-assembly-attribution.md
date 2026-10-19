# Origins: first gameplay instruction attribution

Analysis: 2026-10-17 (America/Los_Angeles). Capture session identifier:
`zombies-20261017T003634Z`, game worker PID 50302. This is the successful
manual-trigger capture after fixing preload loss through the protected shell.
It is separate from the earlier heavy scheduler/Metal capture.

The capture produced original-image address candidates with matching instruction
bytes in Wine. **It does not yet select an optimization or explain frame gaps.**
The sampler was calibrated on our own PE32 workload; original-x86 RIP reporting
under Rosetta is not a guarantee of unbiased instruction residence time.

## Evidence retained privately

Under `bo2-local/profiling/address-recovery/zombies-20261017T003634Z/`:

- `samples.50302.csv` and its stats JSON: 2,313 endpoint samples over 3.001143 s.
- `attribution/summary.json`: module hashes, verification counts, thread CPU.
- `attribution/wine-mach-instructions.json`: runtime PCs/bases, static addresses,
  file offsets, bytes, disassembly, symbol-label candidates and sample counts.
- `attribution/*.dll.json`: per-image PE32 verification, including failures.
- `attribution/ghidra-dispatcher-function.json` and
  `ghidra-dispatcher-page0.json`: independent boundary/byte cross-check.

Raw game paths and proprietary executable addresses remain private. No game
executable, bottle graphics DLL, or Apple framework was disassembled by this
analysis. The game, engine and working debug-register implementation were not
modified. The ntdll SHA-256 still equals Ghidra's fixed artifact:
`c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591`.

Reproduce from the workspace root:

```sh
python3 wine-rosetta-fix/research/cpu-profile/attribute_gameplay_wine.py \
  bo2-local/profiling/address-recovery/zombies-20261017T003634Z/samples.50302.csv \
  --output bo2-local/profiling/address-recovery/zombies-20261017T003634Z/attribution
```

## Coverage and unresolved addresses

| Group | Samples | Result |
|---|---:|---|
| Wine Mach-O modules | 305 | Exact instruction and dump-time bytes match current file |
| Wine PE32 modules | 155 | Exact instruction bytes match; function/source unresolved |
| Wine PE32 modules | 41 | Bytes mismatch; retain unresolved |
| Game executable | 440 | Module identified; instruction/function verification deferred |
| Bottle d3d11.dll | 157 | Module identified; provenance and instruction verification deferred |
| Other Mach-O modules, mainly Apple | 1,144 | Module identified; assembly/function verification deferred |
| Unknown module | 71 | Unresolved |
| **Total** | **2,313** | **460 instruction-verified samples** |

The 41 PE mismatches are 38 kernel32 and 3 ntdll samples. Relocations or changed
code are possible explanations, not established explanations. Do not normalize
bytes or force these through the gate without examining relocation records.
PE files lack usable DWARF function/source results in this run. Exact instruction
identity alone is not full function attribution.

## Function to assembly: verified dispatcher example

Ghidra confirms `___wine_syscall_dispatcher` body `0x343e0..0x3473a`.
Its 250 samples include these exact addresses, verified against captured bytes,
Mach-O executable segment/file offsets, objdump and Ghidra:

| Runtime PC | Runtime base | Static address / file offset | Bytes | Instruction | Samples |
|---|---|---|---|---|---:|
| `0x2089cd4ed` | `0x208999000` | `0x344ed` | `0f05` | `SYSCALL` | 184 |
| `0x2089cd4c8` | `0x208999000` | `0x344c8` | `480fae81c0000000` | `FXSAVE64 [RCX+0xc0]` | 26 |
| `0x2089cd59c` | `0x208999000` | `0x3459c` | `0f28b1c0010000` | `MOVAPS XMM6,[RCX+0x1c0]` | 13 |

The dominant syscall is preceded by `MOV EAX,0x3000003`, loading RDI from
`[R13+0x320]`, and clearing ESI. Adjacent WineCX assembly in
`dlls/ntdll/unix/signal_x86_64.c` identifies the corresponding Apple operation
as `_thread_set_tsd_base`. This is a source correspondence, not proof that the
adjacent source revision produced this binary. It suggests inspecting Windows
API/native transitions and thread-local-state switching, not rewriting this
syscall or removing required state preservation.

Other Mach-O symbol-label candidates include the Unix-call dispatcher (13),
`msync_wait_objs` (6), `get_cached_inproc_sync` (6), and `inproc_wait` (5).
The exact bytes are useful for inspection; small counts do not establish hotness.
In stripped winemetal, objdump labels nine samples after `GetNSScreenForDisplayID`;
**that is not a verified containing function**. A distant preceding symbol can
misname internal code. The same caution applies to stubs and other unconfirmed
symbol ranges. No nearest-symbol label is promoted to a function conclusion.

## CPU activity versus blocking

Thread CPU counters total **11.536745 thread-seconds** during this roughly
three-second multi-threaded capture. These are measured CPU deltas, not wall
seconds or per-function cost. Top threads:

| Thread ID | CPU seconds | Endpoint samples | Leading sampled modules |
|---|---:|---:|---|
| 519505 | 2.442720 | 467 | kernel wrapper, ntdll, d3d11 |
| 519288 | 1.752171 | 360 | kernel wrapper, game executable, ntdll |
| 519533 | 1.228458 | 192 | d3d11, AGXMetal, kernel32 |

There are 981 snapshots in `libsystem_kernel.dylib`. The sampler first observes
running state and then reads registers; a thread can change state between those
steps. A syscall PC can represent a transition or user context associated with
kernel work. These rows do not measure blocked duration, kernel stacks, or exact
syscall cost. The 34,799 skipped not-running observations are not blocked-time
measurements either: repeated observations, changing thread membership and
non-running states prevent treating their count as a duration.

All **11.536745 thread-seconds remain unresolved as exact function-level CPU
cost**. Byte verification improves location identity; it does not turn flat PCs
into inclusive stacks or distribute CPU time exactly. Sampling reported 13
failures, zero buffer overflow and 148,223 microseconds of collector CPU. Collector
CPU does not bound disruption caused by suspending/resuming game threads.

## Relationship to uneven frames and next experiment

The earlier whole-run evidence in [recurring-pacing-findings.md](recurring-pacing-findings.md)
showed recurring encoder-blocking associations and one unusual backend stall.
This capture has no synchronized frame/present or thread-state timeline. Its
threads have different IDs, and neither addresses nor timestamps can be spliced
into the previous run. It cannot establish that the dispatcher caused those gaps.

Next, verify function bounds/source provenance for relevant open-source graphics
code, and distinguish ordinary Wine transition frequency from unusual repeated
work. Then collect several short, simultaneous frame/CPU/state windows with
collector-off comparisons, normal gameplay and no forced alt-tab. Require the
same costly path to recur during slow frame delivery and compare smooth windows.
Resolve scheduler blocking separately from executing CPU work. Validate module
lifetime at capture time, richer caller context and collection disturbance before
selecting or modifying an optimization target.
