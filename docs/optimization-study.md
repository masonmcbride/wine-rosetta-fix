# DR7 predicate: a measured, rejected branchless optimization

Setup follow-up: Ghidra 12.1.4 and a read-only MCP bridge are now installed,
registered with Codex and verified over the MCP protocol; see
[local setup](ghidra-setup.md). The Ghidra findings below were added after the
initial timing experiment, without changing its code or measurements.

Research date: 2026-10-14 (America/Los_Angeles). AI-assisted local research;
not an upstream submission. **Keep the baseline for x86_64 Wine under Rosetta.**
The candidate passed the isolated correctness checks but regressed every tested
x86_64 input distribution. The subsequent Ghidra pass independently checked the
existing Wine artifact; it does not establish a speedup or full build provenance.

## 1. Problem and baseline behavior

Initial inspection found clean companion and Wine worktrees. Companion HEAD was
`b7cf4ae`; Wine HEAD was `6901e703d31`, following shadow-state commit
`b81e0922706` and base `63f62f7cd69`. WineCX source was clean at
`4ca4a0b0d1899b3a362f69844b225475a2b8905e`. The workspace parent itself is not a
Git repository; the IDE-mentioned root AGENTS.md was absent on disk.

The existing patches, probe launcher and C fixtures, implementation notes,
validation records, and controller results were inspected. Historical validation
records report 24/24 breakpoint matrix cases, 126 i386 and 155 x86_64/WOW64
assertions, and the ordinary application TF/CALL failure. These are retained
results, not fresh full-engine validation. The launcher builds both guest
architectures and requires a separate prefix. Neither it nor the game was run.
The controller session lacks Wine CPU profiling and complete input capture;
it provides no basis for selecting a gameplay bottleneck.

