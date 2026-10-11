# Virtualizing x86 debug registers under Rosetta

An ongoing systems project exploring how Wine can preserve **x86 debug-register semantics on Apple Silicon**, where Rosetta’s translated execution cannot use Wine’s usual x86 hardware-breakpoint path.

The challenge spans binary translation, CPU exception semantics, and Wine’s 32-bit/64-bit context boundary: remembering a register value is only the first step toward reproducing its behavior.

## [Explore the illustrated investigation →](walkthrough.ipynb)

Follow the path from shadow register state to execution-breakpoint delivery, then examine a 32-bit single-step CALL stack anomaly. **Diagrams, minimal reproducers, and saved measurements—read directly on GitHub, no setup required.**

### Implemented so far

- Shadow debug-register state and context round trips.
- Opt-in execution-breakpoint delivery, continuation, handler redirection, and DR6/RF behavior.
- **24 passing execution-breakpoint cases** across x86_64 and i386/WOW64.

**Full virtualization is unfinished.** Data watchpoints are not emulated; ordinary application TF/CALL stepping still exposes a stack anomaly. A narrowly gated workaround covers internal breakpoint stepping. Broader correctness, signal-safety, and performance assessment remain open.

BO2’s loading hang motivated the investigation; its successful map load is one integration result.

[Implementation & build guide](docs/implementation.md) · [Validation evidence](test-results/validation-2026-10-08.md) · [Patches](patches/) · [Reproducers](probes/)
