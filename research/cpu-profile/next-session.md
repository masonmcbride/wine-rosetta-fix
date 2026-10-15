# Next-session handoff

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
