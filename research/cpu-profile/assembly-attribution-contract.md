# Mandatory function-to-assembly attribution gate

A performance optimization target must satisfy this gate. A thread name, nearby
symbol, Ghidra decompilation, or unresolved Rosetta PC is insufficient.

1. Record capture identity, PID/lifetime, module SHA-256 and UUID where available,
   architecture, runtime mapping range and the static image base.
2. Establish what the address means: original x86 instruction PC, translated ARM
   PC, return address, or unknown. Do not apply original-image slide arithmetic
   to translated PCs or reuse a slide from another process/capture.
3. For a verified original-image PC, compute static address as runtime PC minus
   runtime image base plus static image base. Check executable section bounds.
4. Resolve the containing function and inspect the exact instruction bytes in
   the matching artifact. Cross-check disassembly and artifact bytes. For return
   addresses, identify the actual preceding call instruction rather than blindly
   subtracting one byte. Ghidra pseudocode is explanatory, not authoritative.
5. Keep running CPU attribution distinct from blocked duration and unresolved
   cost. A sampled PC after an atomic or syscall is not proof of that instruction's
   isolated cost. Call counts alone are not time measurements. Flat endpoint
   estimates are not inclusive call graphs or instruction-cycle measurements.
6. Establish source/build provenance separately from artifact identity before
   changing code. A matching binary hash does not prove adjacent source produced it.
7. Require recurring gameplay evidence, counterexamples, and collection-disturbance
   checks. One stall or a synthetic benchmark cannot select a gameplay optimization.

## Demonstrated mapping, with strict scope

`assembly-mapping-proof.json` records a positive end-to-end example from the
MIT synthetic Wine workload. Captured original x86 PC `0x20893017a` minus its
recorded module base `0x208913000` yields static `0x1d17a`. Read-only Ghidra
identifies `_msync_wait_objs+0x17a`; bytes `0f84f0050000` decode to
`JZ 0x1d770`, following `LOCK CMPXCHG` at `0x1d175`. The instruction bytes were
also checked at the Mach-O segment-derived file offset of the hash-matched
engine ntdll. This is address attribution, not an instruction hotness claim.

**Gameplay is not yet through this gate.** In the current scheduler capture,
CPU sample leaves remain raw PCs, with no verified original-x86/runtime-image
mapping. Some matching Wine UUIDs exist in saved symbol stores; the exported
image-load table is empty, so those identities alone do not supply the required
runtime slides or translated-to-original correspondence. Preserve unresolved
CPU time until those missing links are obtained. Do not select a Wine/DXMT patch
from the current thread-level associations.

## 2026-10-17: partial gameplay location evidence

A separate three-second capture now has dump-time byte-matched Wine instructions
and Ghidra-confirmed syscall-dispatcher boundaries. See
[gameplay attribution](gameplay-assembly-attribution.md). This does not repair the
older scheduler capture or satisfy the complete optimization gate: module lifetime,
caller context, exact function cost, build provenance and recurring frame
correlation remain outstanding.
