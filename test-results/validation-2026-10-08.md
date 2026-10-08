# Validation — 2026-10-08

## Results

| Check | i386 / WOW64 | x86_64 |
| --- | --- | --- |
| Execution-breakpoint matrix | 12/12 pass | 12/12 pass |
| Isolated Wine exception assertions | 126; zero failures; exit 0 | 155 including WOW64; zero failures; exit 0 |
| Debug-register state, delivery, handler redirection | Pass | Pass |
| Internal-stepping CALL/RET stack balance | 4-byte push, zero drift | 8-byte push, zero drift |
| Ordinary application TF + direct CALL | Known failure: 8-byte decrement, −4-byte drift | Pass |

BO2 Zombies: the user confirmed that a map loaded and allowed movement/play
with the patched WineCX engine in a copied bottle. This is manual integration
evidence, not a recorded long-session stability benchmark.

The full Wine exception suite and a Windows reference run were not performed.
Data watchpoints, controller support and extended gameplay are outside this
validation. Internal instruction stepping adds overhead and needs further
signal-safety and upstream review.

## Source and patches

Upstream base: `63f62f7cd6964f544b08ae191d6a3d08fc8e5925`.
Consecutive commits:

1. `b81e0922706f9cc23602fecc014043901c059e88`: Rosetta debug-register shadow state.
2. `6901e703d31f1306252a4c3eb4fae74192f0c234`: opt-in execution delivery, regression tests, separately gated CALL workaround.

The two upstream exports match these commits exactly and apply in order
to the upstream base. The WineCX engine uses base
`7dbc5b5322a6ef3fb04bdc643c64b188fd641149`; apply its shadow-state patch followed
by the WineCX execution patch. Source-built Unix ntdll, wineserver and loader
were combined with the retained Whisky runtime payload.

## Mechanism

`server/mach.c` preserves requested Windows-visible DR state under Rosetta.
`dlls/ntdll/unix/signal_x86_64.c` arms internal TF through context setters and
suspended-thread restoration. `trap_handler` matches enabled execution slots
and uses Wine exception dispatch. Context reads hide internal TF; RF survives
WOW64 host transitions. Disabling DR7 clears guest and native return flags and
suppresses pending internal host steps.

The independently gated CALL workaround validates the previous unprefixed E8
instruction, destination, stack delta and return-address words before moving
the return DWORD and adjusting ESP. It covers internal stepping only.

No guest executable patch or game-specific address is used. Installed Whisky
and the original game bottle were preserved. Temporary test isolation was
restored; disposable probes and build outputs were removed. Raw generic
measurements are in [validation JSON](validation-2026-10-08.json); baseline
measurements are in [baseline JSON](baseline-2026-10-08.json).
