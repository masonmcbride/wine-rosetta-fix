# Wine Rosetta Fix

An experimental execution-breakpoint implementation for Wine under Rosetta on
Apple Silicon. The finished build passed the original BO2 Zombies
loading hang, loaded a map, and allowed movement/play in a copied bottle.
Testing for this experimental milestone is complete. The implementation remains
opt-in and requires separate upstream review before a Wine submission.

## Walk through the investigation

Open [walkthrough.ipynb](walkthrough.ipynb) for the debugging narrative,
LaTeX equations, execution-flow diagram, and measured breakpoint matrix.
Its saved figures render without running Wine; rerunning its analysis cells
requires Python 3 and Jupyter/IPython, with no plotting dependencies.

## Verified behavior

All 24 execution-breakpoint matrix rows passed across x86_64 and i386/WOW64:
initial/resumed PC, later PC, DR6 B0/B1, handler redirection, disabling DR7,
unchanged continuation, duplicate slots and RF suppression. Generic context
round trips, ordinary NOP single-step and internal-stepping CALL/RET also passed.
Isolated upstream Wine exception tests passed 126 i386 and 155 x86_64/WOW64
assertions with zero failures and exit status 0. The full exception suite was
not run. See [results](test-results/validation-2026-10-08.md).

Ordinary application TF + direct CALL still exposes the separate 32-bit Rosetta
stack anomaly. The validated CALL workaround applies only during internal
breakpoint stepping and is independently enabled. Data watchpoints are not
emulated. Extended gameplay, controller support, performance and signal-safety
review remain outside this completed milestone.

## Patch series

The authoritative upstream implementation is two consecutive commits in the
Wine fork, based on `63f62f7cd6964f544b08ae191d6a3d08fc8e5925`.
Apply the two matching exports in order:

1. `patches/0001-debug-register-state.patch` — commit `b81e0922706`.
2. `patches/0002-execution-breakpoints.patch` — commit `6901e703d31`;
   delivery, regression tests and the independently gated CALL workaround.

For the WineCX-based BO2 engine, use the two compatibility patches in
`bo2/patches/` instead, applied in order to WineCX base
`7dbc5b5322a6ef3fb04bdc643c64b188fd641149`.
No game-specific address or guest executable patch is used.

## Build and run BO2

The integration engine replaces Unix ntdll, wineserver and loader; remaining
payloads come from Whisky Wine Libraries 4.6.4-beta.1. Use new output paths and
a prepared copied bottle. Installed Whisky and the original bottle are preserved.

```sh
WINE_SOURCE=/path/to/patched/winecx RUNTIME_PAYLOAD=/path/to/runtime \
  BUILD_DIR=/path/to/new/build OUTPUT_ENGINE=/path/to/new/engine \
  ./bo2/build-components.sh

BO2_ENGINE=/path/to/experimental/engine BO2_PREFIX=/path/to/copied/bottle \
  ./bo2/run-bo2.sh
```

The launcher enables `WINE_ROSETTA_EXEC_BREAKPOINTS=1`,
`WINE_ROSETTA_WOW64_BREAKPOINTS=1` and `WINE_ROSETTA_CALL_WORKAROUND=1`, matching
the successful run. It preserves graphics and synchronization options and
refuses an active prefix. Runtime payloads, bottles, game files, account details
and private logs are excluded from this repository.

## Generic probes

Requires Bash, a compatible Wine engine and both MinGW Windows compilers.
Use a dedicated test prefix and an external timeout when running these fixtures:

```sh
PROBE_ENGINE=/path/to/engine PROBE_PREFIX=/path/to/test-prefix \
  ./probes/run.sh hardware-breakpoint-probe
```

Other fixtures: `debug-register-probe`, `breakpoint-redirect-probe`,
`single-step-probe`, `call-ret-step-probe`, `execution-breakpoint-matrix`,
`internal-call-stack-probe`. Enable the three environment options
above for the finished configuration. Results distinguish the remaining ordinary
TF/CALL failure from successful internal stepping.

Source and modifications: LGPL-2.1-or-later; see LICENSE. Wine-derived patches
retain upstream notices. This project is independent of WineHQ, CodeWeavers,
Whisky and the game publishers.

Final reproducer sources include `execution-breakpoint-matrix.c` (arguments:
location 0=later/1=entry/2=direct-resume, action 0=disable/1=redirect/2=unchanged/3=RF,
duplicate slots 0/1, initial RF 0/1) and `internal-call-stack-probe.c`. Use an
external process timeout; the matrix also bounds its worker wait.

This companion repository explains and exports the work. Upstream Wine
acceptance concerns the two commits in the Wine fork; they have not been
represented here as submitted or merged.

The single launcher is `bo2/run-bo2.sh`. In the local development workspace
it automatically finds the sibling `bo2-local/engine` and `bo2-local/bottle`.
Other users supply `BO2_ENGINE` and `BO2_PREFIX` as shown above.
