# Rejected profiling approaches

Keep these failures visible without shipping the abandoned toolchains.
Full reports and scripts are preserved in the private local research archive.

| Approach | Why it was rejected |
|---|---|
| macOS sample | Unresolved Rosetta PCs, misleading repeated dispatcher frames, and waiting threads mixed with active work. |
| Samply 0.13.1 | ARM collector failed translated-library initialization; translated collector produced no useful samples. Removed at the user's request; do not reinstall by default. |
| Instruments Time Profiler / CPU Profiler | Native calibration worked; translated known-call-chain attribution remained unresolved even with matching symbols. |
| Processor Trace | Short native calibration succeeded; translated calibration did not yield valid trace data. |
| SIGPROF / ITIMER_PROF or VIRTUAL | Named original PCs were recoverable, but unequal-worker CPU weighting failed independent validation. Never rank function cost using those signal counts. |
| Branchless DR7 predicate | Isolated differential checks passed, but all tested Rosetta timing distributions regressed. Candidate remains unapplied; see the optimization study. |

The retained Mach sampler uses direct original-register snapshots and per-thread
CPU counters, with separate within-thread validation. It is still experimental.
Metal System Trace yielded usable gameplay GPU and presentation events, but
those events alone cannot identify the CPU function causing a frame gap.
