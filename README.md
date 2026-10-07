# Wine Rosetta Fix

Experimental execution-breakpoint fixes for Wine under Rosetta on Apple
Silicon. Generic probes establish the behavior independently of BO2.
The current patches target WineCX; they are not ready for an upstream Wine MR.

```
patches/   Experimental WineCX changes
probes/    Generic Windows context, breakpoint and stepping tests
bo2/       Component build and game launch scripts only
wine/      Future independent upstream Wine checkout (ignored)
```

## Next step: the upstream Wine branch

Create a clean upstream Wine checkout at `wine/` and a
`rosetta-exec-breakpoints` branch. Reproduce the generic failures there,
adapt the implementation, integrate Wine regression tests and run them.
Push that branch to your WineHQ GitLab fork and prepare an MR. The checkout
has its own Git history; this public repository ignores it.

Before submission, fix unchanged-debug-register continuation and verify
initial/resumed-PC hits, RF, ordinary TF, remote threads and WOW64 transitions.
Investigate the stepped x86 CALL/RET mismatch separately. The current stack
compensation handles only a validated unprefixed E8 direct CALL. Performance
and signal safety also need review. Data watchpoints are not implemented.
Preserve the working BO2 engine until its replacement passes integration tests.

Wine submission guidance: https://wiki.winehq.org/Submitting_Patches
Upstream repository: https://gitlab.winehq.org/wine/wine

## What currently works

Windows execution-breakpoint behavior requires configuring DR0–DR3/DR7,
receiving `EXCEPTION_SINGLE_STEP`, and resuming with the handler's modified
context. Shadow state alone fixed register readback but did not deliver hits.
The opt-in stepping prototype delivered hits and supported handler redirection
in standalone x86/x64 probes. The full Wine exception suite has not been run.

BO2 Zombies passed the original loading hang, reached its menu and loaded
Buried. Brief operation and resolution/settings changes were reported smooth.
Controller operation and extended matches remain unverified and separate work.

The combined WineCX delta is 215 insertions and 7 deletions across five files,
including 46 inserted regression-test lines. No game addresses or executable
instruction patches were added to Wine. The validated stack compensation
modifies stack state, not executable bytes.

## Run probes

Requires Bash, a compatible Wine engine and both MinGW Windows compilers.
Use a dedicated test prefix, separate from any game bottle:

```sh
PROBE_ENGINE=/path/to/engine PROBE_PREFIX=/path/to/test-prefix \
  ./probes/run.sh hardware-breakpoint-probe
```

Other fixtures: `debug-register-probe`, `breakpoint-redirect-probe`,
`single-step-probe`, `call-ret-step-probe`. Both architectures are compiled
into ignored `local/`. Set `WINE_ROSETTA_EXEC_BREAKPOINTS=1` when testing the
experimental engine. Probe failures may hang or crash the isolated test.

## BO2 integration

Source pin: `7dbc5b5322a6ef3fb04bdc643c64b188fd641149` in WineCX.
Apply `patches/rosetta-debug-state.patch` first, then
`patches/rosetta-execution-stepping-WIP.patch` to that separate source checkout.
The tested runtime used source-built Unix ntdll, wineserver and loader with
remaining payloads retained from Whisky Wine Libraries 4.6.4-beta.1.
Host: Apple Silicon, Rosetta, macOS 15.5. Current upstream reproduction is pending.

The optional build helper requires developer tools, Wine build prerequisites
and new absolute output paths. It never overwrites an existing output engine:

```sh
WINE_SOURCE=/path/to/patched/winecx RUNTIME_PAYLOAD=/path/to/runtime \
  BUILD_DIR=/path/to/new/build OUTPUT_ENGINE=/path/to/new/engine \
  ./bo2/build-components.sh
```

Launch with your own engine and already-prepared copied bottle:

```sh
BO2_ENGINE=/path/to/experimental/engine BO2_PREFIX=/path/to/copied/bottle \
  ./bo2/run-bo2.sh
```

The launcher sets temporary graphics, synchronization and breakpoint options.
It refuses an active prefix and never kills a game. The public `bo2/` folder
contains scripts only: no bottle, account details, game files or runtime.
Private logs and evidence are excluded. Source-only publishing requires no
access to the private working setup. Use a GitHub noreply author email before
committing if you do not want your personal email in public commit metadata.

Source and modifications: LGPL-2.1-or-later; see LICENSE. Wine-derived patches
retain upstream notices. This project is independent of WineHQ, CodeWeavers,
Whisky and the game publishers.