The scoped target is the **pure DR7 slot predicate** inside
[`rosetta_exec_breakpoints`](../../wine/dlls/ntdll/unix/signal_x86_64.c#L554).
After existing platform and feature gates, it returns true if any of four slots
has a nonzero two-bit enable pair and a zero four-bit type/length field.
It returns on the first matching slot. This describes the implementation's
contract, including reserved encodings; it does not redefine architectural DR7.

Selection evidence is an isolated cost profile, not an application hotness
profile. Initial translated x86_64 measurements were 1.4417 ns/call (slot 0),
3.18305 (slot 3), 3.2715 (disabled), and 3.37885 (random). These motivated testing
whether independent slot evaluation removes costly control flow. Those pilot
values are exploratory observations; the retained paired run below is the
quantitative result. Actual slot distributions and the function's fraction of
Wine CPU time remain unmeasured. No claim that this is Wine's leading bottleneck
is supported.

A separate two-second `sample` capture of the isolated baseline driver confirms
`X86-64 (translated)`, but most translated PCs are unresolved. Its 1,700 samples
on the main thread cannot reliably attribute baseline versus PRNG/loop time.
Do not count the idle Rosetta exception thread as additional predicate work.
See [`baseline.sample.txt`](../research/dr7/results/baseline.sample.txt). This
sampling limitation prevents a stronger profile-based application conclusion.

## 2. Source, assembly, and Ghidra status

[`prepare.py`](../research/dr7/prepare.py) captures the source function, generates
an unapplied patch, and reads the existing WineCX ntdll Mach-O using `otool`.
[`artifact-hashes.json`](../research/dr7/results/artifact-hashes.json) identifies
the source, original patch exports and compiled Wine artifact. The ntdll SHA-256
is `c21bfbe3bcd2aea74a8143a4d69cbb7b59017adc9471e43afd08536487a77591`.
This hash identifies the inspected file; it does not prove its build provenance
or establish that it was compiled from the adjacent source revision.

The complete saved [`trap_handler` listing](../research/dr7/results/winecx-trap-handler.asm)
starts at unslid address `0x38520`. No standalone symbol for
`rosetta_exec_breakpoints` survived in this binary. The duplicated slot tests in
the handler provide source-to-machine correspondence for the DR7 idiom, not a
claim that this symbol is the extracted helper:

| Machine observation | Source correspondence in WineCX `signal_x86_64.c` |
|---|---|
| `0x38b0f`: load offset `0x318` | `amd64_thread_data.dr7` (verify layout in source) |
| `0x38b16`, `0x38b1e`: masks 3 and 0xf0000 | slot 0 enable and type/length predicate |
| `0x38b70`, `0x38b78`: masks 12 and 0xf00000 | slot 1 predicate |
| `0x38bc6`, `0x38bce`: masks 48 and 0xf000000 | slot 2 predicate |
| `0x38c1c`, `0x38c24`: masks 192 and 0xf0000000 | slot 3 predicate |
| `0x38b3f`: flags-byte test; subsequent CS/RIP checks | RF and pending-resume suppression in `trap_handler` |

Those handler tests also include address matching and exception semantics that
this experiment does not optimize. The reversible patch touches only the helper.

[`x86_64.s`](../research/dr7/results/x86_64.s) shows Clang unrolling the extracted
baseline into slot tests with three conditional early-return branches. The
candidate uses scalar `test`, `setcc`, `and`, and `or`, with no conditional branch
in the predicate. Removing branches adds work on the common early-hit path.
The translated host instruction stream was not recovered, so the precise
Rosetta execution mechanism behind the regression remains unproven.

[`arm64.s`](../research/dr7/results/arm64.s) shows a materially different lowering:
the candidate uses NEON mask comparisons and a horizontal reduction (`umaxv`),
where the baseline retains branches. Native arm64 is a compiler comparison,
not the deployed Wine ABI or evidence of a Rosetta improvement.

**Ghidra MCP findings (completed follow-up).** GhidraMCP 2.0.0, pinned at
`1e980252087b2479a21b9ca6d82d5829538651a7`, was built locally against Ghidra
12.1.4. Our [hardening patch](../research/ghidra-mcp/readonly-hardening.patch)
unconditionally omits editing tools from MCP registration and mutation routes
from the Java HTTP backend. The backend listens only on loopback. A real stdio
MCP client verified exactly 20 read tools, an unknown-tool error for an editing
call, and HTTP 404 for an empty mutation request. The launcher checks hashes of
the snapshot and audited bridge files, fixes the input path and discards the
temporary project's analysis changes on shutdown. Initial import/auto-analysis
creates a temporary database; read-only refers to subsequent API operations
and the original artifact. This is not an OS security boundary against another
process running as the user.

Raw responses, schemas, versions, disassembly pages, pseudocode and selected
branch references are retained in
[`research/ghidra-mcp/results`](../research/ghidra-mcp/results/).
[`program-info.json`](../research/ghidra-mcp/results/program-info.json) reports
Mach-O, `x86:LE:64:default`, pointer size 8, image base zero, 1,227 functions and
the exact ntdll SHA-256 above. The reported compiler specification `gcc` is
Ghidra's analysis choice; it is not proof that GCC built this artifact.

[`trap-function.json`](../research/ghidra-mcp/results/trap-function.json) locates
`_trap_handler` at `0x38520`, with recovered body range `0x38520–0x38f08`.
The complete paginated disassembly contains 507 instructions. No standalone
`rosetta_exec_breakpoints` function was found; the inspected mask idiom is the
duplicated hit scan in WineCX `trap_handler`, source lines 2750–2778. Relevant
control-flow observations were checked against both the raw instructions and
source, rather than inferred solely from C-like output:

| Branch | Ghidra reference / instruction observation | Source meaning |
|---|---|---|
| `0x38b2d → 0x38b70` | conditional jump; fall-through instruction at `0x38b2f` | skip slot 0 if its enable/type predicate fails |
| `0x38b3d → 0x38b70` | conditional jump after address comparison | skip unmatched slot 0 PC |
| `0x38b46 → 0x38b70` | conditional jump after flags-byte test | suppress slot 0 when RF is set |
| `0x38b4f → 0x38b6b` | conditional jump to setting hit bit 0 | no pending resume suppression |
| `0x38b69 → 0x38b70` | conditional jump following saved-PC comparison | pending resume matches; suppress hit |
| `0x38b85 → 0x38bc6` | conditional jump | advance from slot 1 predicate to slot 2 |
| `0x38bdb → 0x38c1c` | conditional jump | advance from slot 2 predicate to slot 3 |
| `0x38c31 → 0x38c7a` | conditional jump | finish scanning when slot 3 predicate fails |
| `0x38c7c → 0x38e11` | conditional jump after testing accumulated hit bits | enter no-hit handling; application TF still controls whether internal stepping continues |

Branch references record the taken edge; fall-through comes from instruction
ordering and branch semantics, not from a complete basic-block export. These are
selected CFG observations, not a claim to have proved every handler path.
The four slot blocks accumulate bits independently, consistent with duplicate
addresses producing multiple hits; they do not return on the first hit like
the isolated eligibility helper.

[`trap-pseudocode.json`](../research/ghidra-mcp/results/trap-pseudocode.json)
recovers the same four mask pairs and the address/RF checks, without truncation.
Its limitations are concrete: function metadata says `undefined _trap_handler(void)`
while decompilation invents a `short *` return and generic parameters, although
the source defines a `void` signal handler with three parameters. It also uses
`short *` arithmetic, so an apparent offset `0x4d` is 0x9a bytes, not 0x4d bytes.
Types, prototypes, offsets, signedness and apparent returns must be checked
against source, layout and instructions. Pseudocode was never used as the
differential-test oracle or as authoritative semantics. Source/model
correspondence and compiler correctness remain outside the solver model.

## 3. Exact optimization and hypothesis

[`predicate.c`](../research/dr7/predicate.c) retains the baseline loop and defines
a candidate evaluating all four boolean slot results using bitwise OR instead
of short-circuit control flow. Every intermediate boolean is zero or one.
It avoids early exits and exposes independent operations to instruction
scheduling and vectorization. The hypothesis was lower branch cost for late-hit
and unpredictable distributions; early-hit inputs can lose because more work
must execute. The measured x86_64 result rejects the hypothesis for these inputs.

[`candidate.patch`](../research/dr7/candidate.patch) applies to the patched Wine
source with `git apply --check`. It leaves the baseline selected unless compiled
with `-DWINE_RESEARCH_BRANCHLESS_DR7`. It preserves the platform/WOW64 feature
gates. It was **not applied or built into Wine**; reverse application would undo
it in a disposable checkout. The two original implementation patches, Wine
checkouts, working engine, bottles, proprietary executables and anti-cheat
components were not modified. No source-level speedup is promoted to production.

## 4. Correctness evidence and limits

[`harness.c`](../research/dr7/harness.c) compares independent baseline/candidate
functions for all 2^24 assignments of relevant bits (0–7 and 16–31), plus one
million deterministic random 64-bit words. Both x86_64/Rosetta and native arm64
executables passed; saved outputs are in `research/dr7/results/`.
The same native arm64 checks also passed with Clang's undefined-behavior
sanitizer (`-O2 -fsanitize=undefined`); see
[`arm64-ubsan.txt`](../research/dr7/results/arm64-ubsan.txt).

The exhaustive test sets irrelevant bits to zero. Source inspection establishes
that both expressions ignore bits 8–15 and 32–63; random testing additionally
exercises these bits. This combination is evidence for this small pure function,
not a machine-checked proof of C compilation. The model assumes an unsigned
64-bit DR7 value, ordinary nonvolatile memory, no concurrent mutation during a
call, and outputs exactly 0 or 1. All shifts are bounded; no signed overflow or
undefined shift is required. Evaluating slots eagerly has no side effects for a
scalar value. It would require renewed analysis for volatile or concurrently
changing state. The existing code provides no synchronization guarantee that
this experiment independently proves.

[`equivalence.smt2`](../research/dr7/equivalence.smt2) encodes the baseline's nested
early-return conditions and the candidate's mask predicates over a 64-bit
bitvector, asserting unequal boolean results. Run `z3 equivalence.smt2` when a
solver is available; `unsat` would prove this model has no counterexample.
**Z3 was not installed and no solver result is claimed.** Exhaustive relevant-bit
testing made the isolated check practical without installing dependencies.
The SMT model does not prove compiler correctness, source/model correspondence,
memory semantics, signal safety, RF/TF handling or full breakpoint delivery.

No new Windows reference run, full Wine build, or full-engine differential test
was performed. Those would be required before deploying a winning candidate.
The historical debug-register regressions remain historical evidence only.

## 5. Measurements and reproduction

On the user's Apple M4 Pro, macOS 15.5, Apple Clang 17.0.0
(`clang-1700.0.13.5`), both versions were compiled in separate translation units
from the driver at `-O2`, without LTO, and with `noinline` on the predicates.
No fast-math or architecture-specific tuning was used. This controls inlining
and constant folding but differs from the inlined full-Wine context.

Each cell below is the median of 15 fresh-process measurements, alternating
baseline/candidate and candidate/baseline order. Each process warms up for one
million calls then times 20 million with `CLOCK_MONOTONIC`. A precomputed 4,096-word
array keeps PRNG generation outside the timed region. Both variants use the
same seed and array; checksums agree for every pair. Timing includes the loop,
array access and function call; it is not a subtracted intrinsic instruction
latency. Fixed modes repeat one DR7 value. Random mode repeats one deterministic
uniform-bit corpus and does not represent observed application DR7 traffic.

| Architecture | Input | Baseline ns/call | Candidate ns/call | Median paired baseline/candidate |
|---|---|---:|---:|---:|
| x86_64 / Rosetta | slot 0 | 1.478 | 4.150 | 0.355 |
| x86_64 / Rosetta | slot 3 | 3.279 | 4.138 | 0.791 |
| x86_64 / Rosetta | disabled | 3.253 | 4.164 | 0.786 |
| x86_64 / Rosetta | random | 3.413 | 4.092 | 0.837 |
| arm64 native | slot 0 | 0.690 | 0.976 | 0.707 |
| arm64 native | slot 3 | 1.203 | 0.975 | 1.221 |
| arm64 native | disabled | 1.172 | 0.977 | 1.197 |
| arm64 native | random | 2.198 | 0.973 | 2.250 |

Ratios below one mean the candidate is slower. See
[`timings.csv`](../research/dr7/results/timings.csv) for all 240 observations and
[`summary.json`](../research/dr7/results/summary.json) for ranges and aggregates.
[`metadata.json`](../research/dr7/results/metadata.json) records compiler, flags,
seed and source hashes. No confidence interval, cycle counter, CPU affinity,
frequency lock or isolation from background load is claimed. The fixed input
array is cache-resident; cold code/data and actual signal handling are untested.
The native arm64 gains do not offset the relevant x86_64 regressions.

From this repository:

```sh
python3 research/dr7/prepare.py
git -C ../wine apply --check ../wine-rosetta-fix/research/dr7/candidate.patch
python3 research/dr7/run.py
```

The scripts overwrite their generated local research results; archive them
before reproducing if keeping multiple runs. They never launch Wine or games.
For the optional sampling run, build and launch the driver, then use its PID:

```sh
clang -O2 -arch x86_64 research/dr7/predicate.c research/dr7/profile.c -o /tmp/dr7-profile
/tmp/dr7-profile &
profile_pid=$!
sample "$profile_pid" 2 1 -file research/dr7/results/baseline.sample.txt
wait "$profile_pid"
```

The saved sample was taken separately from benchmark measurements. macOS
process inspection required running outside the execution sandbox. Its
unresolved translated PCs were retained without assigning invented symbols.

## 6. Three-minute walkthrough for an NVIDIA compiler engineer

**0:00–0:35 — Set the contract.** “Our existing Wine experiment virtualizes x86
debug-register state under Rosetta, with opt-in instruction stepping for
execution breakpoints. I preserved it. I isolated one unsigned predicate:
four slots, each requiring a nonzero enable pair and a zero type/length nibble.
This is local AI-assisted research, not an upstream submission.”

**0:35–1:10 — Establish the evidence boundary.** “The existing controller
measurements cannot identify a Wine bottleneck. An isolated cost profile showed
late-slot evaluation costing more than an early hit. Sampling confirmed
translated execution but could not resolve host PCs. In compiled Wine ntdll,
we can map four DR7 mask tests and selected branch edges back to source, while
retaining address/RF checks as separate semantics. The read-only Ghidra pass
agrees on those masks but invents a return type for the void handler, so its
pseudocode is supporting evidence rather than a semantic oracle.”

**1:10–1:45 — Explain the transformation and correctness.** “I replaced
short-circuit slot search with eager boolean tests and bitwise OR. It is safe
under a stable scalar input because the tests have no side effects. We compared
all 2^24 relevant-bit assignments and a million full-width random words on both
architectures. A 64-bit SMT model is supplied, but no Z3 result is claimed.
None of this proves full signal-handler correctness.”

**1:45–2:25 — Show the surprising result.** “Clang emits scalar setcc logic for
x86_64 and NEON comparisons/reduction for native arm64. In 15 paired runs per
distribution the translated candidate loses everywhere: slot 0 rises from
1.48 to 4.15 ns/call; random rises from 3.41 to 4.09. Native random inputs improve
from 2.20 to 0.97, but that is a different lowering and execution path. Removing
branches is not itself a performance argument.”

**2:25–3:00 — State the decision and discussion.** “I rejected the candidate for
Wine/Rosetta and kept it as a reversible research patch. The useful questions
are how to obtain trustworthy translated-PC attribution, how much real traffic
reaches the late slots, and how inlining changes the lowering. I would require
an attributed Wine profile and full regression evidence before promoting any
future optimization. What evidence would you want before choosing predication,
scalar branch structure, or vectorization here?”
