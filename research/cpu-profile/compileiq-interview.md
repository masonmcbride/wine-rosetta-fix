# Compiler/runtime tuning: interview evidence

The project now has a complete local compiler experiment: a coherent DWARF
exception build of DXMT v0.80, exception-cleanup probes, an offscreen D3D11 copy
test, a focused graphics API benchmark, and independent Ghidra instruction checks.
No game or installed graphics DLL was changed. Gameplay improvement remains
unmeasured.

## A concise explanation

> I started by making Wine execution breakpoints work under Rosetta so a game
> could load. Then I investigated frame pacing and traced sampled graphics
> instructions to exception registration, TLS and locking. I used binary analysis
> to verify what actually shipped, reproduced an exception-model code-generation
> difference, and built a coherent alternative graphics backend. Both runtime
> configurations passed my exception-cleanup probes, and the graphics builds
> passed an offscreen copy test. A focused D3D11 getter benchmark improved with
> the alternative build. My next step is testing whether that improvement matters
> to actual frame pacing. The connection to compiler tuning is the loop from
> compilation choices to generated code to correctness and measured performance.

CompileIQ searches NVIDIA compiler controls and application parameters against
workload benchmarks. The connection is this experimental method; its controls
are not directly applicable to Wine CPU code or Apple's Metal backend.
[Official CompileIQ overview](https://github.com/NVIDIA/CompileIQ).

## What has actually been established

| Stage | Evidence | Limit |
|---|---|---|
| Identify shipped code | Installed DXMT code matches official v0.80 outside its 16-byte header marker | Does not reproduce the release build |
| Find a mechanism | Installed graphics assembly contains exception registration calling TLS machinery | Samples do not establish aggregate cost or frame-gap causation |
| Vary compilation | Same Clang 21.1.8 compiles the guarded fixture with SjLj and DWARF exception modes | The linked runtime stacks differ |
| Check semantics | Cleanup, nested rethrow, derived/base catch, constructor failure and repeated throws pass on main and secondary threads | No cross-DLL, concurrency or exhaustive ABI validation |
| Build graphics alternative | All three PE32 graphics DLLs compile/link with LLVM-MinGW and DWARF | Compiler, C++ library, unwinder and layout differ from release |
| Exercise graphics | Release, GCC and DWARF builds pass a 4 KiB offscreen resource copy and vertex-state checks | No shaders, rendering, presentation or gameplay tested |
| Measure targeted cost | Repeated synthetic and D3D11 getter timings with saved receipts | Getter is not established as a significant BO2 workload |
| Independently inspect | Ghidra decodes 36 release and 22 alternative entry instructions; bytes/call targets checked against files | Static entry windows, not function CPU attribution |

The initial attempt to link a DWARF fixture against the installed GCC SjLj
runtime failed on `_Unwind_Resume` and `__gxx_personality_v0`. This was resolved
by obtaining a coherent LLVM-MinGW package, not by suppressing the missing
symbols or disabling exceptions.

## Measurements

Synthetic guarded-call fixture: eight alternating-order pairs, 3,000,000 measured
iterations per run, plus translation warmup. Both variants use the same Clang
for the measured work translation unit. SjLj links GCC's runtime; DWARF links
LLVM's runtime. The main translation unit, startup and link stacks differ.

| Configuration | Median ns per guarded iteration |
|---|---:|
| Clang SjLj + GCC exception runtime | 64.98 |
| Clang DWARF + LLVM exception runtime | 2.89 |

All eight paired differences favor DWARF. The measured loop contains two nested
RAII guards and intentionally tiny useful work. This is a mechanism probe, not
a representative graphics workload. No exceptions are thrown in its timed loop;
exception correctness is checked separately before timing. Matching checksums
and cleanup counts prevent silent removal of the intended work.

The focused graphics benchmark calls `IAGetVertexBuffers` on a real immediate
D3D11 context, reading a previously bound buffer's stride/offset. It does not
request the buffer pointer, so it excludes that optional QueryInterface/AddRef
path. A getter microbenchmark measures a specific CPU path; its relevance to
BO2 call frequency has not been established.

| Graphics build | Median ns per `IAGetVertexBuffers` call |
|---|---:|
| Installed DXMT v0.80 release | 36.88 |
| Local GCC SjLj build | 36.16 |
| Local LLVM DWARF build | 10.53 |

All six matched-round release-minus-DWARF differences favor the alternative.

The final results and all individual measurements are in
[graphics receipt](dxmt-graphics-receipt.json). Six rounds use every permutation
of the three build configurations once, balancing order and run position. Each
run performs 1,000,000 measured calls after 10,000 warmup calls. Each also passes
the offscreen copy and state checks. Both D3D11 and DXGI loaded paths are checked.

The source contains nested device-mutex guards on this getter path. Release
assembly registers/unregisters SjLj exception state; the alternative uses DWARF
cleanup. Other compiler/runtime/code-layout differences remain, so the API timing
difference cannot be attributed entirely to exception mode.

## What Ghidra adds

The independent headless audit imports the exact release and candidate hashes
into disposable read-only projects. It verifies entry-window instruction bytes
and relative-call targets against the PE files. At release address `0x6a6a1b1a`,
it confirms the call to `0x6a5ed100`, the exact symbol entry for
`_Unwind_SjLj_Register`. The candidate normal entry path instead begins with
mutex acquisition and a getter-helper call. The linked candidate still contains
DWARF unwinding; exceptions were not removed.

This is stronger than showing decompiler screenshots: there is a traceable chain
from artifact identity to instruction bytes to a hypothesized mechanism and a
repeatable experiment. Ghidra does not measure time, establish callers from flat
samples, or prove why a gameplay frame was late. Its existing live MCP session
still targets the Wine ntdll snapshot; these DXMT audits ran separately without
changing that session.

## Reproduce and inspect

- [Initial codegen/link screen](audit_exception_codegen.py) and
  [receipt](exception-codegen-receipt.json).
- [Runtime fixture runner](run_exception_study.py),
  [work source](exception-runtime/work.cpp),
  [driver](exception-runtime/main.cpp), and
  [runtime receipt](exception-runtime-receipt.json).
- [Graphics runner](run_graphics_smoke.py) and
  [graphics probe](exception-runtime/graphics_smoke.cpp).
- [PE audit](audit_dxmt_pe.py), [export/import receipt](dxmt-pe-audit.json), and
  [getter call-site receipt](dxmt-getter-assembly.json).
- [Ghidra runner](run_ghidra_entry_audit.py),
  [Java script](ghidra/AuditDxmtEntry.java), and
  [verification receipt](ghidra-dxmt-verification.json).
- [GCC build receipt](dxmt-build-feasibility.json),
  [complete local source patch](dxmt-build-feasibility.patch), and
  [DWARF build/toolchain receipt](dxmt-dwarf-build.json).

All large binaries, full assembly and raw logs remain under
`/private/tmp/wine-compileiq-audit/`. The official toolchain archive's SHA-256 was
verified against its release metadata before extraction. The pinned package is
LLVM-MinGW 20251216, Clang 21.1.8, named by DXMT's checked-out CI workflow.
The native PE build uses the prepared import boundary to the installed Wine/Metal
bridge. The source patch also adds a missing `<iomanip>` include and redirects
the Metal compiler's module cache to a disposable directory.

Example runtime study (requires permission to create Wine's local server socket):

```sh
python3 research/cpu-profile/run_exception_study.py \
  --out /private/tmp/wine-compileiq-audit/runtime-study \
  --llvm /private/tmp/wine-compileiq-audit/toolchains/llvm-mingw-20251216-ucrt-macos-universal \
  --engine ../bo2-local/engine --pairs 8 --iterations 3000000
```

The graphics runner requires that study's owned disposable prefix and separate
`release`, `gcc`, `llvm` DLL directories. The receipts retain exact commands.

## Next acceptance gate

Keep the installed baseline. Validate a broader graphics workload, exceptional
paths and any required cross-module ABI behavior. Then measure actual gameplay
with repeatable pacing and disturbance controls before selecting a patch.

Useful interview questions include how to reject incompatible configurations
before expensive measurements, separate compiler effects from workload noise,
and enforce correctness constraints during compiler search. The current work
provides concrete examples of all three problems; it is not an implementation
of CompileIQ or a demonstrated BO2 performance improvement.
